"""Season schedule / results / postseason structures in the FrTk payload.

Reverse-engineered 2026-07-07 from four saves of one dynasty (preseason,
rivalry week, bowl week 1, bowl week 2) plus screenshot ground truth (final
scores, CFP seeds, records). See docs/cfb27-schedule-format.md for the field
research trail.

The season schedule is the `SeasonGameStore` SPBF block (~27.1 MB): 983
records x 100 bytes, one per game slot for the CURRENT season. All values are
big-endian; several fields are typed refs `(tag << 16) | row` as elsewhere in
the save (see conferences.py). Scores are bit-packed. Layout (byte offsets):

    +0    u32  UnpublishedGameStats ref (0x3192|n) while the engine holds a
               pre-simmed, not-yet-official result; in a FREE record (never
               activated) +0 is a small int chaining to the next free record.
    +4    u32  NEUTRAL-SITE stadium uid (0x80xxxxxx opaque venue handle);
               0 = campus game at the home team's stadium. Bowls, New Year's
               Six rounds, the NCG, and neutral CCGs carry one. The six CFP
               bowl venues are the stadium uids in the PlayoffBowlsInfo
               store (bowls.py); writing a different uid here MOVES the game.
    +8    u32  AWAY team ref (0x317C|teamRow); 0 = TBD
    +12   u32  away TeamStats ref (0x2024|n) once locked for play
    +16   u32  BowlGame ref (0x21B2|bowlRow) for bowl/playoff games, else 0
    +24   u32  ScoringSummary ref (0x2E44|n) while pre-simmed
    +32   u32  second UnpublishedGameStats ref while pre-simmed
    +36   u32  HOME team ref;  +40 home TeamStats ref
    +44   u32  Injury-list ref (0x318E|n) while pre-simmed
    +48   f32  unknown float (spread/win-prob-like; often 0)
    +52   u32  AwayRequestId: 0x7FFFFFFF none, 0x8000xxxx allocated
    +56   u32  0x80000000 once initialized
    +60   u32  HomeRequestId (allocated with +52 at the week boundary)
    +68   u32  bit-packed; low ~20 bits are attendance
    +76   bits 609..615 (7)  HOME final score
    +77   bits 617..623 (7)  AWAY final score
    +94   u16, bits 5..8 hold the game's SEASON WEEK (0-based; 0 = the
          kickoff week the profile shows as "Week 1", 13 = rivalry week,
          14 = the Army-Navy week). Decoded 2026-07-11 and verified across
          six saves of three dynasties: official results are exactly weeks
          0..N-1, the engine's pre-simmed set and its SeasonGameRequest
          queue are exactly week N, and no FBS team appears twice in a week
          (only the five FCS placeholder rows repeat). Engine-created
          postseason records (CCGs, bowls, CFP) leave the field 0, so it is
          meaningful only for regular-season records. READ-ONLY for the
          companion: the schedule editor rewrites team refs within a week's
          existing records and never moves a record between weeks.
    +97   bit 0x01  result is OFFICIAL (week advanced past the game);
          bit 0x10  result exists (the engine PRE-SIMS a week's games when
          the week begins, before the user advances);
          bit 0x20  bracket game not yet created (SF/NCG before their
          participants are known)

Scores were validated against known final records (Nebraska 5-6, Oregon 12-2
with per-game log, Texas A&M 10-2) and known CFP first-round/CCG winners.

Record ranges are per dynasty, not fixed: bowls and playoff games are found
by their BowlInfo refs; conference championships by "played after the regular
season with no bowl ref"; free records by the +0 free chain.

THE WEEK SLATE (`SeasonGameRequest`, decoded 2026-07-08). Game records carry
no week field; the CURRENT week's slate lives in the SeasonGameRequest SPBF
store: two request rows per game, each holding a game-record ref (0x3174|row)
at +32. The queue is allocated at the week-ADVANCE boundary, before the engine
locks/pre-sims the week in-session, so it is present even in the pre-lock
arrival autosave (verified: bowl week 1 of dynasty 2543439794, 56 rows = the
exact 28 records the engine later locked). Slate membership also shows at the
record level pre-lock: bytes 98/99 carry a boundary marker (0x1c01 bowls /
0x1c02 CFP rounds) instead of the dormant unplayed pattern (0x1d2d). Those
marker bytes belong to the ENGINE's week machinery: a matchup patch applied to
a pre-lock save must leave bytes 76..99 alone. A locked record uses
`reset_locked_matchup_status`, which preserves its engine-issued requests.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from . import tags as savetags

# The launch-build (RL1) tag values, kept as the BASELINE the synthetic test
# fixtures are built with. Game patches renumber the FrTk type table (the
# 2026-07-16 RL2 patch moved every one of these), so runtime reads/writes
# resolve the payload's actual tags through saveparse.tags.for_payload.
TEAM_REF = savetags.RL1.team
BOWL_REF = savetags.RL1.bowl
UNPUBLISHED_REF = savetags.RL1.unpublished
GAME_REF = savetags.RL1.game    # a SeasonGameStore record ref (SeasonGameRequest)
USER_REF = savetags.RL1.user    # member/user ref in a user-typed request row

_STORE_NAME = b"SeasonGameStore\x00"
_PRACTICE_STORE = b"PracticeSeasonGameStore\x00"
RECORD_SIZE = 100
NO_RESULT = 0x7FFFFFFF


def _dynamic_result_ref(value: int) -> bool:
    return value >> 16 == 0x8000


def request_id_pair(payload: bytes, game: "Game") -> tuple[int, int]:
    """Raw AwayRequestId/HomeRequestId values for one SeasonGame.

    The 468_2 schema confirms these are engine-issued request identities, not
    transferable object references. Their backing requests are created only
    when CFB crosses a week boundary.
    """
    return (struct.unpack_from(">I", payload, game.offset + 52)[0],
            struct.unpack_from(">I", payload, game.offset + 60)[0])


def request_id_pair_complete(payload: bytes, game: "Game") -> bool:
    """Whether both participants received engine-issued request IDs."""
    away, home = request_id_pair(payload, game)
    return _dynamic_result_ref(away) and _dynamic_result_ref(home)


def request_id_pair_partial(payload: bytes, game: "Game") -> bool:
    """Whether exactly one participant received a request ID.

    CFB 27 creates this shape when a future CFP record contains only its bye
    seed at the week boundary. Adding the other participant afterward makes
    the matchup visible and playable, but the post-game flow cannot publish
    the result because the second engine request does not exist. The safe
    repair is to return to the prior week, stage both teams, and cross the
    boundary again. Copying another game's numeric IDs cannot create requests.
    """
    away, home = request_id_pair(payload, game)
    return _dynamic_result_ref(away) != _dynamic_result_ref(home)


# Compatibility aliases for callers written before the schema field names
# were confirmed. New code should use request_id_pair*.
result_pair_refs = request_id_pair
result_pair_complete = request_id_pair_complete
result_pair_partial = request_id_pair_partial


@dataclass
class Game:
    index: int                 # record row in the store
    away_row: int | None       # team row (teams.parse_teams order) or None=TBD
    home_row: int | None
    bowl_row: int | None       # BowlInfo row for bowls/playoff games
    away_score: int | None     # None until a result exists
    home_score: int | None
    official: bool             # result published (week advanced past it)
    has_result: bool           # engine result exists (may be pre-simmed!)
    presimmed: bool            # unpublished pre-simmed stats attached (+0 ref)
    scheduled: bool            # both teams set
    attendance: int | None
    result_slot: int | None    # request id; allocated in play order, a chronology proxy
    venue_uid: int | None      # neutral-site stadium uid (+4); None = campus game
    sched_week: int = 0        # 0-based season week from +94 (regular season
                               # records only; engine-created postseason
                               # records leave it 0, so gate on bowl/CCG first)
    kickoff_raw: int = 0       # u16 at +68 (day/time slot metadata; opaque,
                               # kept with the record, used only for display)
    # writer internals
    offset: int = 0            # absolute offset of this record in the payload

    @property
    def winner_row(self) -> int | None:
        if not self.has_result or self.away_score is None or self.home_score is None:
            return None
        if self.away_score == self.home_score:
            return None
        return self.away_row if self.away_score > self.home_score else self.home_row

    @property
    def loser_row(self) -> int | None:
        w = self.winner_row
        if w is None:
            return None
        return self.home_row if w == self.away_row else self.away_row


@dataclass
class GameStore:
    games: list[Game]
    records_off: int           # absolute offset of record 0
    count: int

    def by_team(self, team_row: int, *, official_only: bool = True) -> list[Game]:
        out = []
        for g in self.games:
            if team_row in (g.away_row, g.home_row) and g.scheduled:
                if g.has_result and (g.official or not official_only):
                    out.append(g)
        return out

    def record(self, team_row: int, *, official_only: bool = True) -> tuple[int, int]:
        w = l = 0
        for g in self.by_team(team_row, official_only=official_only):
            if g.winner_row == team_row:
                w += 1
            elif g.loser_row == team_row:
                l += 1
        return w, l


def _bits(rec: bytes, off: int, width: int) -> int:
    val = 0
    for i in range(width):
        b = off + i
        val = (val << 1) | ((rec[b >> 3] >> (7 - (b & 7))) & 1)
    return val


def _ref(rec: bytes, off: int, tag: int) -> int | None:
    v = struct.unpack_from(">I", rec, off)[0]
    return (v & 0xFFFF) if (v >> 16) == tag else None


def locate(payload: bytes) -> tuple[int, int]:
    """(absolute offset of record 0, record count) of the SeasonGameStore.

    The name also appears inside `PracticeSeasonGameStore`; the real store is
    the occurrence NOT preceded by 'Practice'. Record 0 is found by the first
    team ref after the header (the BSFT field table has no 0x317C values)."""
    at = -1
    i = payload.find(_STORE_NAME)
    while i != -1:
        if payload[i - 8:i] != b"Practice":
            at = i
            break
        i = payload.find(_STORE_NAME, i + 1)
    if at == -1:
        raise ValueError("SeasonGameStore not found")
    bsft = payload.find(b"BSFT", at, at + 120)
    if bsft == -1:
        raise ValueError("SeasonGameStore: BSFT header not found")
    data_size = struct.unpack_from(">I", payload, bsft + 4)[0]
    # the field table between BSFT and the records is data_size - count*100;
    # count sits in the header right after the two data sizes
    count = struct.unpack_from(">I", payload, bsft + 16)[0]
    # data_size spans from the BSFT tag to the end of the records, so the
    # records start data_size - count*stride after the tag (verified: the
    # first record's away-team ref lands exactly there)
    rec0 = bsft + (data_size - count * RECORD_SIZE)
    if not 0 < count < 5000:
        raise ValueError(f"SeasonGameStore: implausible record count {count}")
    return rec0, count


def parse_game(payload: bytes, rec0: int, index: int) -> Game:
    t = savetags.for_payload(payload)
    off = rec0 + index * RECORD_SIZE
    rec = payload[off:off + RECORD_SIZE]
    away = _ref(rec, 8, t.team)
    home = _ref(rec, 36, t.team)
    away_res = struct.unpack_from(">I", rec, 52)[0]
    has_result = bool(
        away_res not in (NO_RESULT, 0)
        and (rec[97] & 0x10 or rec[97] & 0x01)
    )
    official = bool(rec[97] & 0x01)
    hs = _bits(rec, 609, 7) if has_result else None
    as_ = _bits(rec, 617, 7) if has_result else None
    att = _bits(rec, 556, 20) if has_result else None  # low 20 bits of +68
    venue = struct.unpack_from(">I", rec, 4)[0]
    return Game(
        index=index,
        away_row=away,
        home_row=home,
        bowl_row=_ref(rec, 16, t.bowl),
        away_score=as_,
        home_score=hs,
        official=official,
        has_result=has_result,
        result_slot=(away_res & 0xFFFF) if has_result else None,
        presimmed=_ref(rec, 0, t.unpublished) is not None,
        scheduled=away is not None and home is not None,
        attendance=att,
        venue_uid=venue if venue >> 24 == 0x80 else None,
        sched_week=(struct.unpack_from(">H", rec, 94)[0] >> 5) & 0xF,
        kickoff_raw=struct.unpack_from(">H", rec, 68)[0],
        offset=off,
    )


def parse(payload: bytes) -> GameStore:
    rec0, count = locate(payload)
    games = [parse_game(payload, rec0, i) for i in range(count)]
    return GameStore(games=games, records_off=rec0, count=count)


# ---------------------------------------------------------------------------
# writing (in-place, same-length record patches)
# ---------------------------------------------------------------------------
# The FBCHUNKS container has no payload checksum (established by the
# conference editor), so in-place record patches + re-encode produce a save
# the game accepts. Every write below verifies the target record first and
# refuses rather than guessing.

def set_matchup(payload: bytearray, game: Game, *,
                away_row: int | None = ..., home_row: int | None = ...) -> list[str]:
    """Point a game record at different teams. `None` clears a slot to TBD;
    `...` leaves that side untouched. Returns report lines.

    Only the team refs are written. If the engine already locked/pre-simmed
    the game for its week, call `clear_engine_state` too, or the record keeps
    a result that belongs to the old matchup.
    """
    team_ref = savetags.for_payload(payload).team
    report = []
    for off, row, label in ((8, away_row, "away"), (36, home_row, "home")):
        if row is ...:
            continue
        current = struct.unpack_from(">I", payload, game.offset + off)[0]
        if current and (current >> 16) != team_ref:
            raise ValueError(f"game {game.index}: {label} slot holds a non-team ref "
                             f"{current:#x}; refusing to overwrite")
        value = 0 if row is None else ((team_ref << 16) | row)
        struct.pack_into(">I", payload, game.offset + off, value)
        report.append(f"game {game.index}: {label} -> {'TBD' if row is None else f'team row {row}'}")
    return report


# byte offsets of the per-week engine state a matchup patch must reset when
# the engine already locked/pre-simmed the game (see module docstring):
# pending refs (+0, +24, +32, +44), participation refs (+12, +40), the
# request IDs (+52/+60 back to the no-result sentinel), and the result bits.
_ENGINE_STATE_ZERO = (0, 12, 24, 32, 40, 44)


def reset_locked_matchup_status(payload: bytearray, game: Game) -> list[str]:
    """Match the working reference tool's locked-week rewrite exactly.

    The alternative 16-team playoff tool changes only three schema fields on
    a SeasonGame it repurposes: ``GameStatus = HomeScheduled``, ``IsSimmed =
    false``, and ``HasBeenPublished = false``. A byte comparison through the
    game's 468_2 schema shows that this preserves every pending, stats, score,
    and participant-request field and changes only byte 84's GameStatus nibble
    plus the two flags at byte 97. Preserving the request IDs is essential:
    copying or clearing them does not create the backing engine requests.
    """
    base = game.offset
    payload[base + 84] = (payload[base + 84] & 0x0F) | 0x60
    payload[base + 97] &= ~0x11 & 0xFF
    return [f"game {game.index}: status reset to HomeScheduled "
            "(reference-tool locked rewrite)"]


def clear_engine_state(payload: bytearray, game: Game) -> list[str]:
    """Reset a locked/pre-simmed game back to the SCHEDULED-UNPLAYED state so
    the engine re-locks and re-sims the new matchup, and the game's UI shows
    it as an upcoming game (kickoff time) rather than a played 0-0 result.

    The byte recipe was derived empirically from 44 scheduled-unplayed
    postseason records across three saves (every byte of +44..99 is constant
    across them except per-record kickoff metadata, which gets safe preseason
    defaults). Play-state markers that must flip back: +73 bit2, +74 bit7 and
    +84 bit5 clear when unplayed; +92 bit3, +93 bits0-1, +94 bit7, +98 bit0
    and the +99 pattern 0x2D set when unplayed; byte 97 = 0 (no result, not
    official). Teams (+8/+36), venue (+4), and the bowl ref (+16) are
    untouched. The pending/participation records the game pointed at remain
    allocated (orphaned) - the engine rebuilds the week's pending set itself.
    """
    base = game.offset
    for off in _ENGINE_STATE_ZERO:
        struct.pack_into(">I", payload, base + off, 0)
    struct.pack_into(">f", payload, base + 48, 0.0)
    struct.pack_into(">I", payload, base + 52, NO_RESULT)
    struct.pack_into(">I", payload, base + 56, 0x80000000)
    struct.pack_into(">I", payload, base + 60, NO_RESULT)
    struct.pack_into(">I", payload, base + 64, 0)
    # +68 high bits are scheduling metadata (survive play, keep); the low 20
    # bits are attendance (zero); +72..75 back to the preseason default
    payload[base + 69] &= 0xF0
    payload[base + 70] = 0
    payload[base + 71] = 0
    payload[base + 72:base + 76] = b"\xb0\x00\x01\xf4"
    # scores + trailing result metadata back to the unplayed pattern
    payload[base + 76:base + 80] = b"\x00\x00\x00\x28"
    # +80 survives play (keep); +81..91 constant when unplayed
    payload[base + 81:base + 92] = b"\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00"
    payload[base + 92] |= 0x08
    payload[base + 93] |= 0x03
    payload[base + 94] |= 0x80
    payload[base + 96] = 0
    payload[base + 97] = 0
    payload[base + 98] = 0x1D
    payload[base + 99] = 0x2D
    return [f"game {game.index}: engine week-state cleared (pending/participation/result)"]


def _put_bits(payload: bytearray, base: int, off: int, width: int, val: int) -> None:
    for i in range(width):
        b = off + i
        idx = base + (b >> 3)
        bit = (val >> (width - 1 - i)) & 1
        payload[idx] = (payload[idx] & ~(1 << (7 - (b & 7)))) | (bit << (7 - (b & 7)))


def swap_result_scores(payload: bytearray, game: Game) -> list[str]:
    """Swap an OFFICIAL game's home/away scores in place (bits 609..623),
    flipping its winner. Nothing else in the record changes.

    Used by the championship-week PREPARE for a user team the engine's
    postseason selection would snub: the boundary recomputes rankings and
    picks its bowl/CFP fields from RESULTS (a planted rank is recomputed
    away, verified in-game), so results are the only lever that survives it.
    The caller records the original scores and restores them in the first
    wave write, so only the boundary ever sees the flipped season."""
    if not game.has_result:
        return [f"game {game.index}: no result to swap"]
    hs, as_ = game.home_score or 0, game.away_score or 0
    _put_bits(payload, game.offset, 609, 7, as_)
    _put_bits(payload, game.offset, 617, 7, hs)
    return [f"game {game.index}: result flipped ({as_}-{hs} from {hs}-{as_})"]


def set_result_scores(payload: bytearray, game: Game, *, home: int, away: int) -> list[str]:
    """Write explicit final scores into a record's packed score fields (the
    restore side of swap_result_scores)."""
    _put_bits(payload, game.offset, 609, 7, home)
    _put_bits(payload, game.offset, 617, 7, away)
    return [f"game {game.index}: result restored ({home}-{away})"]


def set_venue(payload: bytearray, game: Game, stadium_handle: int | None) -> list[str]:
    """Move a game: write a stadium uid handle at +4 (None/0 = the home
    team's stadium). Handles come from stadiums.stadium_table for this save."""
    value = stadium_handle or 0
    if value and value >> 24 != 0x80:
        raise ValueError(f"game {game.index}: {value:#x} is not a stadium handle")
    struct.pack_into(">I", payload, game.offset + 4, value)
    where = f"{value:#x}" if value else "home team's stadium"
    return [f"game {game.index}: venue -> {where}"]


def read_record(payload: bytes, store: "GameStore", index: int) -> bytes:
    """The raw RECORD_SIZE bytes of one game record (for freeze/restore)."""
    off = store.records_off + index * RECORD_SIZE
    return bytes(payload[off:off + RECORD_SIZE])


def write_record(payload: bytearray, store: "GameStore", index: int,
                 data: bytes) -> list[str]:
    """Restore a game record's raw bytes verbatim.

    Used to PIN the user's own played game across a wave rewind: the captured
    bytes are exactly what the engine wrote when the user played (a valid
    official-with-result record whose request IDs, +52/+60, are the
    record's OWN pre-allocated slots, stable across rewinds), so grafting them
    back onto the pre-lock base keeps the user's real matchup and final score
    on their schedule instead of a leftover pairing. The engine treats an
    official-with-result slate record as already played and does not re-sim
    it."""
    if len(data) != RECORD_SIZE:
        raise ValueError(f"record data must be {RECORD_SIZE} bytes, got {len(data)}")
    off = store.records_off + index * RECORD_SIZE
    payload[off:off + RECORD_SIZE] = data
    return [f"game {index}: user's played record pinned ({RECORD_SIZE} bytes)"]


def week_slate(payload: bytes) -> list[int]:
    """Game-record indices of the CURRENT week's slate, from the engine's own
    SeasonGameRequest queue (see module docstring).

    Allocated at the week-advance boundary, the queue is present even in the
    pre-lock arrival autosave, which makes it the authority on which records
    the engine will lock (sim, or offer the user to play) this week. A matchup
    written into a slate record of a PRE-LOCK save is adopted by the engine at
    lock exactly as if it had scheduled it itself, including the user's own
    game on the dynasty home screen."""
    from . import bowls as savebowls
    try:
        rec0, stride, count, _ = savebowls._find_store(payload, b"SeasonGameRequest")
    except ValueError:
        return []
    game_ref = savetags.for_payload(payload).game
    rows: set[int] = set()
    for row in range(count):
        base = rec0 + row * stride
        for j in range(stride // 4):
            v = struct.unpack_from(">I", payload, base + j * 4)[0]
            if (v >> 16) == game_ref:
                rows.add(v & 0xFFFF)
    return sorted(rows)


def _pending_request_rows(payload: bytes, game_index: int) -> list[int]:
    """SeasonGameRequest row offsets that point at one game record."""
    from . import bowls as savebowls
    try:
        rec0, stride, count, _ = savebowls._find_store(
            payload, b"SeasonGameRequest")
    except ValueError:
        return []
    game_ref = savetags.for_payload(payload).game
    rows: list[int] = []
    for row in range(count):
        base = rec0 + row * stride
        words = struct.unpack_from(f">{stride // 4}I", payload, base)
        if any((word >> 16) == game_ref
               and (word & 0xFFFF) == game_index for word in words):
            rows.append(base)
    return rows


def user_pending_count(payload: bytes, game_index: int,
                       member_row: int = 0) -> int:
    """Number of Actions rows wired to a game for one dynasty member."""
    member_ref = (savetags.for_payload(payload).user << 16) | member_row
    return sum(
        struct.unpack_from(">I", payload, base + 16)[0] == member_ref
        for base in _pending_request_rows(payload, game_index)
    )


def _downgrade_user_request(payload: bytearray, base: int) -> None:
    """Restore one user-typed request row to the observed CPU row shape."""
    scheduler_handle = struct.unpack_from(">I", payload, base + 4)[0]
    pending_handle = struct.unpack_from(">I", payload, base + 44)[0]
    struct.pack_into(">I", payload, base + 16, 0)
    struct.pack_into(">I", payload, base + 28, scheduler_handle)
    struct.pack_into(">I", payload, base + 40, NO_RESULT)
    struct.pack_into(">I", payload, base + 48, pending_handle)
    struct.pack_into(">I", payload, base + 56, 0x09000000)


def repair_duplicate_user_pending(
        payload: bytearray, game_index: int, member_row: int = 0,
        user_team_rows: set[int] | None = None) -> list[str]:
    """Collapse duplicate Play Game rows for one matchup to one row.

    CFB can create two user variants when a custom native matchup reaches a
    boundary with an inherited user marker. Both rows open the same
    SeasonGame, so leaving both produces two identical Actions entries. The
    correct row is the one whose +40 RequestId belongs to the user's side of
    the SeasonGame. Healthy decoded saves contain the user variant first for a
    home user and second for an away user. Preserve the
    matching row and restore the other duplicate to the byte-for-byte CPU
    shape without touching the SeasonGame or either participant RequestId.
    """
    member_ref = (savetags.for_payload(payload).user << 16) | member_row
    rows = [
        base for base in _pending_request_rows(bytes(payload), game_index)
        if struct.unpack_from(">I", payload, base + 16)[0] == member_ref
    ]
    if len(rows) <= 1:
        return []
    keep = rows[-1]
    if user_team_rows:
        store = parse(bytes(payload))
        game = store.games[game_index]
        away_request, home_request = request_id_pair(bytes(payload), game)
        wanted_request = (
            away_request if game.away_row in user_team_rows
            else home_request if game.home_row in user_team_rows
            else None)
        if wanted_request is not None:
            keep = next(
                (base for base in rows
                 if struct.unpack_from(">I", payload, base + 40)[0]
                 == wanted_request), keep)
    report: list[str] = []
    for base in rows:
        if base == keep:
            continue
        _downgrade_user_request(payload, base)
        report.append(
            f"request for game {game_index}: duplicate user action removed")
    return report


def set_user_pending(payload: bytearray, user_game_index: int | None,
                     member_row: int = 0,
                     user_team_rows: set[int] | None = None) -> list[str]:
    """Reconcile the USER marking in the SeasonGameRequest queue (PRE-LOCK).

    Each queued game has two request rows. For the game the USER plays this
    week, one row is the user-participation variant:
    +16 = 0x21DA|member, +28 = 0, +48 = the no-result sentinel, +56 = 0x01
    (CPU rows: +16 = 0, +28 = the scheduler handle, +48 = the game's pending
    handle, +56 = 0x09; observed identically across two dynasties and weeks).
    The week boundary writes the variant only for the matchup the ENGINE
    scheduled the user into, and the LOCK trusts it blindly: a game without
    it is pre-simmed like any CPU game even when the user's team is in the
    record, and the user reads as on a bye (observed in-game 2026-07-08,
    Minnesota run). So after rewriting a pre-lock world's matchups, the queue
    must be reconciled: mark the record now hosting the user's game, and
    downgrade any pair whose record no longer does. The +40 RequestId is left
    as the sentinel until the engine allocates the participant request IDs.

    The user row's +40 must carry the request ID for the user's side or the
    dynasty hub reads the user as on a bye (this word is the ONLY wiring
    difference between a playable and a bye user game; verified by diffing
    Maryland's real bowl game against a marked-but-bye wave game). The request
    IDs (+52/+60 of the game record) are allocated by the week-advance
    BOUNDARY, so it is present in the pre-lock arrival autosave and this
    write can fill +40 immediately; if a base predates the allocation, +40
    is left sentinel and `fill_user_pending_slot` completes it after the
    lock runs.

    `user_game_index=None` downgrades every pair (the user has no game this
    week). Rows already past the lock (+40 holds a RequestId) are refused.
    """
    from . import bowls as savebowls
    try:
        rec0, stride, count, _ = savebowls._find_store(bytes(payload), b"SeasonGameRequest")
    except ValueError:
        return ["SeasonGameRequest store not found; user marking skipped"]
    t = savetags.for_payload(payload)
    store = parse(bytes(payload))
    words_n = stride // 4
    pairs: dict[int, list[int]] = {}
    for row in range(count):
        base = rec0 + row * stride
        for j in range(words_n):
            v = struct.unpack_from(">I", payload, base + j * 4)[0]
            if (v >> 16) == t.game:
                pairs.setdefault(v & 0xFFFF, []).append(base)
                break
    report: list[str] = []
    marked = False
    for game_index, bases in pairs.items():
        if len(bases) < 2:
            continue
        want_user = game_index == user_game_index
        if want_user:
            # A custom native boundary can preserve an inherited marker and
            # also create the engine's own marker, yielding two identical Play
            # Game entries. Collapse the duplicate even after lock. It is safe
            # because the retained row still owns the playable request and the
            # SeasonGame request IDs are untouched.
            report.extend(repair_duplicate_user_pending(
                payload, game_index, member_row, user_team_rows))
        user_bases = [base for base in bases
                      if struct.unpack_from(">I", payload, base + 16)[0]
                      == (t.user << 16) | member_row]
        if not want_user:
            for base in user_bases:
                request_id = struct.unpack_from(">I", payload, base + 40)[0]
                if request_id != NO_RESULT:
                    report.append(
                        f"request for game {game_index}: already locked; not retyped")
                else:
                    _downgrade_user_request(payload, base)
                    report.append(
                        f"request for game {game_index}: downgraded to a CPU game")
            continue
        game = store.games[game_index]
        away_request_id, home_request_id = request_id_pair(bytes(payload), game)
        participant_request_id = (
            home_request_id if user_team_rows and game.home_row in user_team_rows
            else away_request_id)
        # Preserve an existing single user row. Otherwise match the row whose
        # boundary-issued RequestId belongs to the user's side. Before the row
        # IDs exist, the queue pair is home first and away second.
        side_base = (bases[0]
                     if user_team_rows and game.home_row in user_team_rows
                     else bases[1])
        base = (user_bases[0] if len(user_bases) == 1 else next(
            (candidate for candidate in bases
             if struct.unpack_from(">I", payload, candidate + 40)[0]
             == participant_request_id), side_base))
        request_id = struct.unpack_from(">I", payload, base + 40)[0]
        is_user = (struct.unpack_from(">I", payload, base + 16)[0] >> 16) == t.user
        if is_user == want_user:
            if want_user and request_id == NO_RESULT \
                    and participant_request_id >> 16 == 0x8000:
                struct.pack_into(">I", payload, base + 40, participant_request_id)
                report.append(f"request for game {game_index}: RequestId "
                              f"filled ({participant_request_id:#010x})")
            marked = marked or want_user
            continue
        if want_user:
            struct.pack_into(">I", payload, base + 16, (t.user << 16) | member_row)
            struct.pack_into(">I", payload, base + 28, 0)
            struct.pack_into(">I", payload, base + 48, NO_RESULT)
            struct.pack_into(">I", payload, base + 56, 0x01000000)
            if participant_request_id >> 16 == 0x8000:
                struct.pack_into(">I", payload, base + 40, participant_request_id)
                report.append(f"request for game {game_index}: marked as the user's "
                              f"game (RequestId {participant_request_id:#010x})")
            else:
                report.append(f"request for game {game_index}: marked as the user's "
                              "game (RequestId pending the lock)")
            marked = True
    if user_game_index is not None and not marked:
        report.append(f"request for game {user_game_index}: not in the week queue; "
                      "user marking skipped")
    return report


def user_pending_game(payload: bytes, member_row: int = 0) -> int | None:
    """The current-week game record wired to the user's Actions entry.

    The user-participation request can outlive a matchup rewrite. In that
    state the SeasonGame containing the user's team is not authoritative:
    Actions still opens the record referenced by the typed request row. Prefer
    a locked row whose +40 RequestId is filled, then a pre-lock typed
    row. This lets the playoff writer preserve the engine's organic play-game
    wiring instead of fabricating it on a different record.
    """
    from . import bowls as savebowls
    try:
        rec0, stride, count, _ = savebowls._find_store(
            payload, b"SeasonGameRequest")
    except ValueError:
        return None
    t = savetags.for_payload(payload)
    candidates: list[tuple[bool, int]] = []
    for row in range(count):
        base = rec0 + row * stride
        words = struct.unpack_from(f">{stride // 4}I", payload, base)
        if words[4] != (t.user << 16) | member_row:
            continue
        game_index = next(
            (word & 0xFFFF for word in words if word >> 16 == t.game), None)
        if game_index is not None:
            candidates.append((words[10] != NO_RESULT, game_index))
    return max(candidates, default=(False, None))[1]


def user_pending_fix_due(payload: bytes, game_index: int,
                         user_team_rows: set[int] | None = None) -> bool:
    """Whether the user's queued game needs its +40 RequestId filled."""
    return bool(_user_pending_rows(payload, game_index, user_team_rows))


def _user_pending_rows(payload: bytes, game_index: int,
                       user_team_rows: set[int] | None = None) \
        -> list[tuple[int, int]]:
    """(row offset, participant RequestId) for a user row whose +40 is still the
    sentinel after the game record received its participant request IDs."""
    from . import bowls as savebowls
    try:
        rec0, stride, count, _ = savebowls._find_store(bytes(payload), b"SeasonGameRequest")
    except ValueError:
        return []
    t = savetags.for_payload(payload)
    store = parse(bytes(payload))
    game = store.games[game_index]
    away_request_id, home_request_id = request_id_pair(payload, game)
    participant_request_id = (
        home_request_id if user_team_rows and game.home_row in user_team_rows
        else away_request_id)
    if participant_request_id >> 16 != 0x8000:
        return []  # the boundary has not allocated the requests yet
    out = []
    for row in range(count):
        base = rec0 + row * stride
        words = struct.unpack_from(f">{stride // 4}I", payload, base)
        gref = next((w & 0xFFFF for w in words if (w >> 16) == t.game), None)
        if gref != game_index:
            continue
        if (words[4] >> 16) == t.user and words[10] == NO_RESULT:
            out.append((base, participant_request_id))
    return out


def fill_user_pending_slot(payload: bytearray, game_index: int,
                           user_team_rows: set[int] | None = None) -> list[str]:
    """Complete the user marking AFTER the lock: copy the game record's
    participant RequestId (allocated by the boundary on arrival to the week)
    into the user-typed request row's +40.

    The dynasty hub's play-your-game flow reads exactly this word: with the
    sentinel there the user shows as on a bye even though the lock honored
    the user mark (game left un-simmed, slots allocated). Verified by
    diffing a real playable user bowl game (Maryland, bowl week 2) against
    a marked-but-bye wave game (Missouri): the ONLY wiring difference is
    this one word. The request IDs cannot be invented pre-boundary: the engine
    allocates ids in its own sim-chronology order, which is not predictable
    from the queue."""
    fixes = _user_pending_rows(payload, game_index, user_team_rows)
    report = []
    for base, participant_request_id in fixes:
        struct.pack_into(">I", payload, base + 40, participant_request_id)
        report.append(f"request for game {game_index}: RequestId filled "
                      f"({participant_request_id:#010x}); the game is now playable")
    return report


def set_bowl_ref(payload: bytearray, game: Game, bowl_row: int | None) -> list[str]:
    """Repoint the game's BowlInfo ref (site/branding for neutral games)."""
    bowl_ref = savetags.for_payload(payload).bowl
    current = struct.unpack_from(">I", payload, game.offset + 16)[0]
    if current and (current >> 16) != bowl_ref:
        raise ValueError(f"game {game.index}: +16 holds non-bowl ref {current:#x}")
    value = 0 if bowl_row is None else ((bowl_ref << 16) | bowl_row)
    struct.pack_into(">I", payload, game.offset + 16, value)
    return [f"game {game.index}: bowl ref -> {bowl_row}"]
