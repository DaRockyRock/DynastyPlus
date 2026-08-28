"""Decode CFB 27 texture RES payloads to PIL images.

Header layout (little-endian, reversed from the game's 184-byte ITexture RES):
    +0x00 u32 mipOffsets[2]
    +0x08 u32 type (0 = 2d)
    +0x0C u32 pixelFormat (RenderFormat enum)
    +0x10 u32 unknown
    +0x14 u16 flags
    +0x16 u16 width, +0x18 u16 height, +0x1A u16 depth, +0x1C u16 sliceCount
    +0x1E u8 mipCount, +0x1F u8 firstMip
    +0x20 u64 unknown
    +0x28 guid chunkId (.NET layout)
    +0x38 u32 mipSizes[15]
    +0x74 u32 chunkSize
    ... name hash + texture group string

Pixel data lives in the referenced chunk, mip 0 first. Formats are decoded via
texture2ddecoder (BCn) or raw RGBA. The RenderFormat values here were confirmed
empirically by decoding and eyeballing known logos.
"""
from __future__ import annotations

from dataclasses import dataclass

from .reader import Reader


@dataclass
class TextureInfo:
    width: int
    height: int
    depth: int
    mip_count: int
    first_mip: int
    pixel_format: int
    chunk_guid: str
    mip_sizes: list
    chunk_size: int
    texture_type: int


def parse_header(res: bytes) -> TextureInfo:
    r = Reader(res)
    r.skip(8)  # mipOffsets
    ttype = r.u32(be=False)
    pixel_format = r.u32(be=False)
    r.skip(4)
    r.skip(2)  # flags
    width = r.u16(be=False)
    height = r.u16(be=False)
    depth = r.u16(be=False)
    r.skip(2)  # sliceCount
    mip_count = r.u8()
    first_mip = r.u8()
    r.skip(8)
    guid = r.guid(be=False)
    mip_sizes = [r.u32(be=False) for _ in range(15)]
    chunk_size = r.u32(be=False)
    return TextureInfo(width, height, depth, mip_count, first_mip, pixel_format,
                       guid, mip_sizes, chunk_size, ttype)


# RenderFormat -> decoder kind. Extended as new formats are observed;
# unknown formats raise so the extractor can report them.
FORMAT_DECODERS = {
    0x36: "bc1",    # 54
    0x3B: "bc3",    # 59
    0x40: "bc5",    # 64
    0x42: "bc7",    # 66  (UI logos)
    0x0B: "rgba8",  # 11
    0x23: "rgba8",  # 35
}


def decode(info: TextureInfo, chunk_data: bytes):
    from PIL import Image
    import texture2ddecoder

    kind = FORMAT_DECODERS.get(info.pixel_format)
    if kind is None:
        raise ValueError(f"unmapped RenderFormat 0x{info.pixel_format:02x} "
                         f"({info.width}x{info.height}, {len(chunk_data)} bytes)")
    w, h = info.width, info.height
    mip0 = chunk_data[:info.mip_sizes[0]] if info.mip_sizes[0] else chunk_data

    if kind == "rgba8":
        return Image.frombytes("RGBA", (w, h), mip0[:w * h * 4], "raw", "RGBA")
    decoder = getattr(texture2ddecoder, f"decode_{kind}")
    return Image.frombytes("RGBA", (w, h), decoder(mip0, w, h), "raw", "BGRA")
