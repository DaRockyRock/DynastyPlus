"""Tests for the CFB 27 save container decoder (`backend.saveparse`)."""
import os
import struct
import zlib
from datetime import datetime
from pathlib import Path

import pytest

from backend.saveparse import cfb27, container, teams


def _build_fbchunks(payload: bytes, *, version: int = 1,
                    saved_at: datetime = datetime(2026, 7, 6, 13, 42, 47),
                    build_id: str = "College-27-RL1-9039126") -> bytes:
    """Assemble a synthetic FBCHUNKS container mirroring the real header layout."""
    buf = bytearray(82)
    buf[0:8] = container.MAGIC
    struct.pack_into("<H", buf, 8, version)
    struct.pack_into("<6H", buf, 22, saved_at.year, saved_at.month, saved_at.day,
                     saved_at.hour, saved_at.minute, saved_at.second)
    b = build_id.encode("latin1")
    buf[34:34 + len(b)] = b
    buf[34 + len(b)] = 0  # NUL terminator
    stream = zlib.compress(payload, 6)
    assert stream[:2] == b"\x78\x9c"
    assert b"\x78\x9c" not in bytes(buf[8:]), "header must not contain a false zlib header"
    return bytes(buf) + stream + b"\x00" * 4096  # trailing zero padding like the real file


def test_roundtrip_header_and_payload():
    payload = b"FrTk" + b"\x00\x00\x00\x80" + b"hello dynasty" * 100
    c = container.decode(_build_fbchunks(payload))
    assert c.version == 1
    assert c.saved_at == datetime(2026, 7, 6, 13, 42, 47)
    assert c.build_id == "College-27-RL1-9039126"
    assert c.payload == payload
    assert c.is_cfb27
    assert c.compressed_len > 0


def test_is_fbchunks_sniff():
    good = _build_fbchunks(b"FrTk" + b"x" * 10)
    assert container.is_fbchunks(good)
    assert container.is_fbchunks(good[:8])
    assert not container.is_fbchunks(b'{"season": {}}')
    assert not container.is_fbchunks(b"")


def test_decode_rejects_non_fbchunks():
    with pytest.raises(ValueError):
        container.decode(b'{"not": "a save"}')


def test_cfb27_decode_requires_frtk():
    with pytest.raises(ValueError):
        cfb27.decode(_build_fbchunks(b"NOPE" + b"x" * 10))


def test_iter_strings_and_grep():
    payload = b"FrTk" + b"\x00" * 4 + b"Crimson Tide\x00\x00Tide\x00\x00BAMA\x00"
    found = dict(cfb27.iter_strings(payload, min_len=4))
    assert "Crimson Tide" in found.values()
    hits = cfb27.grep(payload, "Tide")
    assert any("Tide" in text for _, text in hits)


def test_read_save_returns_none_until_mapping_built(tmp_path: Path):
    # container decodes, but to_dynasty is not implemented yet -> graceful None
    save = tmp_path / "DYNASTY-TEST-AUTOSAVE"
    save.write_bytes(_build_fbchunks(b"FrTk" + b"\x00" * 32))
    assert cfb27.read_save(str(save)) is None
    # non-existent path is also None, not an error
    assert cfb27.read_save(str(tmp_path / "missing")) is None


def _team_record(school: str, abbr: str, nick: str, brand: str, slug: str) -> bytes:
    """A synthetic 503-byte team record with the real field offsets (key at +300)."""
    rec = bytearray(teams.RECORD_STRIDE)

    def put(off: int, s: str) -> None:
        rec[off:off + len(s)] = s.encode("latin1")

    put(300 + teams._OFF_SCHOOL, school)     # -227
    put(300 + teams._OFF_ABBR, abbr)         # -204
    put(300 + teams._OFF_NICK, nick)         # -146
    put(300 + teams._OFF_ABBR_ALT, brand)    # -77
    put(300, "teamdb_" + slug)               # key
    return bytes(rec)


def test_parse_teams_synthetic():
    payload = (b"FrTk" + b"\x00" * 8
               + _team_record("Alabama", "ALA", "Crimson Tide", "BAMA", "bama")
               + _team_record("Michigan", "", "Wolverines", "MICH", "mich")   # blank -204 -> brand
               + _team_record("Practice", "", "", "", "practice"))            # skipped
    ts = teams.parse_teams(payload)
    assert [t.slug for t in ts] == ["bama", "mich"]
    bama = ts[0]
    assert bama.school == "Alabama"
    assert bama.abbreviation == "ALA"
    assert bama.nickname == "Crimson Tide"
    assert bama.name == "Alabama Crimson Tide"
    assert ts[1].abbreviation == "MICH"  # fell back to brand code
    assert ts[1].to_schema()["name"] == "Michigan Wolverines"


@pytest.mark.skipif(not os.environ.get("CFB27_SAVE"), reason="set CFB27_SAVE to a real autosave to run")
def test_real_save_decodes():
    c = cfb27.decode(os.environ["CFB27_SAVE"])
    assert c.is_cfb27
    assert c.version >= 1
    assert len(c.payload) > 1_000_000
    assert c.build_id.startswith("College-27")


@pytest.mark.skipif(not os.environ.get("CFB27_SAVE"), reason="set CFB27_SAVE to a real autosave to run")
def test_real_save_teams():
    c = cfb27.decode(os.environ["CFB27_SAVE"])
    ts = teams.parse_teams(c.payload)
    assert len(ts) >= 130
    assert len({t.slug for t in ts}) == len(ts)  # unique keys
    by = {t.slug: t for t in ts}
    assert by["bama"].school == "Alabama"
    assert by["bama"].nickname == "Crimson Tide"
    assert by["bama"].abbreviation == "ALA"
    assert by["mich"].abbreviation == "MICH"
    # every non-generic team resolves an abbreviation
    assert all(t.abbreviation for t in ts if not t.slug.startswith("fcs"))
