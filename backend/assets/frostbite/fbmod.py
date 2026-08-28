"""Write Frosty `.fbmod` files, the mod format the MMC Modding Tools consume.

The MMC Modding Tools (the Madden / College Football Modding Community's fork
of the open-source Frosty Toolsuite) are the community-standard way to mod
CFB 27: their Mod Manager imports `.fbmod` files, merges the enabled ones into
a ModData mirror inside the game folder, and launches the game with
`-dataPath`. Dynasty+ exports its texture re-skins in this format and hands
apply/launch to the Mod Manager instead of building ModData itself.

Format (FrostyToolsuite 1.0.6.x: FrostyModWriter/FrostyModReader/
EditorModResource; all values little-endian, strings are NUL-terminated UTF-8
unless noted):

  u64  magic          0x01005954534F5246 ("FROSTY\\x00\\x01")
  u32  version        5
  i64  dataOffset     file offset of the manifest table (patched at the end)
  i32  dataCount      manifest entry count           (patched at the end)
  str  profileName    1-byte length prefix (BinaryWriter sized string);
                      compared case-insensitively by the reader
  i32  gameVersion    the install's layout.toc "head" value
  cstr title, author, category, version, description, link
  i32  resourceCount
  per resource:
    u8   type          0 Embedded, 1 Ebx, 2 Res, 3 Chunk, 4 Bundle
    i32  resourceIndex manifest slot, -1 = no data
    cstr name          asset path (lowercase) / chunk guid text
    if resourceIndex != -1:
      20B sha1 of the STORED payload, i64 originalSize, u8 flags,
      i32 handlerHash, cstr userData
    i32  addedBundleCount, i32[] fnv1 bundle hashes
    Res extras:   u32 resType, u64 resRid, i32 metaLen, meta bytes
    Chunk extras: u32 rangeStart, u32 rangeEnd, u32 logicalOffset,
                  u32 logicalSize, i32 h32, i32 firstMip
  manifest table at dataOffset: dataCount x (i64 offset, i64 size), then the
  payload blobs; offsets are relative to the end of the table.

Resources 0-4 are always the Icon and Screenshot0-3 embedded entries (the
reader indexes them blindly). Res/Chunk payloads are stored exactly as they
will land in a cas file: wrapped as cas blocks. Uncompressed blocks (type
0x00) are used so no proprietary compressor is needed; the game's block
reader is codec-generic.

The exact format was recovered by decompiling the MMC fork's FrostyCore.dll
(FrostyModWriter.WriteProject + the nested ChunkResource/ResResource writers,
FrostyMod.Magic/Version). The CFB 27 profile is version 7, and its chunk
resource carries an extra `h64` (int64) that stock Frosty does not:

    base fields (EditorModResource.Write): type(u8), resourceIndex(i32),
      name(cstr), if idx!=-1 [sha1(20), size(i64), flags(u8), handlerHash(i32),
      userData(cstr)], addedBundleCount(i32) + i32[]
    chunk tail: rangeStart(u32), rangeEnd(u32), logicalOffset(u32),
      logicalSize(u32), h32(i32), h64(i64, CFB 27/Madden 27 only), firstMip(i32),
      superBundleCount(i32) + i32[]
    res tail: resType(u32), resRid(u64), metaLen(i32), meta

h32/h64 are name-hashes Frosty computes for its own bookkeeping (chunk-bundle
membership / added chunks). A texture is located in game by its chunk GUID, so
a RE-SKIN of an existing chunk renders with h32=h64=0 (our ModData writer,
proven at the reader level, never set them either). firstMip is the texture's
first mip; chunk originalSize is 0 (Frosty's ModifyChunk never sets it) and a
re-skin chunk has flags 0 (observed in real MMC texture mods).
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path

MAGIC = 0x01005954534F5246   # FrostyMod.Magic (72155812747760198)
VERSION = 7                  # FrostyMod.Version in the MMC fork
PROFILE_NAME = "CollegeFB27"  # ProfilesLibrary.ProfileName in the MMC fork
# the CFB 27 / Madden 27 profiles add an int64 h64 to the chunk resource
_HAS_H64 = True

_TYPE_EMBEDDED = 0
_TYPE_RES = 2
_TYPE_CHUNK = 3

# 64 KiB uncompressed cas blocks, the block size Frosty's own writer uses
_BLOCK = 0x10000
_BLOCK_TYPE_NONE = 0x00


def cas_blocks(data: bytes) -> bytes:
    """Wrap raw bytes as uncompressed cas blocks (8-byte BE header each:
    decompSize(32)|type(8)|0x7(4)|compSize(20))."""
    out = bytearray()
    for i in range(0, len(data), _BLOCK):
        chunk = data[i:i + _BLOCK]
        n = len(chunk)
        header = (n << 32) | (_BLOCK_TYPE_NONE << 24) | (0x7 << 20) | n
        out += header.to_bytes(8, "big")
        out += chunk
    return bytes(out)


@dataclass
class ModDetails:
    title: str
    author: str = "Dynasty+"
    category: str = "Graphics"
    version: str = "1.0"
    description: str = ""
    link: str = ""


@dataclass
class EmbeddedResource:
    """Icon / screenshot image bytes (PNG), or None for an empty slot."""
    name: str
    data: bytes | None = None


@dataclass
class ResResource:
    """A replaced RES asset (e.g. an ITexture header). `data` is the raw
    uncompressed RES payload; it is block-wrapped on write."""
    name: str
    data: bytes
    res_type: int
    res_rid: int
    res_meta: bytes = b""


@dataclass
class ChunkResource:
    """A replaced chunk (e.g. texture pixel data). `data` is the raw
    uncompressed payload; it is block-wrapped on write. The logical fields
    describe the chunk the way the texture RES does (for an unsplit
    single-mip texture: offset 0, size = the payload size)."""
    guid: str
    data: bytes
    logical_offset: int
    logical_size: int
    first_mip: int = 0
    h32: int = 0
    h64: int = 0


def _cstr(s: str) -> bytes:
    return (s or "").encode("utf-8") + b"\0"


class _Manifest:
    """Payload blobs, deduplicated by sha1 exactly like Frosty's writer."""

    def __init__(self):
        self.blobs: list[bytes] = []
        self._by_sha1: dict[bytes, int] = {}

    def add(self, data: bytes, sha1: bytes | None = None) -> int:
        if sha1 is not None and sha1 in self._by_sha1:
            return self._by_sha1[sha1]
        self.blobs.append(data)
        idx = len(self.blobs) - 1
        if sha1 is not None:
            self._by_sha1[sha1] = idx
        return idx

    def serialize(self) -> bytes:
        table = bytearray()
        body = bytearray()
        for blob in self.blobs:
            table += struct.pack("<qq", len(body), len(blob))
            body += blob
        return bytes(table + body)


