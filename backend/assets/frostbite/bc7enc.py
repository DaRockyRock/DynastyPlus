"""A vectorized BC7 encoder (mode 6 only) for writing textures back into the
game's format.

Mode 6 is the single-subset RGBA mode: 7-bit endpoints + a shared p-bit per
endpoint (so endpoints reconstruct to arbitrary 8-bit values up to the shared
LSB) and 4-bit indices. One mode keeps the encoder small and is a good fit for
flat logo art: solid regions are exact (min == max collapses the palette) and
edges take minor quantization. Everything the game's own decoder needs is
produced; output length is deterministic (16 bytes per 4x4 block), so a
replacement payload is always byte-for-byte the same size as the original
texture it mimics.

Block layout (128 bits, LSB-first):
    bits 0-6    mode marker (bit 6 set)
    bits 7-62   endpoints R0 R1 G0 G1 B0 B1 A0 A1, 7 bits each
    bit  63     P0        bit 64  P1
    bits 65-127 indices: index0 in 3 bits (anchor, MSB implied 0), then 15 x 4
"""
from __future__ import annotations

import numpy as np

# 4-bit interpolation weights from the BC7 spec
_WEIGHTS4 = np.array([0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64],
                     dtype=np.int32)


def encode_bc7(rgba: np.ndarray) -> bytes:
    """Encode an (H, W, 4) uint8 RGBA array (H, W multiples of 4) to BC7."""
    h, w, _ = rgba.shape
    if h % 4 or w % 4:
        raise ValueError("BC7 needs dimensions in multiples of 4")
    # -> (N, 16, 4) blocks in raster order
    blocks = (rgba.reshape(h // 4, 4, w // 4, 4, 4)
                  .transpose(0, 2, 1, 3, 4)
                  .reshape(-1, 16, 4)
                  .astype(np.int32))
    n = blocks.shape[0]

    lo8 = blocks.min(axis=1)   # (N, 4) bounding-box endpoints
    hi8 = blocks.max(axis=1)

    # shared p-bit per endpoint: majority vote of the channels' LSBs
    p0 = (np.sum(lo8 & 1, axis=1) >= 2).astype(np.int64)
    p1 = (np.sum(hi8 & 1, axis=1) >= 2).astype(np.int64)
    e0 = np.clip((lo8 - p0[:, None] + 1) >> 1, 0, 127)
    e1 = np.clip((hi8 - p1[:, None] + 1) >> 1, 0, 127)
    c0 = (e0 << 1) | p0[:, None]   # reconstructed 8-bit endpoints
    c1 = (e1 << 1) | p1[:, None]

    # palette (N, 16, 4) and nearest-index per pixel
    pal = ((c0[:, None, :] * (64 - _WEIGHTS4)[None, :, None]
            + c1[:, None, :] * _WEIGHTS4[None, :, None] + 32) >> 6)
    d = blocks[:, :, None, :] - pal[:, None, :, :]      # (N, 16px, 16pal, 4)
    idx = np.square(d).sum(axis=3).argmin(axis=2)        # (N, 16)

    # anchor rule: index 0 must have its MSB clear; swap endpoints + invert
    swap = idx[:, 0] >= 8
    if swap.any():
        e0[swap], e1[swap] = e1[swap].copy(), e0[swap].copy()
        p0[swap], p1[swap] = p1[swap].copy(), p0[swap].copy()
        idx[swap] = 15 - idx[swap]

    e0 = e0.astype(np.uint64)
    e1 = e1.astype(np.uint64)
    idx = idx.astype(np.uint64)

    lo = np.full(n, 1 << 6, dtype=np.uint64)  # mode 6 marker
    shift = 7
    for ch in range(4):
        lo |= e0[:, ch] << np.uint64(shift)
        lo |= e1[:, ch] << np.uint64(shift + 7)
        shift += 14
    lo |= p0.astype(np.uint64) << np.uint64(63)

    hi = p1.astype(np.uint64)
    hi |= idx[:, 0] << np.uint64(1)           # 3-bit anchor index
    shift = 4
    for k in range(1, 16):
        hi |= idx[:, k] << np.uint64(shift)
        shift += 4

    out = np.empty((n, 2), dtype="<u8")
    out[:, 0] = lo
    out[:, 1] = hi
    return out.tobytes()


def encode_texture(img, info) -> bytes:
    """Encode a PIL image to a replacement payload for a parsed TextureInfo
    (BC7, matching dimensions and full mip chain). The result is exactly
    `info.chunk_size` bytes."""
    from PIL import Image

    if info.pixel_format != 0x42:
        raise ValueError(f"only BC7 (0x42) textures are supported, got {info.pixel_format:#x}")
    out = bytearray()
    w, h = info.width, info.height
    for mip in range(info.mip_count):
        frame = img.convert("RGBA").resize((max(4, w), max(4, h)), Image.LANCZOS)
        data = encode_bc7(np.asarray(frame, dtype=np.uint8))
        expect = info.mip_sizes[mip] if info.mip_sizes[mip] else len(data)
        if len(data) != expect:
            raise ValueError(f"mip {mip}: encoded {len(data)} bytes, texture wants {expect}")
        out += data
        w, h = w // 2, h // 2
    if info.chunk_size and len(out) != info.chunk_size:
        raise ValueError(f"payload {len(out)} bytes != chunk size {info.chunk_size}")
    return bytes(out)
