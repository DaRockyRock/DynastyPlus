"""National rankings from the FrTk payload.

Decoded 2026-07-07: the save keeps the polls as PER-TEAM RANK FIELDS in the
`TeamStore` record store (143 records x 788 bytes, rows in teams.parse_teams
order), NOT as ranked lists. Each field ranks EVERY team (a full 1..~138
ordering, not just a top 25); the game only displays the head of the list.
That is why a bracket larger than 25 teams can be seeded straight from the
save: teams "outside the top 25" still carry a real, record-based rank.

Verified offsets (validated against in-game screenshots from two dynasties):

    +699  u8   the CFP committee ranking. Matches the game's "Top 25
               Rankings" screen exactly (25/25) in the Missouri State save
               and the playoff seeds in the Nebraska save. This drives
               selection + seeding. (+694 is byte-identical in every save
               observed, so it is read as the same poll / a safe alias.)
    +674  u16BE the AP-style media poll. Agrees with the committee late in
               the Nebraska save but diverges earlier (e.g. Texas A&M over
               Ohio State at #1 in the Missouri State save), so it must NOT
               be used for playoff seeding, only surfaced as AP flavor.
    +689  u8   a preseason / program-strength index (blue-bloods by pedigree
               regardless of record); not a live poll.

Every team always carries a rank, so "top 25" is simply rank in 1..25.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

_TEAMSTORE_ANCHOR = b"\x00\x09TeamStore\x00"
CFP_RANK_OFF = 699      # u8  - the committee ranking (drives seeding)
CFP_ALIAS_OFF = 694     # u8  - byte-identical committee alias (kept in step)
AP_RANK_OFF = 674       # u16 BE - the AP-style media poll (flavor only)
POWER_INDEX_OFF = 689   # u8  - preseason / program-strength index

# the polls the editor can read and write, keyed the way the API exposes them
POLLS = ("cfp", "ap")


@dataclass(frozen=True)
class TeamRanks:
    row: int
    rank: int          # the CFP committee ranking (drives selection + seeding)
    ap_rank: int       # the AP-style media poll (flavor)
    power_index: int   # preseason / program-strength index


def _store(payload: bytes) -> tuple[int, int, int]:
    at = payload.find(_TEAMSTORE_ANCHOR)
    if at == -1:
        raise ValueError("TeamStore not found")
    bsft = payload.find(b"BSFT", at, at + 400)
    if bsft == -1:
        raise ValueError("TeamStore: BSFT header not found")
    w = struct.unpack_from(">6I", payload, bsft + 4)
    count, fields = w[3], w[4] + 1
    rec0 = bsft + 4 + 24 + fields * 4
    stride = (w[0] - 28 - fields * 4) // count
    return rec0, stride, count


def parse(payload: bytes) -> list[TeamRanks]:
    """Every team's current ranks, indexed by team row."""
    rec0, stride, count = _store(payload)
    out = []
    for row in range(count):
        base = rec0 + row * stride
        out.append(TeamRanks(
            row=row,
            rank=payload[base + CFP_RANK_OFF],
            ap_rank=struct.unpack_from(">H", payload, base + AP_RANK_OFF)[0],
            power_index=payload[base + POWER_INDEX_OFF],
        ))
    return out


def rank_of(team: TeamRanks, poll: str) -> int:
    """The team's rank in the given poll ('cfp' or 'ap'); 0 = unranked."""
    return team.rank if poll == "cfp" else team.ap_rank


def poll_order(payload: bytes, poll: str = "cfp") -> list[int]:
    """Team rows in the given poll's order, best first (ranked rows only; a
    rank of 0 means the row is an unranked placeholder and stays out)."""
    ranked = [t for t in parse(payload) if rank_of(t, poll) > 0]
    return [t.row for t in sorted(ranked, key=lambda t: rank_of(t, poll))]


