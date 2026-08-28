"""Small big-endian-default binary reader used by the Frostbite parsers."""
from __future__ import annotations

import struct
import uuid


class Reader:
    __slots__ = ("buf", "pos")

    def __init__(self, buf: bytes, pos: int = 0):
        self.buf = buf
        self.pos = pos

    def seek(self, pos: int) -> None:
        self.pos = pos

    def skip(self, n: int) -> None:
        self.pos += n

    def read(self, n: int) -> bytes:
        out = self.buf[self.pos:self.pos + n]
        if len(out) != n:
            raise EOFError(f"wanted {n} bytes at {self.pos}, got {len(out)}")
        self.pos += n
        return out

    def u8(self) -> int:
        v = self.buf[self.pos]
        self.pos += 1
        return v

    def u16(self, be: bool = True) -> int:
        return struct.unpack_from(">H" if be else "<H", self.buf, self._adv(2))[0]

    def u32(self, be: bool = True) -> int:
        return struct.unpack_from(">I" if be else "<I", self.buf, self._adv(4))[0]

    def i32(self, be: bool = True) -> int:
        return struct.unpack_from(">i" if be else "<i", self.buf, self._adv(4))[0]

    def u64(self, be: bool = True) -> int:
        return struct.unpack_from(">Q" if be else "<Q", self.buf, self._adv(8))[0]

    def i64(self, be: bool = True) -> int:
        return struct.unpack_from(">q" if be else "<q", self.buf, self._adv(8))[0]

    def cstr(self) -> str:
        end = self.buf.index(0, self.pos)
        out = self.buf[self.pos:end].decode("latin1")
        self.pos = end + 1
        return out

    def guid(self, be: bool = True) -> str:
        """Read a .NET-layout GUID (Data1/2/3 endian-dependent, 8 raw bytes)."""
        d1 = self.u32(be)
        d2 = self.u16(be)
        d3 = self.u16(be)
        rest = self.read(8)
        return str(uuid.UUID(fields=(d1, d2, d3, rest[0], rest[1], int.from_bytes(rest[2:], "big"))))

    def _adv(self, n: int) -> int:
        p = self.pos
        if p + n > len(self.buf):
            raise EOFError(f"wanted {n} bytes at {p}")
        self.pos += n
        return p


def guid_from_dotnet_bytes(raw: bytes) -> str:
    """Interpret 16 bytes the way .NET's Guid(byte[]) does (LE first three fields)."""
    r = Reader(raw)
    return r.guid(be=False)
