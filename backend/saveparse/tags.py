"""Per-save FrTk type-tag discovery.

Typed references in the payload are `(tag << 16) | row` words, where `tag` is
the type's id in the save's FrTk type table. The 2026-07-16 RL2 game patch
(build College-27-RL2-9058834) renumbered that table, and NOT uniformly:
measured pre/post-patch on the same dynasty, Team moved 0x317C -> 0x3182 (+6,
with the whole 0x31xx cluster), BowlGame moved 0x21B2 -> 0x21BC (+10), the
conference tie-in ref 0x2186 -> 0x218E (+8), and TeamStats stayed 0x2024. Any
hardcoded tag can silently break on a schema-reshuffling patch, or worse,
collide: the RL2 Team tag equals the RL1 Division tag.

This module derives the tags from the payload being parsed. Every anchor used
is a NAME (store type names, the conference record array's string-offset
quad), which renumbering does not move. When a payload carries no evidence for
a tag (synthetic test fixtures, degenerate saves), the value falls back to the
launch-build (RL1) constant, re-based where a cluster relationship has held:

* the 0x31xx cluster (conference / division / division-list / division-ref /
  team / season-game / unpublished-stats) has always shifted TOGETHER, so its
  members fall back relative to the measured conference tag;
* the user/member ref falls back relative to the measured BowlGame tag (they
  sit in the same cluster and moved together on RL2);
* everything else falls back to its RL1 value.

A payload with no evidence at all (e.g. a synthetic fixture built from the
RL1 constants) resolves to exactly the RL1 constants, so pre-patch behavior
is unchanged wherever nothing was measured.

Derivations are a handful of `payload.find` scans and are cached per payload
object. The cache key is (id(payload), len(payload)); tags are a property of
the GAME BUILD, not of the dynasty, so a stale-id collision between two
payloads of the same build is harmless, and payloads of different builds
virtually never share both id and byte length. In-place writes to a bytearray
keep both key parts, and cannot change the save's tags.
"""
from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class SaveTags:
    conf: int          # Conference record self tag
    div: int           # Division
    divlist: int       # DivisionList entry
    div_ref: int       # Division ref inside DivisionListStore rows
    team: int          # Team ref
    game: int          # SeasonGame record ref
    unpublished: int   # UnpublishedGameStats ref (pre-simmed results)
    bowl: int          # BowlGame identity ref
    conf_ref: int      # Conference ref (bowl tie-ins, history records)
    user: int          # member/user slot ref (user-typed SeasonGameRequest)


# The launch-build values (College-27-RL1), the baseline every fallback
# derives from. These are also what synthetic test fixtures are built with.
RL1 = SaveTags(conf=0x311E, div=0x3182, divlist=0x3180, div_ref=0x311C,
               team=0x317C, game=0x3174, unpublished=0x3192,
               bowl=0x21B2, conf_ref=0x2186, user=0x21DA)

# plausible type-tag range: every observed tag is 0x20xx..0x33xx; opaque
# handles (0x80xxxxxx), request ids (0x8000xxxx), and the 0x7xxx sentinel
# values some queue rows carry all sit above it
_TAG_LO, _TAG_HI = 0x2000, 0x4000

_CONF_RECORD_SIZE = 80
_CONF_STRING_SLOT = 136
_CONF_ROWS = 12
# row 0's string-offset quad [name, style, champ game, display]; invariant
# across builds (the string slot layout did not change on RL2)
_CONF_QUAD0 = struct.pack(">4I", 0, 71, 22, 50)

_GAME_RECORD_SIZE = 100


def _u32(payload: bytes, off: int) -> int:
    return struct.unpack_from(">I", payload, off)[0]


def _is_tag(v: int) -> bool:
    return _TAG_LO <= v < _TAG_HI


def _dominant(counter: Counter, min_hits: int) -> int | None:
    if not counter:
        return None
    tag, hits = counter.most_common(1)[0]
    return tag if hits >= min_hits else None


# --------------------------------------------------------------------------
# name-anchored store locators (tag-free; mirror the parsers' own math)
# --------------------------------------------------------------------------

