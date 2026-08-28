"""Read + decompress asset payloads out of cas archives.

Every stored asset is a sequence of blocks, each with an 8-byte big-endian
header packing flags(8) | decompressedSize(24) | compressionType(8) | 0x7(4) |
compressedSize(20). Compression types seen in CFB 27 are None / ZStd / Oodle
Kraken; Oodle is decoded through the game's own oo2core_9_win64.dll via ctypes.
"""
from __future__ import annotations

import ctypes
import zlib
from functools import lru_cache
from pathlib import Path

from .gamefs import CasRef, GameFS

TYPE_NONE = 0x00
TYPE_ZLIB = 0x02
TYPE_LZ4 = 0x09
TYPE_ZSTD = 0x0F
TYPE_OODLE_KRAKEN = 0x11
TYPE_OODLE_SELKIE = 0x15
TYPE_OODLE_LEVIATHAN = 0x19
OODLE_TYPES = {TYPE_OODLE_KRAKEN, TYPE_OODLE_SELKIE, TYPE_OODLE_LEVIATHAN}


@lru_cache(maxsize=1)
def _oodle(game_root: str):
    dll = Path(game_root) / "oo2core_9_win64.dll"
    lib = ctypes.CDLL(str(dll))
    fn = lib.OodleLZ_Decompress
    fn.restype = ctypes.c_int64
    fn.argtypes = [
        ctypes.c_char_p, ctypes.c_int64,  # src, srcLen
        ctypes.c_char_p, ctypes.c_int64,  # dst, dstLen
        ctypes.c_int32, ctypes.c_int32, ctypes.c_int32,  # fuzzSafe, checkCRC, verbosity
        ctypes.c_void_p, ctypes.c_int64,  # decBufBase, decBufSize
        ctypes.c_void_p, ctypes.c_void_p,  # fpCallback, cbCtx
        ctypes.c_void_p, ctypes.c_int64,  # scratch, scratchSize
        ctypes.c_int32,  # threadPhase (3 = all)
    ]
    return fn


def _oodle_decompress(game_root: str, src: bytes, dst_size: int) -> bytes:
    out = ctypes.create_string_buffer(dst_size)
    got = _oodle(game_root)(src, len(src), out, dst_size, 1, 0, 0, None, 0, None, None, None, 0, 3)
    if got != dst_size:
        raise ValueError(f"oodle: expected {dst_size} bytes, got {got}")
    return out.raw


class CasReader:
    def __init__(self, fs: GameFS):
        self.fs = fs
        self._zstd = None

    def read(self, ref: CasRef) -> bytes:
        return self.decompress(self.read_raw(ref))

    def read_raw(self, ref: CasRef) -> bytes:
        """Read a cas slice without block decompression (bundle metas are raw)."""
        with open(self.fs.cas_path(ref), "rb") as fh:
            fh.seek(ref.offset)
            return fh.read(ref.size)

    def decompress(self, raw: bytes) -> bytes:
        out = bytearray()
        pos = 0
        n = len(raw)
        while pos < n:
            packed = int.from_bytes(raw[pos:pos + 8], "big")
            pos += 8
            if packed == 0:
                continue
            decompressed_size = (packed >> 32) & 0x00FFFFFF
            ctype = (packed >> 24) & 0x7F  # high bit = FIFA19-only obfuscation
            if (packed >> 20) & 0xF != 0x7:
                raise ValueError(f"bad cas block header at {pos - 8}")
            buffer_size = packed & 0x000FFFFF
            if ctype == TYPE_NONE:
                buffer_size = decompressed_size
            block = raw[pos:pos + buffer_size]
            pos += buffer_size
            if ctype == TYPE_NONE:
                out += block
            elif ctype == TYPE_ZLIB:
                out += zlib.decompress(block)
            elif ctype == TYPE_ZSTD:
                out += self._zstd_decompress(block, decompressed_size)
            elif ctype == TYPE_LZ4:
                import lz4.block
                out += lz4.block.decompress(block, uncompressed_size=decompressed_size)
            elif ctype in OODLE_TYPES:
                out += _oodle_decompress(str(self.fs.root), bytes(block), decompressed_size)
            else:
                raise ValueError(f"unknown compression type 0x{ctype:02x}")
        return bytes(out)

    def _zstd_decompress(self, block: bytes, size: int) -> bytes:
        if self._zstd is None:
            import zstandard
            self._zstd = zstandard.ZstdDecompressor()
        return self._zstd.decompress(block, max_output_size=size)
