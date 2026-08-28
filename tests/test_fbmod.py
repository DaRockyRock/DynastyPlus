"""fbmod writer round-trip: parse the output the exact way FrostyModReader
(FrostyToolsuite 1.0.6.x) does, field by field, so a format drift fails here
before it fails inside the MMC Mod Manager."""
import hashlib
import struct

import pytest

from backend.assets.frostbite import fbmod


# --- a faithful FrostyModReader port (read side of the C# reference) --------

class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self, n):
        b = self.data[self.pos:self.pos + n]
        assert len(b) == n, "unexpected EOF"
        self.pos += n
        return b

    def u8(self):
        return self.read(1)[0]

    def i32(self):
        return struct.unpack("<i", self.read(4))[0]

    def u32(self):
        return struct.unpack("<I", self.read(4))[0]

    def i64(self):
        return struct.unpack("<q", self.read(8))[0]

    def u64(self):
        return struct.unpack("<Q", self.read(8))[0]

    def cstr(self):
        end = self.data.index(0, self.pos)
        s = self.data[self.pos:end].decode("utf-8")
        self.pos = end + 1
        return s


def read_fbmod(data: bytes) -> dict:
    r = _Reader(data)
    assert r.u64() == fbmod.MAGIC
    version = r.u32()
    assert version == fbmod.VERSION
    data_offset = r.i64()
    data_count = r.i32()
    profile = r.read(r.u8()).decode("ascii")
    game_version = r.i32()
    details = {k: r.cstr() for k in
               ("title", "author", "category", "version", "description", "link")}

    resources = []
    for _ in range(r.i32()):
        res: dict = {"type": r.u8(), "index": r.i32(), "name": r.cstr()}
        if res["index"] != -1:
            res["sha1"] = r.read(20)
            res["size"] = r.i64()
            res["flags"] = r.u8()
            res["handler"] = r.i32()
            res["user_data"] = r.cstr()
        res["bundles"] = [r.i32() for _ in range(r.i32())]
        if res["type"] == 2:    # Res
            res["res_type"] = r.u32()
            res["res_rid"] = r.u64()
            res["res_meta"] = r.read(r.i32())
        elif res["type"] == 3:  # Chunk (CFB 27 / v7 layout, incl. h64)
            (res["range_start"], res["range_end"], res["logical_offset"],
             res["logical_size"]) = (r.u32(), r.u32(), r.u32(), r.u32())
            res["h32"] = r.i32()
            res["h64"] = struct.unpack_from("<q", r.read(8))[0]
            res["first_mip"] = r.i32()
            res["superbundles"] = [r.i32() for _ in range(r.i32())]
        resources.append(res)

    def payload(res):
        if res.get("index", -1) == -1:
            return None
        p = data_offset + res["index"] * 16
        offset, size = struct.unpack_from("<qq", data, p)
        start = data_offset + data_count * 16 + offset
        return data[start:start + size]

    return {"profile": profile, "game_version": game_version,
            "details": details, "resources": resources, "payload": payload,
            "data_count": data_count}


def unwrap_cas_blocks(stored: bytes) -> bytes:
    """Decode the uncompressed cas-block stream back to raw bytes, checking
    each header the way the game's block reader does."""
    out = bytearray()
    pos = 0
    while pos < len(stored):
        header = int.from_bytes(stored[pos:pos + 8], "big")
        decomp = header >> 32
        btype = (header >> 24) & 0xFF
        flags = (header >> 20) & 0xF
        comp = header & 0xFFFFF
        assert btype == 0x00
        assert flags == 0x7
        assert comp == decomp
        out += stored[pos + 8:pos + 8 + comp]
        pos += 8 + comp
    return bytes(out)


# --- fixtures ----------------------------------------------------------------

GUID = "cbc19cbc-8087-c127-101d-a989f73dd279"


def _write(tmp_path, resources):
    details = fbmod.ModDetails(title="Test Mod", description="a test")
    out = tmp_path / "test.fbmod"
    report = fbmod.write_fbmod(out, details, resources, game_version=4298863)
    return report, out.read_bytes()