def _spbf_store(payload: bytes, name: bytes) -> tuple[int, int, int, int] | None:
    """(rec0, stride, count, strings_off) of an SPBF store by type name, or
    None. Same header math as bowls._find_store, non-raising."""
    at = payload.find(b"\x00" + name + b"\x00")
    if at == -1:
        return None
    bsft = payload.find(b"BSFT", at, at + 400)
    if bsft == -1:
        return None
    try:
        w = struct.unpack_from(">6I", payload, bsft + 4)
    except struct.error:
        return None
    count, fields = w[3], w[4] + 1
    if not (0 < count < 100_000 and 0 < fields < 512):
        return None
    body = w[0] - 28 - fields * 4
    if body <= 0 or body % count:
        return None
    rec0 = bsft + 4 + 24 + fields * 4
    stride = body // count
    if rec0 + count * stride > len(payload):
        return None
    return rec0, stride, count, rec0 + count * stride


def _season_game_store(payload: bytes) -> tuple[int, int] | None:
    """(rec0, count) of the SeasonGameStore, same selection as schedule.locate
    (skip the Practice store, header math for record 0)."""
    at = -1
    i = payload.find(b"SeasonGameStore\x00")
    while i != -1:
        if payload[i - 8:i] != b"Practice":
            at = i
            break
        i = payload.find(b"SeasonGameStore\x00", i + 1)
    if at == -1:
        return None
    bsft = payload.find(b"BSFT", at, at + 120)
    if bsft == -1:
        return None
    try:
        data_size = _u32(payload, bsft + 4)
        count = _u32(payload, bsft + 16)
    except struct.error:
        return None
    if not 0 < count < 5000:
        return None
    rec0 = bsft + (data_size - count * _GAME_RECORD_SIZE)
    if rec0 < 0 or rec0 + count * _GAME_RECORD_SIZE > len(payload):
        return None
    return rec0, count


def find_conference_records(payload: bytes) -> tuple[int, int] | None:
    """(records_off, conf_tag) of the 12x80 conference record array, located
    WITHOUT knowing the build's tag: row 0's string-offset quad {0,71,22,50}
    at +40 is invariant, and the self tag is read from +36. A hit must
    validate over all 12 rows (each row's quad points at its own 136-byte
    string slot) before it is accepted."""
    i = payload.find(_CONF_QUAD0)
    while i != -1:
        base0 = i - 40
        if base0 >= 0:
            try:
                tag, idv = struct.unpack_from(">HH", payload, base0 + 36)
            except struct.error:
                tag, idv = 0, 1
            if idv == 0 and _is_tag(tag) and _validate_conf_rows(payload, base0, tag):
                return base0, tag
        i = payload.find(_CONF_QUAD0, i + 1)
    return None


def _validate_conf_rows(payload: bytes, records: int, tag: int) -> bool:
    for row in range(_CONF_ROWS):
        base = records + row * _CONF_RECORD_SIZE
        try:
            t = struct.unpack_from(">H", payload, base + 36)[0]
            quad = struct.unpack_from(">4I", payload, base + 40)
        except struct.error:
            return False
        expect = tuple(row * _CONF_STRING_SLOT + off for off in (0, 71, 22, 50))
        if t not in (tag, 0) or quad != expect:
            return False
    return True


# --------------------------------------------------------------------------
# per-tag measurements
# --------------------------------------------------------------------------

def _measure_game_store(payload: bytes) -> dict[str, int | None]:
    """team/bowl/unpublished from the SeasonGameStore's own records."""
    loc = _season_game_store(payload)
    if loc is None:
        return {}
    rec0, count = loc
    c_team, c_bowl, c_unpub = Counter(), Counter(), Counter()
    for r in range(count):
        base = rec0 + r * _GAME_RECORD_SIZE
        for off, ctr, max_row in ((8, c_team, 1024), (36, c_team, 1024),
                                  (16, c_bowl, 256), (0, c_unpub, 8192)):
            v = _u32(payload, base + off)
            if v and _is_tag(v >> 16) and (v & 0xFFFF) < max_row:
                ctr[v >> 16] += 1
    return {"team": _dominant(c_team, 8),
            "bowl": _dominant(c_bowl, 3),
            "unpublished": _dominant(c_unpub, 3)}


