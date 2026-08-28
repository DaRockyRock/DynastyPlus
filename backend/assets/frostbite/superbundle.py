"""Parse a superbundle .toc payload (Manifest2019 layout).

Header (all big-endian uint32 unless noted):
    +0x00 bundleHashMapOffset
    +0x04 bundleDataOffset
    +0x08 bundlesCount
    +0x0C chunkHashMapOffset
    +0x10 chunkGuidOffset
    +0x14 chunksCount
    +0x18 unused, +0x1C unused
    +0x20 namesOffset
    +0x24 chunkDataOffset
    +0x28 dataCount
    +0x2C flags (1 = has base bundles, 2 = has base chunks, 4 = huffman names)
    if huffman: +0x30 namesCount, +0x34 tableCount, +0x38 tableOffset

Bundle entries at bundleDataOffset: int32 nameOffset (bit index when huffman),
uint32 size (top 2 bits: 0 = bundle lives in the .sb file, 1 = inline in this
toc), int64 offset. Chunk entries at chunkGuidOffset: 16-byte reversed guid +
int32 index into the uint32 chunkData table (top byte of index is the cas-id
flag; 1 = one-word id, 0x80 = two-word id), followed in the table by offset and
size words (little-endian words stored byteswapped, hence the ReverseEndianness).
"""
from __future__ import annotations

from dataclasses import dataclass

from .gamefs import CasRef
from .huffman import HuffmanDecoder
from .reader import Reader, guid_from_dotnet_bytes

FLAG_HAS_BASE_BUNDLES = 1
FLAG_HAS_BASE_CHUNKS = 2
FLAG_COMPRESSED_NAMES = 4


@dataclass
class BundleRef:
    name: str
    offset: int
    size: int
    inline: bool  # True: bundle struct lives in this toc payload


@dataclass
class SuperBundle:
    bundles: list
    chunks: dict  # guid str -> CasRef
    flags: int


def _cas_id_one(word: int) -> tuple[bool, int, int]:
    return ((word >> 16) & 0xFF) != 0, (word >> 8) & 0xFF, word & 0xFF


def _cas_id_two(w1: int, w2: int) -> tuple[bool, int, int]:
    is_patch = ((w1 >> 16) & 0xFF) != 0
    install_chunk = ((w1 << 16) & 0xFFFF0000) | ((w2 >> 16) & 0xFFFF)
    return is_patch, install_chunk, w2 & 0xFFFF


def parse(payload: bytes) -> SuperBundle:
    r = Reader(payload)
    r.skip(4)  # bundleHashMapOffset
    bundle_data_offset = r.u32()
    bundles_count = r.i32()
    r.skip(4)  # chunkHashMapOffset
    chunk_guid_offset = r.u32()
    chunks_count = r.i32()
    r.skip(8)  # two unused (crypto?) offsets
    names_offset = r.u32()
    chunk_data_offset = r.u32()
    data_count = r.i32()
    flags = r.i32()

    huffman = None
    if flags & FLAG_COMPRESSED_NAMES:
        names_count = r.u32()
        table_count = r.u32()
        table_offset = r.u32()
        huffman = HuffmanDecoder()
        r.seek(names_offset)
        huffman.read_data(r, names_count)
        r.seek(table_offset)
        huffman.read_table(r, table_count)

    bundles = []
    r.seek(bundle_data_offset)
    for _ in range(bundles_count):
        name_offset = r.i32()
        size = r.u32()
        offset = r.i64()
        if huffman is not None:
            name = huffman.decode(name_offset)
        else:
            back = r.pos
            r.seek(names_offset + name_offset)
            name = r.cstr()
            r.seek(back)
        load_flag = size >> 30
        bundles.append(BundleRef(name=name, offset=offset, size=size & 0x3FFFFFFF, inline=load_flag == 1))

    chunks: dict[str, CasRef] = {}
    if chunks_count:
        # the chunkData words are stored little-endian in the file; reading them
        # big-endian here matches FrostySdk's raw-read + ReverseEndianness
        r.seek(chunk_data_offset)
        data = [r.u32() for _ in range(data_count)]
        r.seek(chunk_guid_offset)
        removed = set()
        for _ in range(chunks_count):
            guid = guid_from_dotnet_bytes(r.read(16)[::-1])
            index = r.i32()
            if index == -1:
                removed.add(guid)
                continue
            if guid in removed:
                continue
            id_flag = (index >> 24) & 0xFF
            index &= 0x00FFFFFF
            if id_flag == 1:
                is_patch, install_chunk, cas_index = _cas_id_one(data[index])
                index += 1
            elif id_flag == 0x80:
                is_patch, install_chunk, cas_index = _cas_id_two(data[index], data[index + 1])
                index += 2
            else:
                raise ValueError(f"unknown cas id flag 0x{id_flag:02x}")
            offset = data[index]
            size = data[index + 1]
            chunks[guid] = CasRef(is_patch, install_chunk, cas_index, offset, size)

    return SuperBundle(bundles=bundles, chunks=chunks, flags=flags)
