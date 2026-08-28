"""Parse the Frostbite DbObject tree used by CFB 27's layout.toc.

Encoding (reversed from layout.toc, big-endian game but LEB128 sizes):

    element := type_byte [name cstring] value
      * bit 0x80 of type_byte CLEAR  -> element is a named field (read a
        NUL-terminated name next); SET -> no name (root + list elements).
      * low 7 bits = value type.

    value by type:
      0x01 List    : LEB128 byte-size, then elements until a 0x00 type byte
      0x02 Object  : LEB128 byte-size, then named fields until a 0x00 type byte
      0x06 Bool    : 1 byte
      0x07 String  : LEB128 length, then that many bytes (trailing NUL included)
      0x08 Int64   : 8 bytes LE
      0x0f GUID    : 16 bytes
      0x10 SHA1    : 20 bytes
      0x13 Blob    : LEB128 length, then that many bytes

Unknown types raise DbParseError with context so the type map can be extended.
"""
from __future__ import annotations


class DbParseError(Exception):
    pass


LIST = 0x01
OBJECT = 0x02
BOOL = 0x06
STRING = 0x07
INT32 = 0x08
INT64 = 0x09
GUID = 0x0F
SHA1 = 0x10
BLOB = 0x13


def _leb(buf: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _cstr(buf: bytes, pos: int) -> tuple[str, int]:
    end = buf.index(0, pos)
    return buf[pos:end].decode("latin1"), end + 1


def _context(buf: bytes, pos: int) -> str:
    lo = max(0, pos - 8)
    seg = buf[lo:pos + 16]
    return f"valuepos={pos} bytes={seg.hex()}"


def _value(typ: int, buf: bytes, pos: int):
    if typ == OBJECT:
        size, pos = _leb(buf, pos)
        end = pos + size
        obj: dict = {}
        while pos < end and buf[pos] != 0x00:
            name, val, pos = _element(buf, pos)
            obj[name] = val
        return obj, end  # end includes the 0x00 terminator
    if typ == LIST:
        size, pos = _leb(buf, pos)
        end = pos + size
        arr: list = []
        while pos < end and buf[pos] != 0x00:
            _name, val, pos = _element(buf, pos)
            arr.append(val)
        return arr, end
    if typ == STRING:
        n, pos = _leb(buf, pos)
        return buf[pos:pos + n].split(b"\x00", 1)[0].decode("latin1"), pos + n
    if typ == BLOB:
        n, pos = _leb(buf, pos)
        return buf[pos:pos + n], pos + n
    if typ == BOOL:
        return bool(buf[pos]), pos + 1
    if typ == INT32:
        return int.from_bytes(buf[pos:pos + 4], "little"), pos + 4
    if typ == INT64:
        return int.from_bytes(buf[pos:pos + 8], "little"), pos + 8
    if typ == GUID:
        return buf[pos:pos + 16].hex(), pos + 16
    if typ == SHA1:
        return buf[pos:pos + 20].hex(), pos + 20
    raise DbParseError(f"unknown DbObject type 0x{typ:02x} ({_context(buf, pos)})")


def _element(buf: bytes, pos: int):
    """Return (name_or_None, value, new_pos)."""
    tb = buf[pos]
    pos += 1
    typ = tb & 0x7F
    name = None
    if not (tb & 0x80):
        name, pos = _cstr(buf, pos)
    val, pos = _value(typ, buf, pos)
    return name, val, pos


def parse(payload: bytes):
    """Parse a DbObject payload (as returned by toc.read_payload) into Python."""
    _name, val, _pos = _element(payload, 0)
    return val