def _measure_requests(payload: bytes) -> dict[str, int | None]:
    """game/user from the SeasonGameRequest queue: every row carries one
    SeasonGame ref; only a user-typed row has a non-zero +16 member ref."""
    loc = _spbf_store(payload, b"SeasonGameRequest")
    if loc is None:
        return {}
    rec0, stride, count, _ = loc
    words_n = stride // 4
    c_game, c_user = Counter(), Counter()
    for r in range(count):
        base = rec0 + r * stride
        try:
            words = struct.unpack_from(f">{words_n}I", payload, base)
        except struct.error:
            break
        for w in words:
            if w and _is_tag(w >> 16) and (w & 0xFFFF) < 5000:
                c_game[w >> 16] += 1
        if words_n > 4 and words[4] and _is_tag(words[4] >> 16):
            c_user[words[4] >> 16] += 1
    # the user ref also lands in the all-words histogram; a queue with a user
    # row still counts far more game refs (two rows per game, one ref each)
    for tag in c_user:
        c_game.pop(tag, None)
    return {"game": _dominant(c_game, 2), "user": _dominant(c_user, 1)}


def _measure_bowl_store(payload: bytes) -> int | None:
    """conf_ref from the BowlGame store's tie-in slots (+8/+12)."""
    loc = _spbf_store(payload, b"BowlGame")
    if loc is None:
        return None
    rec0, stride, count, _ = loc
    c = Counter()
    for r in range(count):
        base = rec0 + r * stride
        for off in (8, 12):
            v = _u32(payload, base + off)
            if v and _is_tag(v >> 16) and (v & 0xFFFF) < 64:
                c[v >> 16] += 1
    return _dominant(c, 3)


def _measure_team_from_ctls(payload: bytes) -> int | None:
    """team from the ConferenceTeamListStore's membership refs (the fallback
    for payloads with no season schedule, e.g. conference test fixtures)."""
    at = payload.find(b"ConferenceTeamListStore\x00")
    if at == -1:
        return None
    cmpc = payload.find(b"CMPC", at, at + 200)
    if cmpc == -1:
        return None
    c = Counter()
    end = min(len(payload) - 4, cmpc + 2400)
    for pos in range(cmpc + 12, end, 4):
        v = _u32(payload, pos)
        if v and _is_tag(v >> 16) and (v & 0xFFFF) < 1024:
            c[v >> 16] += 1
    return _dominant(c, 8)


