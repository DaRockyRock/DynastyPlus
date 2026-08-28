"""Tests for the Frostbite bundle readers (backend.assets.frostbite)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.assets.frostbite import dbobject, toc


def _leb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | 0x80 if n else b)
        if not n:
            return bytes(out)


def _string(s: str) -> bytes:
    body = s.encode("latin1") + b"\x00"
    return _leb(len(body)) + body


def _obj(fields: list[tuple[str, int, bytes]]) -> bytes:
    body = b"".join(bytes([tb]) + name.encode() + b"\x00" + val for name, tb, val in fields) + b"\x00"
    return _leb(len(body)) + body


def _list(elements: list[tuple[int, bytes]]) -> bytes:
    body = b"".join(bytes([tb]) + val for tb, val in elements) + b"\x00"
    return _leb(len(body)) + body


def test_read_payload_strips_dice_header():
    raw = toc.MAGIC_PREFIX + b"\x01" + b"\x00" * (toc.HEADER_LEN - 4) + b"PAYLOAD"
    assert toc.is_toc(raw)
    assert toc.read_payload(raw) == b"PAYLOAD"
    assert not toc.is_toc(b"{json}")


def test_dbobject_roundtrip():
    tags = _list([(0x80 | dbobject.STRING, _string("a")),
                  (0x80 | dbobject.STRING, _string("b"))])
    payload = bytes([0x80 | dbobject.OBJECT]) + _obj([
        ("title", dbobject.STRING, _string("Hello")),
        ("count", dbobject.INT32, (7).to_bytes(4, "little")),
        ("flag", dbobject.BOOL, b"\x01"),
        ("tags", dbobject.LIST, tags),
    ])
    tree = dbobject.parse(payload)
    assert tree == {"title": "Hello", "count": 7, "flag": True, "tags": ["a", "b"]}


def test_dbobject_unknown_type_raises():
    payload = bytes([0x80 | dbobject.OBJECT]) + _obj([("x", 0x7A, b"")])
    with pytest.raises(dbobject.DbParseError):
        dbobject.parse(payload)


def _game_dir() -> Path | None:
    env = os.environ.get("CFB27_GAME")
    if env:
        return Path(env)
    default = Path(r"C:\Program Files (x86)\Steam\steamapps\common\College Football 27")
    return default if default.exists() else None


@pytest.mark.skipif(_game_dir() is None, reason="set CFB27_GAME to the install dir to run")
def test_real_layout_toc_parses():
    layout = _game_dir() / "Data" / "layout.toc"
    tree = dbobject.parse(toc.read_payload(layout))
    assert isinstance(tree["superBundles"], list) and len(tree["superBundles"]) > 20
    names = [s["name"] for s in tree["superBundles"]]
    assert any(n.endswith("imageassetlibrarysb") for n in names)
    assert "installManifest" in tree