def _common_header(rtype: int, index: int, name: str, *, sha1: bytes = b"",
                   size: int = 0, flags: int = 0) -> bytes:
    out = bytearray()
    out += struct.pack("<Bi", rtype, index)
    out += _cstr(name)
    if index != -1:
        out += sha1
        out += struct.pack("<qBi", size, flags, 0)  # size, flags, handlerHash
        out += _cstr("")                            # userData
    out += struct.pack("<i", 0)                     # no added bundles
    return bytes(out)


def write_fbmod(path: Path | str, details: ModDetails,
                resources: list[EmbeddedResource | ResResource | ChunkResource],
                game_version: int = 0) -> dict:
    """Serialize a mod to `path`. Icon/screenshot slots are filled from any
    EmbeddedResource entries passed in (missing slots are written empty).
    Returns a small report {file, resources, size}."""
    manifest = _Manifest()
    body = bytearray()

    # required embedded slots first, in reader order
    embedded = {r.name: r for r in resources if isinstance(r, EmbeddedResource)}
    slots = ["Icon"] + [f"Screenshot{i}" for i in range(4)]
    count = 0
    for slot in slots:
        r = embedded.get(slot)
        if r is not None and r.data:
            idx = manifest.add(r.data)
            body += _common_header(_TYPE_EMBEDDED, idx, slot, sha1=bytes(20),
                                   size=len(r.data))
        else:
            body += _common_header(_TYPE_EMBEDDED, -1, slot)
        count += 1

    for r in resources:
        if isinstance(r, EmbeddedResource):
            continue
        stored = cas_blocks(r.data)
        sha1 = hashlib.sha1(stored).digest()
        idx = manifest.add(stored, sha1)
        if isinstance(r, ResResource):
            body += _common_header(_TYPE_RES, idx, r.name.lower(), sha1=sha1,
                                   size=len(r.data), flags=0)
            body += struct.pack("<IQi", r.res_type, r.res_rid, len(r.res_meta))
            body += r.res_meta
        elif isinstance(r, ChunkResource):
            # a re-skin of an existing chunk: flags 0, originalSize 0 (faithful
            # to Frosty's ModifyChunk, matching real MMC texture mods).
            body += _common_header(_TYPE_CHUNK, idx, r.guid, sha1=sha1,
                                   size=0, flags=0)
            # rangeStart, rangeEnd(=stored len), logicalOffset, logicalSize, h32
            body += struct.pack("<IIIIi", 0, len(stored), r.logical_offset,
                                r.logical_size, r.h32)
            if _HAS_H64:                    # CFB 27 / Madden 27 only
                body += struct.pack("<q", r.h64)
            # firstMip, then the (empty) superBundlesToAdd list
            body += struct.pack("<ii", r.first_mip, 0)
        else:  # pragma: no cover - future resource kinds
            raise TypeError(f"unsupported resource {type(r).__name__}")
        count += 1

    head = bytearray()
    head += struct.pack("<QI", MAGIC, VERSION)
    patch_at = len(head)
    head += struct.pack("<qi", 0, 0)  # dataOffset / dataCount, patched below
    head += bytes([len(PROFILE_NAME)]) + PROFILE_NAME.encode("ascii")
    head += struct.pack("<i", game_version)
    for s in (details.title, details.author, details.category,
              details.version, details.description, details.link):
        head += _cstr(s)
    head += struct.pack("<i", count)

    out = bytearray(head + body)
    struct.pack_into("<qi", out, patch_at, len(out), len(manifest.blobs))
    out += manifest.serialize()

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(bytes(out))
    return {"file": str(p), "resources": count, "size": len(out)}