def _measure_division_self_tag(payload: bytes) -> int | None:
    """div from the DivisionStore's record heads ([tag|row] in sequence).
    Some saves carry runtime handles there instead (see conferences.py), so
    a strong majority of rows must agree."""
    loc = _spbf_store(payload, b"DivisionStore")
    if loc is None:
        # the synthetic fixture has no BSFT header; fall back to a name-window
        # scan for a sequential [tag|0][..12b..][tag|1] pattern (16-byte stride)
        at = payload.find(b"DivisionStore\x00")
        if at == -1:
            return None
        for start in range(at, min(at + 600, len(payload) - 36), 2):
            tag, idv = struct.unpack_from(">HH", payload, start)
            if idv == 0 and _is_tag(tag):
                t1, i1 = struct.unpack_from(">HH", payload, start + 16)
                t2, i2 = struct.unpack_from(">HH", payload, start + 32)
                if (t1, i1) == (tag, 1) and (t2, i2) == (tag, 2):
                    return tag
        return None
    rec0, stride, count, _ = loc
    agree: Counter = Counter()
    for row in range(count):
        try:
            tag, idv = struct.unpack_from(">HH", payload, rec0 + row * stride)
        except struct.error:
            break
        if idv == row and _is_tag(tag):
            agree[tag] += 1
    tag = _dominant(agree, max(3, (count * 2) // 3))
    return tag


def _measure_conf_head_refs(payload: bytes, records: int) -> Counter:
    """The high halfwords of the conference records' +0 division refs:
    DivisionList entries for divided conferences (the majority), a direct
    Division for the Independents (the minority)."""
    c: Counter = Counter()
    for row in range(_CONF_ROWS):
        v = _u32(payload, records + row * _CONF_RECORD_SIZE)
        if v and _is_tag(v >> 16):
            c[v >> 16] += 1
    return c


def _measure_div_ref(payload: bytes) -> int | None:
    """div_ref from the DivisionListStore: slot 0 of every 8-byte row is a
    Division ref, so the first tag-like u32 whose high half repeats across
    the following slot-0 positions is the ref tag."""
    at = payload.find(b"DivisionListStore\x00")
    if at == -1:
        return None
    cmpc = payload.find(b"CMPC", at, at + 200)
    if cmpc == -1:
        return None
    for pos in range(cmpc + 4, min(cmpc + 400, len(payload) - 4), 4):
        v = _u32(payload, pos)
        hi = v >> 16
        if not (v and _is_tag(hi) and (v & 0xFFFF) < 64):
            continue
        repeats = sum(
            1 for k in range(1, 8)
            if pos + k * 8 + 4 <= len(payload)
            and (_u32(payload, pos + k * 8) >> 16) == hi)
        if repeats >= 2:
            return hi
    return None


# --------------------------------------------------------------------------
# resolution
# --------------------------------------------------------------------------

def _derive(payload: bytes) -> SaveTags:
    conf_hit = find_conference_records(payload)
    conf = conf_hit[1] if conf_hit else RL1.conf

    def conf_rel(rl1_value: int) -> int:
        # the 0x31xx cluster shifts together (verified RL1 -> RL2)
        return rl1_value + (conf - RL1.conf)

    gs = _measure_game_store(payload)
    rq = _measure_requests(payload)

    team = gs.get("team") or _measure_team_from_ctls(payload) or conf_rel(RL1.team)
    game = rq.get("game") or conf_rel(RL1.game)
    unpublished = gs.get("unpublished") or conf_rel(RL1.unpublished)
    bowl = gs.get("bowl") or RL1.bowl
    conf_ref = _measure_bowl_store(payload) or RL1.conf_ref
    # user sits next to BowlGame in the type table and moved with it on RL2
    user = rq.get("user") or (bowl + (RL1.user - RL1.bowl))

    div_store = _measure_division_self_tag(payload)
    heads = _measure_conf_head_refs(payload, conf_hit[0]) if conf_hit else Counter()
    div = divlist = None
    if len(heads) >= 2:
        (a, _), (b, _) = heads.most_common(2)
        divlist, div = a, b
    elif len(heads) == 1:
        only = next(iter(heads))
        if div_store is not None and only == div_store:
            div = only
        else:
            divlist = only
    div = div_store or div or conf_rel(RL1.div)
    divlist = divlist if divlist is not None else conf_rel(RL1.divlist)
    div_ref = _measure_div_ref(payload) or conf_rel(RL1.div_ref)

    return SaveTags(conf=conf, div=div, divlist=divlist, div_ref=div_ref,
                    team=team, game=game, unpublished=unpublished,
                    bowl=bowl, conf_ref=conf_ref, user=user)


_cache: dict[int, tuple[bytes | bytearray, SaveTags]] = {}


def for_payload(payload: bytes | bytearray) -> SaveTags:
    """The save's own type tags, derived once per payload object and cached.
    The cache keeps a strong reference to its source object and checks identity
    on every hit. CFB saves from different game builds have the same byte
    length, and Python may reuse an id after an older bytes object is freed, so
    an ``(id, length)`` key alone can otherwise return launch-build tags for a
    post-patch save. Safe for bytearrays being written in place: writes do not
    change the save's schema tags."""
    key = id(payload)
    hit = _cache.get(key)
    if hit is not None and hit[0] is payload:
        return hit[1]
    tags = _derive(payload)
    # Keeping the source object prevents id reuse while it is cached. Bound the
    # retained save payloads so a long-running app cannot accumulate them.
    if len(_cache) >= 8:
        _cache.clear()
    _cache[key] = (payload, tags)
    return tags
