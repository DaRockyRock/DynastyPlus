"""Read Frostbite .toc / .sb bundle catalogs from CFB 27.

CFB 27's catalogs open with the DICE signature `00 D1 CE 0N` followed by a fixed
0x22C-byte header, then the payload. Unlike older Frostbite titles, the payload
here is NOT XOR-obfuscated (an early XOR attempt was a false positive): the 32-char
hex value in the header (`f07cb3fa231144fe...`, identical across files) is a format
GUID, not a key, and XORing with it only scrambles the real bytes.

Ground truth from the install:
  * `layout.toc` payload is a plaintext DbObject listing every superbundle
    (`Win32/imageassetlibrarysb`, `Win32/levels/collegefbgame/...`, 108 total).
  * Each per-bundle `Win32/<name>.toc` payload is a binary chunk/asset table
    (big-endian sizes/offsets), a distinct structure still being reversed.

`read_payload` returns the bytes after the header. Parsing the DbObject is
`dbobject` (planned); parsing the per-bundle binary tables is the next stage.
"""
from __future__ import annotations

from pathlib import Path

MAGIC_PREFIX = b"\x00\xd1\xce"
HEADER_LEN = 0x22C  # 556: fixed DICE header before the payload


def is_toc(source: str | Path | bytes) -> bool:
    head = bytes(source[:3]) if isinstance(source, (bytes, bytearray)) else _head(source, 3)
    return head == MAGIC_PREFIX


def read_payload(source: str | Path | bytes) -> bytes:
    """Return the payload bytes after the DICE header (no XOR)."""
    raw = bytes(source) if isinstance(source, (bytes, bytearray)) else Path(source).read_bytes()
    if raw[:3] != MAGIC_PREFIX:
        return raw
    return raw[HEADER_LEN:]


def _head(path: str | Path, n: int) -> bytes:
    try:
        with Path(path).open("rb") as fh:
            return fh.read(n)
    except OSError:
        return b""
