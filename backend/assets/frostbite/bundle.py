"""Parse a Manifest2019 bundle: header struct + BinaryBundle meta + cas refs.

A bundle region (usually inline in the superbundle toc payload) is:
    +0x00 int32 bundleOffset   (0 with bundleSize 0 -> meta lives in a cas file)
    +0x04 int32 bundleSize
    +0x08 uint32 locationOffset (cas-id flag byte per file info, region-relative)
    +0x0C int32 totalCount
    +0x10 uint32 dataOffset     (file info words: [cas id words] offset size)
    +0x14 3 unused uint32s
The BinaryBundle meta (magic xor "pecn") lists ebx/res/chunk entries; the file
info stream at dataOffset yields a (cas, offset, size) per entry, in order, with
the meta itself first when it is not inline.
"""
from __future__ import annotations

from dataclasses import dataclass

from .gamefs import CasRef
from .reader import Reader

SALT = 0x7065636E  # "pecn"
MAGIC_STANDARD = 0xED1CEDB8
MAGIC_KELVIN = 0xC3889333
MAGIC_ENCRYPTED = 0xC3E5D5C3


@dataclass
class EbxEntry:
    name: str
    original_size: int
    cas: CasRef | None = None


@dataclass
class ResEntry:
    name: str
    original_size: int
    res_type: int
    res_meta: bytes
    res_rid: int
    cas: CasRef | None = None


@dataclass
class ChunkEntry:
    guid: str
    logical_offset: int
    logical_size: int
    cas: CasRef | None = None


@dataclass
class Bundle:
    ebx: list
    res: list
    chunks: list
    meta_cas: CasRef | None = None  # set when the BinaryBundle meta is in a cas


def parse_binary_bundle(r: Reader) -> tuple[list, list, list]:
    size = r.u32()
    start = r.pos
    be = True
    magic = r.u32() ^ SALT
    if magic not in (MAGIC_STANDARD, MAGIC_KELVIN, MAGIC_ENCRYPTED):
        raw = (magic ^ SALT)
        magic = int.from_bytes(raw.to_bytes(4, "big"), "little") ^ SALT
        be = False
        if magic not in (MAGIC_STANDARD, MAGIC_KELVIN, MAGIC_ENCRYPTED):
            raise ValueError("bad bundle magic")
    if magic == MAGIC_ENCRYPTED:
        raise ValueError("encrypted bundle (no key support)")

    contains_sha1 = magic == MAGIC_STANDARD
    total_count = r.u32(be)
    ebx_count = r.i32(be)
    res_count = r.i32(be)
    chunk_count = r.i32(be)
    strings_offset = r.u32(be) + start
    r.skip(8)  # metaOffset + metaSize

    r.skip(20 * total_count if contains_sha1 else 0)

    def name_at(off: int) -> str:
        back = r.pos
        r.seek(strings_offset + off)
        s = r.cstr()
        r.seek(back)
        return s

    ebx = []
    for _ in range(ebx_count):
        name_offset = r.u32(be)
        original_size = r.u32(be)
        ebx.append(EbxEntry(name_at(name_offset), original_size))

    res = []
    res_entries = [(r.u32(be), r.u32(be)) for _ in range(res_count)]
    res_types = [r.u32(be) for _ in range(res_count)]
    res_metas = [r.read(16) for _ in range(res_count)]
    res_rids = [r.u64(be) for _ in range(res_count)]
    for i in range(res_count):
        name_offset, original_size = res_entries[i]
        res.append(ResEntry(name_at(name_offset), original_size, res_types[i], res_metas[i], res_rids[i]))

    chunks = []
    for _ in range(chunk_count):
        guid = r.guid(be)
        logical_offset = r.u32(be)
        logical_size = r.u32(be)
        chunks.append(ChunkEntry(guid, logical_offset, logical_size))

    r.seek(start + size)
    return ebx, res, chunks


def _read_cas_id(r: Reader, flag: int, current: tuple | None) -> tuple:
    # Bitfield: 0x80 = two-word cas id follows, 0x01 = one-word id follows,
    # neither = reuse the previous id. CFB 27 also sets 0x04 on some entries
    # (seen on the bundle-meta info); it changes nothing about the encoding.
    if flag & 0x80:
        w1, w2 = r.u32(), r.u32()
        return (
            ((w1 >> 16) & 0xFF) != 0,
            ((w1 << 16) & 0xFFFF0000) | ((w2 >> 16) & 0xFFFF),
            w2 & 0xFFFF,
        )
    if flag & 0x01:
        w = r.u32()
        return ((w >> 16) & 0xFF) != 0, (w >> 8) & 0xFF, w & 0xFF
    if current is None:
        raise ValueError("cas id continuation with no previous id")
    return current


def parse_bundle(payload: bytes, region_offset: int, region_size: int,
                 read_cas=None) -> Bundle:
    """Parse a bundle region. `read_cas(CasRef) -> bytes` must return the RAW
    cas slice (bundle metas are stored uncompressed); only needed when the
    BinaryBundle meta lives in a cas file rather than inline."""
    r = Reader(payload, region_offset)
    bundle_offset = r.i32()
    bundle_size = r.i32()
    location_offset = r.u32()
    total_count = r.i32()
    data_offset = r.u32()

    r.seek(region_offset + location_offset)
    flags = r.read(total_count)

    inline_meta = not (bundle_offset == 0 and bundle_size == 0)
    idx = 0
    current = None
    meta_cas = None

    if inline_meta:
        mr = Reader(payload, region_offset + bundle_offset)
        ebx, res, chunks = parse_binary_bundle(mr)
        r.seek(region_offset + data_offset)
    else:
        r.seek(region_offset + data_offset)
        current = _read_cas_id(r, flags[idx], current)
        idx += 1
        offset, size = r.u32(), r.u32()
        meta_cas = CasRef(current[0], current[1], current[2], offset, size)
        if read_cas is None:
            raise ValueError("bundle meta in cas but no read_cas supplied")
        ebx, res, chunks = parse_binary_bundle(Reader(read_cas(meta_cas)))

    for entry in (*ebx, *res, *chunks):
        current = _read_cas_id(r, flags[idx], current)
        idx += 1
        offset, size = r.u32(), r.u32()
        entry.cas = CasRef(current[0], current[1], current[2], offset, size)

    return Bundle(ebx=ebx, res=res, chunks=chunks, meta_cas=meta_cas)
