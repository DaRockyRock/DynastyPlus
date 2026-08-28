"""Regression tests for per-build FrTk type-tag discovery."""
from __future__ import annotations

import struct

from backend.saveparse import conferences, schedule, tags
from test_saveparse_conferences import build_payload


RL2 = {
    tags.RL1.conf: 0x3124,
    tags.RL1.div: 0x3188,
    tags.RL1.divlist: 0x3186,
    tags.RL1.div_ref: 0x3122,
    tags.RL1.team: 0x3182,
}


def _retag(payload: bytes, mapping: dict[int, int]) -> bytes:
    """Rewrite aligned type halfwords in the synthetic RL1 fixture."""
    out = bytearray(payload)
    # Some synthetic stores begin on a two-byte rather than four-byte boundary,
    # so inspect every aligned halfword. This is test-fixture conversion only.
    for off in range(0, len(out) - 1, 2):
        value = struct.unpack_from(">H", out, off)[0]
        replacement = mapping.get(value)
        if replacement is not None:
            struct.pack_into(">H", out, off, replacement)
    return bytes(out)


def test_rl2_conference_and_team_tags_are_discovered_from_the_payload():
    """The July 16 schema shift must not turn Team refs into Division refs."""
    tags._cache.clear()
    payload = _retag(build_payload(), RL2)

    found = tags.for_payload(payload)
    assert found.conf == 0x3124
    assert found.div == 0x3188
    assert found.divlist == 0x3186
    assert found.div_ref == 0x3122
    assert found.team == 0x3182
    # Tags with no store evidence inherit the measured 0x31xx cluster shift.
    assert found.game == 0x317A
    assert found.unpublished == 0x3198

    table = conferences.parse(payload)
    assert table.writable_membership, table.notes
    assert table.by_name("ACC").team_rows == [0, 1, 2, 3]
    assert table.by_name("Big_Ten").team_rows == [12, 13, 14, 15]


def test_tag_cache_pins_and_identity_checks_its_source(monkeypatch):
    """Equal-length save objects never inherit another object's schema tags."""
    tags._cache.clear()
    calls: list[bytes] = []

    def derive(payload):
        calls.append(payload)
        return tags.RL1 if payload[0] == 1 else tags.SaveTags(
            conf=0x3124, div=0x3188, divlist=0x3186, div_ref=0x3122,
            team=0x3182, game=0x317A, unpublished=0x3198,
            bowl=0x21BC, conf_ref=0x218E, user=0x21E4,
        )

    monkeypatch.setattr(tags, "_derive", derive)
    first = bytes([1, 0, 0, 0])
    second = bytes([2, 0, 0, 0])

    assert tags.for_payload(first) is tags.RL1
    assert tags.for_payload(first) is tags.RL1
    assert tags.for_payload(second).team == 0x3182
    assert calls == [first, second]
    assert tags._cache[id(first)][0] is first
    assert tags._cache[id(second)][0] is second


def test_schedule_result_flag_is_a_real_boolean(monkeypatch):
    """The public Game model promises bool, not the raw 0x10 bit value."""
    monkeypatch.setattr(tags, "for_payload", lambda _payload: tags.RL1)
    record = bytearray(schedule.RECORD_SIZE)
    struct.pack_into(">I", record, 8, (tags.RL1.team << 16) | 1)
    struct.pack_into(">I", record, 36, (tags.RL1.team << 16) | 2)
    struct.pack_into(">I", record, 52, 0x80000001)
    record[97] = 0x11

    game = schedule.parse_game(bytes(record), 0, 0)
    assert game.has_result is True
    assert game.official is True