def set_poll_order(payload: bytearray, order: list[int],
                   poll: str = "cfp") -> list[str]:
    """Write a FULL poll ordering in place: order[i] is the team row ranked
    i+1.

    These fields are full 1..N orderings over every real team, not top-25
    lists (see the module docstring), so the write keeps them a permutation:
    `order` must contain exactly the rows the save currently ranks in this
    poll, once each. Rows the save leaves at rank 0 (dead/placeholder rows)
    are never touched. The committee write covers both +699 and its +694
    alias so the two stay byte-identical, the shape every observed save
    carries."""
    if poll not in POLLS:
        raise ValueError(f"unknown poll: {poll!r}")
    rec0, stride, count = _store(bytes(payload))
    current = parse(bytes(payload))
    ranked = {t.row for t in current if rank_of(t, poll) > 0}
    if len(order) != len(set(order)):
        raise ValueError("poll order contains a duplicate team row")
    if set(order) != ranked:
        missing = sorted(ranked - set(order))
        extra = sorted(set(order) - ranked)
        raise ValueError(
            "poll order must cover exactly the save's ranked rows "
            f"(missing {missing[:5]}{'...' if len(missing) > 5 else ''}, "
            f"extra {extra[:5]}{'...' if len(extra) > 5 else ''})")
    changed = 0
    for i, row in enumerate(order):
        rank = i + 1
        base = rec0 + row * stride
        if poll == "cfp":
            if rank > 0xFF:
                raise ValueError(f"committee rank {rank} exceeds a u8")
            if payload[base + CFP_RANK_OFF] != rank:
                changed += 1
            payload[base + CFP_RANK_OFF] = rank
            payload[base + CFP_ALIAS_OFF] = rank
        else:
            if rank > 0xFFFF:
                raise ValueError(f"AP rank {rank} exceeds a u16")
            if struct.unpack_from(">H", payload, base + AP_RANK_OFF)[0] != rank:
                changed += 1
            struct.pack_into(">H", payload, base + AP_RANK_OFF, rank)
    return [f"{poll} poll: full ordering written "
            f"({changed} of {len(order)} team ranks changed)"]


def swap_committee_rank(payload: bytearray, row_a: int, row_b: int) -> list[str]:
    """Swap two teams' CFP committee ranks in place (+699 and its +694 alias).

    The engine's own 12-team playoff selection at the week-advance boundary
    is driven by this field (verified on a real base: its first round is
    exactly committee ranks 5..12, its byes ranks 1..4). Swapping the user
    into that window BEFORE the boundary makes the engine schedule the
    user's playoff game itself, with all of its own opaque user wiring (the
    only thing that makes a game playable from the dynasty hub; fabricated
    queue wiring alone reads as a bye, three in-game tests). The caller
    records the swap, seeds the CUSTOM bracket from the real ranking, and
    restores the real ranks in later writes."""
    rec0, stride, count = _store(bytes(payload))
    if not (0 <= row_a < count and 0 <= row_b < count):
        raise ValueError(f"team rows out of range: {row_a}, {row_b}")
    for off in (CFP_RANK_OFF, CFP_ALIAS_OFF):
        a = rec0 + row_a * stride + off
        b = rec0 + row_b * stride + off
        payload[a], payload[b] = payload[b], payload[a]
    return [f"committee rank swapped: team row {row_a} <-> team row {row_b}"]


def home_stadium_handle(payload: bytes, team_row: int) -> int | None:
    """The team's home stadium uid handle (TeamStore +152; verified against
    the Stadium[] table, 138/143 rows). Used to pin a game to a specific
    campus when the record's home slot cannot hold the intended host (the
    user's engine-scheduled side must be preserved)."""
    rec0, stride, count = _store(payload)
    if not 0 <= team_row < count:
        return None
    v = struct.unpack_from(">I", payload, rec0 + team_row * stride + 152)[0]
    return v if v >> 24 == 0x80 else None


def order(payload: bytes) -> list[int]:
    """Team rows in CFP-committee-ranking order, best first (ranked teams
    only; a rank of 0 means the team is unranked/placeholder)."""
    ranked = [t for t in parse(payload) if t.rank > 0]
    return [t.row for t in sorted(ranked, key=lambda t: t.rank)]
