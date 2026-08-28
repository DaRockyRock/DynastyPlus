"""The FBCHUNKS container: the outer layer of a CFB 27 save.

Fully reverse-engineered from real autosaves and reliable. A dynasty save is:

    offset  bytes
    0       "FBCHUNKS"                      8-byte magic
    8       version                         u16 LE (observed: 1)
    10      flags/reserved                  (not yet needed)
    22      saved-at timestamp              6x u16 LE: year, month, day, hour, min, sec
    34      build id                        NUL-terminated ASCII ("College-27-RL1-9039126")
    ~82     zlib stream (0x78 0x9c)         one deflate stream -> the FrTk payload
    ...     zero padding                    to the file's slot size (ignored)

There is a single zlib chunk despite the plural name; the compressed stream is
followed by zero padding, so we inflate with a decompress object and let the
trailing bytes fall into `unused_data`.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAGIC = b"FBCHUNKS"
# Dynasty saves use the default-compression header (78 9c); the college profile
# (PROFILE-COLLEGE) uses best-compression (78 da). Accept every standard variant.
_ZLIB_HEADERS = (b"\x78\x9c", b"\x78\xda", b"\x78\x5e", b"\x78\x01")


def _find_zlib(raw: bytes, start: int = 8) -> int:
    hits = [i for i in (raw.find(h, start) for h in _ZLIB_HEADERS) if i != -1]
    return min(hits) if hits else -1


@dataclass(frozen=True)
class Container:
    """The decoded outer container of a CFB 27 save."""

    version: int
    saved_at: datetime | None
    build_id: str
    payload: bytes  # the inflated FrTk object graph
    compressed_len: int
    zlib_offset: int

    @property
    def is_cfb27(self) -> bool:
        return self.payload[:4] == b"FrTk"


def peek(source: str | Path) -> tuple[int, datetime | None, str] | None:
    """Read (version, saved_at, build_id) from a container's header without
    inflating the payload. Returns None when the file is not FBCHUNKS. Cheap
    enough to run over a whole saves folder on every scan."""
    try:
        with Path(source).open("rb") as fh:
            head = fh.read(192)
    except OSError:
        return None
    if head[:8] != MAGIC:
        return None
    try:
        version = struct.unpack_from("<H", head, 8)[0]
    except struct.error:
        return None
    return version, _read_timestamp(head, 22), _read_cstr(head, 34)


def is_fbchunks(source: str | Path | bytes) -> bool:
    """True if the source looks like an FBCHUNKS container (magic sniff only)."""
    if isinstance(source, (bytes, bytearray)):
        return bytes(source[:8]) == MAGIC
    try:
        with Path(source).open("rb") as fh:
            return fh.read(8) == MAGIC
    except OSError:
        return False


def decode(source: str | Path | bytes) -> Container:
    """Decode an FBCHUNKS container into its inflated payload + header metadata.

    Accepts a path or the raw bytes. Raises ValueError if the magic is wrong and
    zlib.error if the compressed stream is corrupt.
    """
    raw = bytes(source) if isinstance(source, (bytes, bytearray)) else Path(source).read_bytes()
    if raw[:8] != MAGIC:
        raise ValueError(f"not an FBCHUNKS save (magic={raw[:8]!r})")

    version = struct.unpack_from("<H", raw, 8)[0]
    saved_at = _read_timestamp(raw, 22)
    build_id = _read_cstr(raw, 34)

    z = _find_zlib(raw)
    if z == -1:
        raise ValueError("no zlib stream found in FBCHUNKS container")
    d = zlib.decompressobj()
    payload = d.decompress(raw[z:])
    payload += d.flush()
    compressed_len = (len(raw) - z) - len(d.unused_data)

    return Container(
        version=version,
        saved_at=saved_at,
        build_id=build_id,
        payload=payload,
        compressed_len=compressed_len,
        zlib_offset=z,
    )


def encode(original: bytes, payload: bytes, *, saved_at: datetime | None = None) -> bytes:
    """Rebuild an FBCHUNKS save around a (patched) payload.

    The header carries no checksum (verified across real saves); the only
    fields that track the stream are the u32 LE compressed length and the
    timestamp. Everything else is copied verbatim from `original`, the new
    zlib stream replaces the old one, and the file is zero-padded back to the
    original fixed slot size. Raises ValueError if the original header cannot
    be understood or the new stream does not fit the slot.
    """
    if original[:8] != MAGIC:
        raise ValueError("original is not an FBCHUNKS save")
    z = _find_zlib(original)
    if z == -1:
        raise ValueError("original has no zlib stream")
    d = zlib.decompressobj()
    d.decompress(original[z:])
    d.flush()
    old_len = (len(original) - z) - len(d.unused_data)

    # locate the compressed-length field by its current value (header layout
    # verification, not an assumption about a fixed offset)
    header = bytearray(original[:z])
    needle = struct.pack("<I", old_len)
    at = header.find(needle, 8)
    if at == -1 or header.find(needle, at + 1) != -1:
        raise ValueError("could not locate a unique compressed-length header field")

    stream = zlib.compress(payload, 6)
    if z + len(stream) > len(original):
        raise ValueError("patched payload compresses larger than the save slot")
    struct.pack_into("<I", header, at, len(stream))
    if saved_at is not None:
        struct.pack_into("<6H", header, 22, saved_at.year, saved_at.month, saved_at.day,
                         saved_at.hour, saved_at.minute, saved_at.second)
    return bytes(header) + stream + b"\x00" * (len(original) - z - len(stream))


def _read_timestamp(raw: bytes, off: int) -> datetime | None:
    try:
        y, mo, d, h, mi, s = struct.unpack_from("<6H", raw, off)
    except struct.error:
        return None
    if not (2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31 and h < 24 and mi < 60 and s < 60):
        return None
    try:
        return datetime(y, mo, d, h, mi, s)
    except ValueError:
        return None


def _read_cstr(raw: bytes, off: int, limit: int = 128) -> str:
    end = raw.find(b"\x00", off, off + limit)
    if end == -1:
        end = off + limit
    return raw[off:end].decode("latin1", errors="replace")