def test_header_details_and_empty_slots(tmp_path):
    report, raw = _write(tmp_path, [])
    mod = read_fbmod(raw)
    assert mod["profile"] == "CollegeFB27"
    assert mod["game_version"] == 4298863
    assert mod["details"]["title"] == "Test Mod"
    assert mod["details"]["author"] == "Dynasty+"
    assert mod["details"]["link"] == ""
    # the icon + 4 screenshot slots are always present, empty here
    assert report["resources"] == 5
    names = [r["name"] for r in mod["resources"]]
    assert names == ["Icon", "Screenshot0", "Screenshot1", "Screenshot2", "Screenshot3"]
    assert all(r["type"] == 0 and r["index"] == -1 for r in mod["resources"])
    assert mod["data_count"] == 0


def test_res_and_chunk_round_trip(tmp_path):
    res_data = bytes(range(256)) * 3          # fake ITexture header bytes
    chunk_data = b"\xAB" * (0x10000 + 100)    # forces two cas blocks
    icon = b"\x89PNG fake"
    _report, raw = _write(tmp_path, [
        fbmod.EmbeddedResource("Icon", icon),
        fbmod.ResResource(name="Teamconferences/Assets/Tcon_Big12",
                          data=res_data, res_type=0x6BDE20BA,
                          res_rid=0xE229AF5A53C1A371, res_meta=b"M" * 16),
        fbmod.ChunkResource(guid=GUID, data=chunk_data,
                            logical_offset=0, logical_size=len(chunk_data),
                            first_mip=0, h32=0x1234, h64=0x509e57bf00001234),
    ])
    mod = read_fbmod(raw)
    icon_res, *_slots, res, chunk = mod["resources"][0], *mod["resources"][1:5], *mod["resources"][5:]
    assert mod["payload"](icon_res) == icon

    assert res["type"] == 2
    assert res["name"] == "teamconferences/assets/tcon_big12"  # lowercased
    assert res["size"] == len(res_data)
    assert res["flags"] == 0 and res["handler"] == 0 and res["bundles"] == []
    assert res["res_type"] == 0x6BDE20BA
    assert res["res_rid"] == 0xE229AF5A53C1A371
    assert res["res_meta"] == b"M" * 16
    stored = mod["payload"](res)
    assert res["sha1"] == hashlib.sha1(stored).digest()
    assert unwrap_cas_blocks(stored) == res_data

    assert chunk["type"] == 3
    assert chunk["name"] == GUID
    assert chunk["size"] == 0          # faithful to Frosty's ModifyChunk
    assert chunk["flags"] == 0         # re-skin of an existing chunk
    assert chunk["range_start"] == 0
    assert chunk["logical_offset"] == 0
    assert chunk["logical_size"] == len(chunk_data)
    assert chunk["h32"] == 0x1234
    assert chunk["h64"] == 0x509e57bf00001234  # int64, CFB 27 field
    assert chunk["first_mip"] == 0
    assert chunk["superbundles"] == []
    stored = mod["payload"](chunk)
    assert chunk["range_end"] == len(stored)
    assert chunk["sha1"] == hashlib.sha1(stored).digest()
    assert unwrap_cas_blocks(stored) == chunk_data


def test_identical_payloads_share_a_manifest_slot(tmp_path):
    data = b"same-bytes" * 100
    _report, raw = _write(tmp_path, [
        fbmod.ChunkResource(guid=GUID, data=data, logical_offset=0,
                            logical_size=len(data)),
        fbmod.ChunkResource(guid="49a3531e-b3af-b4ea-48d7-a565fce858fd",
                            data=data, logical_offset=0, logical_size=len(data)),
    ])
    mod = read_fbmod(raw)
    chunks = [r for r in mod["resources"] if r["type"] == 3]
    assert len(chunks) == 2
    assert chunks[0]["index"] == chunks[1]["index"]  # sha1 dedup
    assert mod["data_count"] == 1


def test_multi_block_wrapping_is_exact():
    data = bytes(300000)  # > 4 blocks at 64 KiB
    stored = fbmod.cas_blocks(data)
    assert unwrap_cas_blocks(stored) == data
    n_blocks = (len(data) + 0xFFFF) // 0x10000
    assert len(stored) == len(data) + 8 * n_blocks
