"""Conference / division / membership structures in the FrTk payload.

Fully reverse-engineered from real CFB 27 dynasty saves (2026-07-06 build
"College-27-RL1-9039126"). Three structures cooperate:

1. The Conference table (~19.2 MB): a 12-row record array + string area.
   Each record is 80 bytes; row k sits at `records + 80*k`:

       +0    u32be division ref: 0x3180<<16|row (DivisionList) or
             0x3182<<16|row (a single Division, used by Independents);
             an all-zero record is the game's one BLANK conference slot
       +36   u32be self tag 0x311e<<16|id (id skips the blank row)
       +40   4x u32be string offsets into the string area, in field order
             [name, style, champ game, display]; always slot*136 + {0,71,22,50}
       +56   metadata (conference enum id, colors; not decoded)

   The string area starts right after the records (records + 960): twelve
   136-byte slots holding four inline NUL-padded strings per conference:
   internal name (<=21), championship game name (<=27) at +22, display name
   (<=20) at +50, and a schedule-style enum string at +71 (e.g.
   "NoDivsProtectedRivalsStyle", "EvenDivsOverlappingGamesStyle").

2. The DivisionStore (~25.9 MB, an SPBF block found by its name string):
   twelve 16-byte records `[0x3182|row][u32be dispOff][u32be nameOff][u32be ?]`
   followed by twelve 53-byte string slots (name <=20 at +0, display <=31 at
   +21). Rows 0-9 are the implicit whole-conference divisions plus
   "FBS Independents" (row 5); rows 10/11 are the Sun Belt's "East"/"West".

3. The membership stores (~27.5 MB, ASTO blocks found by their name strings):
   `ConferenceTeamListStore` holds one zero-padded 80-byte list per
   conference of u32be team refs (0x317c<<16|teamRow, teamRow = the index in
   `teams.parse_teams` order); interleaved bare u32 values of unknown meaning
   are preserved untouched. Independents have no conference list; their teams
   live only in the `DivisionTeamListStore`, whose twelve 80-byte slots (one
   per Division row, same order) hold the division memberships. Both stores
   carry a count table in their CMPC header; the conference store duplicates
   each count (pairs), the division store lists twelve counts in row order.
   A third store, `DivisionListStore` (2-wide lists of 0x311c division refs),
   maps every non-blank conference, in row order, to its Division rows; that
   is the structural conference -> divisions link used here.

The FBCHUNKS header has no payload checksum (verified across saves), so
in-place, same-length payload patches + re-deflate produce a save the game
accepts. Everything here is located by anchor search, never absolute offset.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from . import tags as savetags
from . import teams as saveteams

# The launch-build (RL1) tag values. These are the BASELINE ONLY: game patches
# renumber the FrTk type table (2026-07-16 RL2 shifted this whole cluster +6),
# so every runtime read/write resolves the payload's actual tags through
# saveparse.tags.for_payload. The constants stay for the synthetic test
# fixtures, which are built in the RL1 shape.
CONF_TAG = savetags.RL1.conf
DIV_TAG = savetags.RL1.div
DIVLIST_TAG = savetags.RL1.divlist
DIV_REF = savetags.RL1.div_ref
TEAM_REF = savetags.RL1.team

CONF_COUNT = 12
CONF_RECORD_SIZE = 80
CONF_STRING_SLOT = 136
# (offset, capacity incl. NUL) of each string field inside a conference slot
CONF_FIELDS = {"name": (0, 22), "champ_game": (22, 28), "display": (50, 21), "style": (71, 65)}

DIV_COUNT = 12
DIV_RECORD_SIZE = 16
DIV_STRING_SLOT = 53
DIV_FIELDS = {"name": (0, 21), "display": (21, 32)}

LIST_SLOT_BYTES = 80          # one membership list slot (20 team refs max)
MAX_LIST_TEAMS = LIST_SLOT_BYTES // 4
INDEPENDENTS_KEY = "FBS_Independents"

_CTLS_NAME = b"ConferenceTeamListStore"
_DSTO_NAME = b"DivisionTeamListStore"
_DIVSTORE_NAME = b"DivisionStore"
_DIVLIST_NAME = b"DivisionListStore"


@dataclass
class Division:
    row: int
    name: str
    display: str
    team_rows: list[int] = field(default_factory=list)
    # writer internals
    strings_off: int = 0          # absolute offset of this division's 53-byte slot
    list_off: int | None = None   # absolute offset of its DivisionTeamListStore slot
    count_offs: list[int] = field(default_factory=list)


@dataclass
class Conference:
    row: int
    blank: bool
    name: str = ""
    champ_game: str = ""
    display: str = ""
    style: str = ""
    division_rows: list[int] = field(default_factory=list)
    team_rows: list[int] = field(default_factory=list)
    # True for Independents (and for a conference activated into the blank
    # row): the record references a single Division directly via 0x3182
    direct_division: bool = False
    direct_division_row: int | None = None
    # for 0x3180 refs: the DivisionList entry row (list index = row // 2)
    divlist_row: int | None = None
    # writer internals
    strings_off: int = 0          # absolute offset of this conference's 136-byte slot
    list_off: int | None = None   # absolute offset of its ConferenceTeamListStore list
    list_capacity: int = 0        # bytes available at list_off before the next structure
    count_offs: list[int] = field(default_factory=list)


@dataclass
class ConferenceTable:
    conferences: list[Conference]
    divisions: list[Division]
    records_off: int
    strings_off: int
    writable_membership: bool     # counts + lists located well enough to edit safely
    notes: list[str] = field(default_factory=list)

    def by_name(self, name: str) -> Conference | None:
        return next((c for c in self.conferences if c.name == name), None)

    @property
    def independents(self) -> Conference | None:
        # the Independents pool is division-only AND has no championship game;
        # a conference activated into the blank row is division-only WITH one
        return next((c for c in self.conferences
                     if c.direct_division and not c.champ_game), None)


def _cstr(payload: bytes, off: int, cap: int) -> str:
    end = payload.find(b"\x00", off, off + cap)
    if end == -1:
        end = off + cap
    return payload[off:end].decode("latin1", "replace")


def _u32(payload: bytes, off: int) -> int:
    return struct.unpack_from(">I", payload, off)[0]


# --------------------------------------------------------------------------
# locating + parsing
# --------------------------------------------------------------------------

def _find_records(payload: bytes) -> int:
    """Absolute offset of the 12x80 conference record array.

    Anchored on row 0's string-offset quad, which never changes even when the
    strings have been edited or a game patch has renumbered the type table
    (the tag itself is read from the save, see saveparse.tags)."""
    hit = savetags.find_conference_records(payload)
    if hit is None:
        raise ValueError("conference record array not found")
    return hit[0]


def _count_conference_rows(payload: bytes, records: int,
                           conf_tag: int = CONF_TAG) -> int:
    """Rows in the record array (12 stock; growable). A row is real while its
    tag is a conference tag or the blank marker AND its string quad points at
    its own slot; the first string slot's bytes break the pattern."""
    rows = 0
    while rows < 32:
        base = records + rows * CONF_RECORD_SIZE
        tag = struct.unpack_from(">H", payload, base + 36)[0]
        quad = struct.unpack_from(">4I", payload, base + 40)
        expect = tuple(rows * CONF_STRING_SLOT + off for off, _ in
                       (CONF_FIELDS["name"], CONF_FIELDS["style"],
                        CONF_FIELDS["champ_game"], CONF_FIELDS["display"]))
        if tag not in (conf_tag, 0) or quad != expect:
            break
        rows += 1
    if rows < CONF_COUNT:
        raise ValueError(f"conference record array truncated at {rows} rows")
    return rows


def _parse_conference_records(payload: bytes) -> tuple[int, int, list[Conference]]:
    t = savetags.for_payload(payload)
    records = _find_records(payload)
    n_rows = _count_conference_rows(payload, records, t.conf)
    strings = records + n_rows * CONF_RECORD_SIZE
    confs: list[Conference] = []
    for row in range(n_rows):
        base = records + row * CONF_RECORD_SIZE
        slot = strings + row * CONF_STRING_SLOT
        tag = struct.unpack_from(">H", payload, base + 36)[0]
        if tag not in (t.conf, 0):
            raise ValueError(f"conference row {row}: unexpected tag {tag:#x}")
        quad = struct.unpack_from(">4I", payload, base + 40)
        expect = tuple(row * CONF_STRING_SLOT + off for off, _ in
                       (CONF_FIELDS["name"], CONF_FIELDS["style"],
                        CONF_FIELDS["champ_game"], CONF_FIELDS["display"]))
        if quad != expect:
            raise ValueError(f"conference row {row}: string quad {quad} != {expect}")
        if tag == 0:
            # the game's blank conference slot: zeroed refs + tag, valid quad
            confs.append(Conference(row=row, blank=True, strings_off=slot))
            continue
        div_ref = _u32(payload, base)
        confs.append(Conference(
            row=row,
            blank=False,
            name=_cstr(payload, slot + CONF_FIELDS["name"][0], CONF_FIELDS["name"][1]),
            champ_game=_cstr(payload, slot + CONF_FIELDS["champ_game"][0], CONF_FIELDS["champ_game"][1]),
            display=_cstr(payload, slot + CONF_FIELDS["display"][0], CONF_FIELDS["display"][1]),
            style=_cstr(payload, slot + CONF_FIELDS["style"][0], CONF_FIELDS["style"][1]),
            direct_division=(div_ref >> 16) == t.div,
            direct_division_row=(div_ref & 0xFFFF) if (div_ref >> 16) == t.div else None,
            divlist_row=(div_ref & 0xFFFF) if (div_ref >> 16) == t.divlist else None,
            strings_off=slot,
        ))
    return records, strings, confs


def _bsft_store(payload: bytes, name: bytes) -> tuple[int, int, int, int]:
    """Locate a BSFT record store by its type name.

    Returns (rec0, stride, count, strings_off). This is the game's own store
    descriptor (the same header decode the other save readers use, see
    saveparse/polls._store): the BSFT words give the record count and the
    total record-region size directly, so records are located structurally
    rather than by scanning for a per-record self-tag. That matters because a
    record's leading bytes are not a reliable anchor: some saves carry a
    runtime handle there instead of the canonical `type|row` self-tag (observed
    on a real DivisionStore whose rows read 0x2cc2/0x2cbc/0x2524 rather than
    0x3182|row, while the store header and the string offsets were intact)."""
    at = payload.find(name + b"\x00")
    if at == -1:
        raise ValueError(f"{name.decode()} not found")
    bsft = payload.find(b"BSFT", at, at + 400)
    if bsft == -1:
        raise ValueError(f"{name.decode()}: BSFT header not found")
    w = struct.unpack_from(">6I", payload, bsft + 4)
    total, count, fields = w[0], w[3], w[4] + 1
    if count <= 0 or fields <= 0:
        raise ValueError(f"{name.decode()}: bad header (count={count}, fields={fields})")
    field_table = fields * 4
    rec0 = bsft + 28 + field_table
    stride = (total - 28 - field_table) // count
    strings_off = bsft + total
    if stride <= 0:
        raise ValueError(f"{name.decode()}: bad record stride {stride}")
    return rec0, stride, count, strings_off


def _division_store_offset(payload: bytes) -> int:
    """Absolute offset of the DivisionStore's first record, via the store
    header (never the fragile per-record self-tag). For the write path. Falls
    back to the row-0 self-tag search for a payload with no BSFT header (the
    synthetic test fixture; every real save carries one)."""
    try:
        rec0, _stride, _count, _strings = _bsft_store(payload, _DIVSTORE_NAME)
        return rec0
    except (ValueError, struct.error):
        pass
    name_at = payload.find(_DIVSTORE_NAME + b"\x00")
    div_tag = savetags.for_payload(payload).div
    first = payload.find(struct.pack(">HH", div_tag, 0), name_at, name_at + 600)
    if first == -1:
        raise ValueError("DivisionStore records not found")
    return first


def _parse_divisions(payload: bytes) -> list[Division]:
    """Parse the DivisionStore. Anchored on the store's BSFT header so it works
    regardless of what each record's leading bytes hold; falls back to the
    legacy self-tag scan if the header cannot be read confidently."""
    try:
        rec0, stride, count, strings = _bsft_store(payload, _DIVSTORE_NAME)
    except (ValueError, struct.error):
        return _parse_divisions_legacy(payload)
    if stride < 12 or count < DIV_COUNT:
        return _parse_divisions_legacy(payload)
    # a division's string offsets must land inside the store's own strings
    # region; if they do not, the header did not actually describe divisions
    # and the resilient legacy scan is the safer read
    span = count * DIV_STRING_SLOT + 64
    divs: list[Division] = []
    for row in range(count):
        base = rec0 + row * stride
        disp_off = _u32(payload, base + 4)
        name_off = _u32(payload, base + 8)
        if not (0 <= name_off < span and 0 <= disp_off < span):
            return _parse_divisions_legacy(payload)
        divs.append(Division(
            row=row,
            name=_cstr(payload, strings + name_off, DIV_FIELDS["name"][1]),
            display=_cstr(payload, strings + disp_off, DIV_FIELDS["display"][1]),
            strings_off=strings + name_off,
        ))
    return divs


def _parse_divisions_legacy(payload: bytes) -> list[Division]:
    """The original self-tag scan: rows are tagged 0x3182|row in sequence (12
    stock; growable). Kept as a fallback for any save the header decode cannot
    handle, so a save that parses today never regresses."""
    name_at = payload.find(_DIVSTORE_NAME + b"\x00")
    if name_at == -1:
        raise ValueError("DivisionStore not found")
    div_tag = savetags.for_payload(payload).div
    first = payload.find(struct.pack(">HH", div_tag, 0), name_at, name_at + 600)
    if first == -1:
        raise ValueError("DivisionStore records not found")
    n_rows = 0
    while n_rows < 64:
        tag, r = struct.unpack_from(">HH", payload, first + n_rows * DIV_RECORD_SIZE)
        if tag != div_tag or r != n_rows:
            break
        n_rows += 1
    if n_rows < DIV_COUNT:
        raise ValueError(f"DivisionStore truncated at {n_rows} rows")
    strings = first + n_rows * DIV_RECORD_SIZE
    divs: list[Division] = []
    for row in range(n_rows):
        base = first + row * DIV_RECORD_SIZE
        disp_off = _u32(payload, base + 4)
        name_off = _u32(payload, base + 8)
        divs.append(Division(
            row=row,
            name=_cstr(payload, strings + name_off, DIV_FIELDS["name"][1]),
            display=_cstr(payload, strings + disp_off, DIV_FIELDS["display"][1]),
            strings_off=strings + name_off,
        ))
    return divs


@dataclass
class _Asto:
    counts_off: int
    counts: list[int]
    data_off: int
    lists: list[tuple[int, list[int]]]   # (absolute offset, team rows)
    end_off: int


def _is_typename_start(payload: bytes, pos: int) -> bool:
    """Whether `pos` begins a FrTk type-name word (three+ ASCII letters, e.g.
    'TeamStats[]', 'Team[]'). Team refs (0x317c.., high byte '1') and count/zero
    words never qualify, so this reliably marks the end of a store's data grid."""
    if pos + 3 >= len(payload):
        return False
    def _alpha(b: int) -> bool:
        return 0x41 <= b <= 0x5A or 0x61 <= b <= 0x7A
    return _alpha(payload[pos]) and _alpha(payload[pos + 1]) and _alpha(payload[pos + 2])


def _find_store_end(payload: bytes, start: int, limit: int = 8192) -> int:
    """Offset of the store's terminator: the next type-name word at or after
    `start` (4-byte aligned scan). Returns the scan bound if none is found."""
    end = min(len(payload) - 4, start + limit)
    pos = start
    while pos <= end:
        if _is_typename_start(payload, pos):
            return pos
        pos += 4
    return end


def _parse_asto(payload: bytes, name: bytes, data_slots: int | None = None) -> _Asto:
    """Parse an ASTO team-list store: a CMPC header, a small-int count run, a
    grid of fixed 80-byte list slots, then the next store's type name.

    The data grid is located by the store's TERMINATOR (the next type-name
    word), not by scanning for the first team ref. A leading list can be EMPTY
    (its slot is zeros, sometimes with a stray value); the old first-ref scan
    then walked out of the count run into the data and either mis-placed the
    grid or ran off the end ('count run too long'). When the caller knows the
    slot count (`data_slots`, e.g. one per division), the grid is pinned exactly
    as the last data_slots*80 bytes before the terminator; otherwise the
    first-ref heuristic is used, but bounded by the terminator so an all-empty
    store degrades instead of crashing."""
    at = payload.find(name + b"\x00")
    if at == -1:
        raise ValueError(f"{name.decode()} not found")
    cmpc = payload.find(b"CMPC", at, at + 200)
    if cmpc == -1:
        raise ValueError(f"{name.decode()}: CMPC header not found")
    counts_off = cmpc + 4 + 8  # skip the two duplicated data-size u32s
    term = _find_store_end(payload, counts_off)

    team_ref = savetags.for_payload(payload).team
    if data_slots is not None:
        data_off = term - data_slots * LIST_SLOT_BYTES
        if data_off < counts_off:            # malformed: no room for a count run
            data_off = counts_off
    else:
        data_off = counts_off
        p = counts_off
        while p < term:                      # first team ref, bounded by the end
            if (_u32(payload, p) >> 16) == team_ref:
                data_off = p
                break
            p += 4

    counts = [_u32(payload, o) for o in range(counts_off, data_off, 4)]
    if data_slots is None:
        # CTLS path: the grid was located by the first-team-ref scan, so any
        # trailing zeros here are padding between the count run and the grid.
        # When data_slots PINS the grid (DSTO), the run ends exactly at the
        # grid and its trailing zeros are REAL per-slot counts (empty
        # divisions, which an in-game realignment leaves at the tail); trimming
        # them would misalign the per-division slice, so keep them.
        while counts and counts[-1] == 0:
            counts.pop()

    lists: list[tuple[int, list[int]]] = []
    cur: list[int] = []
    cur_off = 0
    pos = data_off
    while pos < term:
        v = _u32(payload, pos)
        if (v >> 16) == team_ref:
            if not cur:
                cur_off = pos
            cur.append(v & 0xFFFF)
        elif cur:
            lists.append((cur_off, cur))
            cur = []
        pos += 4
    if cur:
        lists.append((cur_off, cur))
    return _Asto(counts_off=counts_off, counts=counts, data_off=data_off,
                 lists=lists, end_off=term)


def _next_nonzero(payload: bytes, start: int, end: int) -> int:
    """First offset in [start, end) whose u32 is non-zero (4-byte steps)."""
    pos = start
    while pos < end:
        if _u32(payload, pos) != 0:
            return pos
        pos += 4
    return end


def _parse_division_lists(payload: bytes, max_lists: int) -> list[list[int]]:
    """The DivisionListStore: one 2-slot (8-byte) row per non-blank conference,
    in conference-row order.

    Slot 0 of a row is always the conference's Division ref (0x311c|row); slot 1
    is a second Division ref for a two-division conference (e.g. Sun Belt
    East/West), otherwise filler. That filler is 0 in a clean save, but the game
    can leave a stale runtime handle there (observed: 0x2178|n). So the row's
    divisions are ONLY its 0x311c slots, and the store ends where slot 0 stops
    being a division ref, never where slot 1 happens to be non-zero (which the
    earlier reader mistook for the end, dropping every list after the first)."""
    at = payload.find(_DIVLIST_NAME + b"\x00")
    if at == -1:
        raise ValueError("DivisionListStore not found")
    cmpc = payload.find(b"CMPC", at, at + 200)
    if cmpc == -1:
        raise ValueError("DivisionListStore: CMPC header not found")
    div_ref = savetags.for_payload(payload).div_ref
    pos = cmpc + 4
    # skip the small header/count values up to the first division ref
    while (_u32(payload, pos) >> 16) != div_ref:
        pos += 4
        if pos - cmpc > 400:
            raise ValueError("DivisionListStore: no division refs found")
    lists: list[list[int]] = []
    for _ in range(max(0, max_lists)):
        slot0 = _u32(payload, pos)
        if (slot0 >> 16) != div_ref:
            break  # slot 0 is always a division ref; a non-ref is past the end
        row = [slot0 & 0xFFFF]
        slot1 = _u32(payload, pos + 4)
        if (slot1 >> 16) == div_ref:
            row.append(slot1 & 0xFFFF)
        lists.append(row)
        pos += 8
    return lists


def _match_count_pairs(counts: list[int], lengths: list[int]) -> list[list[int]] | None:
    """Locate each list's count inside the store's count run (STOCK shape).

    A stock ConferenceTeamListStore writes every list count TWICE in list
    order, with unrelated single values interleaved; return the count-run
    indices (pairs) per list, or None if the doubled template does not match."""
    out: list[list[int]] = []
    i = 0
    for want in lengths:
        while i + 1 < len(counts) and not (counts[i] == want and counts[i + 1] == want):
            i += 1
        if i + 1 >= len(counts):
            return None
        out.append([i, i + 1])
        i += 2
    return out


def _match_count_singles(counts: list[int], lengths: list[int]) -> list[list[int]] | None:
    """Locate each list's count when the store writes each count ONCE.

    After a realignment done in CFB 27's OWN in-game dynasty setup, the
    ConferenceTeamListStore writes each list's count a single time followed by
    a zero separator (`[15, 0, 14, 0, ...]`) instead of the stock doubled pair.
    Match each length to the next slot holding that value whose successor is
    zero, which excludes the header/stray values (none of those are followed by
    a zero); the final count can abut the next structure, so its trailing-zero
    requirement is relaxed. Returns one count-run index per list, or None."""
    out: list[list[int]] = []
    i = 0
    for pos, want in enumerate(lengths):
        last = pos == len(lengths) - 1
        while i < len(counts):
            next_zero = i + 1 >= len(counts) or counts[i + 1] == 0
            if counts[i] == want and (next_zero or last):
                break
            i += 1
        if i >= len(counts):
            return None
        out.append([i])
        i += 1
    return out


def _match_count_run(counts: list[int], lengths: list[int]) -> list[list[int]] | None:
    """Per-list count-run indices, whichever shape the store uses: the stock
    doubled pair or the in-game-realignment single-with-zero. None if neither
    matches. The count writer (set_memberships) fills every returned index, so
    a doubled list yields two offsets and a single yields one (its zero
    separator is left untouched, matching what the game itself wrote).

    A THIRD, transitional shape exists in a just-realigned week-1 autosave: the
    new counts sit as singles interleaved with stale pre-realignment values and
    no zero separators, with no unambiguous per-list slot. Both matchers reject
    it (singles requires the zero separator), so parse() keeps that save
    read-only rather than guess a slot and risk a corrupt write. The game
    normalizes the run to the clean single-with-zero shape as the season
    advances, and conference writes are preseason-gated regardless."""
    return (_match_count_pairs(counts, lengths)
            or _match_count_singles(counts, lengths))


def _locate_count_window(counts: list[int], lengths: list[int]) -> int | None:
    """Start index of the contiguous window in `counts` equal to `lengths`
    (one count per slot, in order), searched nearest-the-grid (highest start)
    first so a coincidental leading run never shadows the real one. Used for
    the DivisionTeamListStore, whose per-division counts are contiguous.
    None if no window matches."""
    n = len(lengths)
    if n == 0 or n > len(counts):
        return None
    for start in range(len(counts) - n, -1, -1):
        if counts[start:start + n] == lengths:
            return start
    return None


def parse(payload: bytes) -> ConferenceTable:
    """Parse the full conference setup out of a decoded save payload."""
    records, strings, confs = _parse_conference_records(payload)
    divisions = _parse_divisions(payload)
    notes: list[str] = []
    writable = True

    # division memberships: one 80-byte slot per Division row, in row order.
    # Pass the slot count so the data grid is pinned by the store terminator
    # even when leading divisions are empty (their slots are zeros/stray bytes,
    # which otherwise defeats a first-team-ref scan).
    team_ref = savetags.for_payload(payload).team
    dsto = _parse_asto(payload, _DSTO_NAME, data_slots=len(divisions))
    for div in divisions:
        div.list_off = dsto.data_off + div.row * LIST_SLOT_BYTES
        pos, rows = div.list_off, []
        for k in range(MAX_LIST_TEAMS):
            v = _u32(payload, pos + k * 4)
            if (v >> 16) != team_ref:
                break
            rows.append(v & 0xFFFF)
        div.team_rows = rows
    # the division store carries one count per division row, contiguous and in
    # row order, ending at (or just before) the grid. Locate that window in the
    # untrimmed run rather than assuming it is exactly the last n_div entries:
    # a stock save can leave padding after it, and an in-game-realigned save
    # ends it with real zero-counts for its empty trailing divisions. Search
    # nearest-the-grid first so a coincidental header run never wins.
    n_div = len(divisions)
    d_lengths = [len(d.team_rows) for d in divisions]
    dstart = _locate_count_window(dsto.counts, d_lengths)
    if dstart is not None:
        base = dsto.counts_off + dstart * 4
        for d in divisions:
            d.count_offs = [base + d.row * 4]
    else:
        writable = False
        notes.append("division count table did not match parsed lists")

    # structural conference -> divisions mapping. A record's f0 ref is either
    # a direct Division (0x3182, the Independents pattern) or a DivisionList
    # entry (0x3180) whose row encodes the list index as row // 2 (each list
    # occupies two elements; verified across every stock conference).
    # one division-list row per non-blank conference (conference-row order);
    # pass the count so a stale handle in a row's second slot can never be
    # mistaken for the end of the store
    live = [c for c in confs if not c.blank]
    div_lists = _parse_division_lists(payload, len(live))
    for conf in live:
        if conf.direct_division:
            conf.division_rows = [conf.direct_division_row]
        else:
            idx = (conf.divlist_row or 0) // 2
            if idx >= len(div_lists):
                raise ValueError(f"conference {conf.name!r}: division list {idx} out of range")
            conf.division_rows = list(div_lists[idx])

    # conference membership lists (ConferenceTeamListStore, in conference-row
    # order). Two passes so an UNDIVIDED conference works too: some saves keep
    # every conference's teams mirrored into its division, others leave the
    # divisions empty and hold the membership only here (observed live). Pass 1
    # matches by set-equality with the division union (order-independent, the
    # proven path when divisions carry the teams); pass 2 assigns the remaining
    # lists positionally to the still-unmatched conferences (whose empty
    # divisions give no union to match on). Because the store and the conference
    # rows share an order, pass 1 removes matching positions from both in step,
    # so the leftovers stay aligned.
    ctls = _parse_asto(payload, _CTLS_NAME)
    unions = {c.row: [r for dr in c.division_rows for r in divisions[dr].team_rows]
              for c in live}

    def _claim(conf, i, off, rows) -> None:
        used.add(i)
        conf.team_rows = list(rows)
        conf.list_off = off
        nxt = _next_nonzero(payload, off + len(rows) * 4, ctls.end_off)
        conf.list_capacity = min(LIST_SLOT_BYTES, nxt - off)

    used: set[int] = set()
    for conf in live:
        union = unions[conf.row]
        match = next(((i, off, rows) for i, (off, rows) in enumerate(ctls.lists)
                      if i not in used and union and set(rows) == set(union)), None)
        if match is not None:
            _claim(conf, *match)

    remaining = [i for i in range(len(ctls.lists)) if i not in used]
    ri = 0
    for conf in live:
        if conf.list_off is not None or conf.direct_division:
            continue  # already matched, or Independents (division-only, no list)
        if unions[conf.row]:
            # had teams in its divisions but no list matched: genuinely unresolved
            conf.team_rows = unions[conf.row]
            writable = False
            notes.append(f"no membership list matched conference {conf.name!r}")
        elif ri < len(remaining):
            i = remaining[ri]
            ri += 1
            _claim(conf, i, *ctls.lists[i])
        else:
            conf.team_rows = []

    # Independents (and any conference with no CTLS list): membership is its
    # division union.
    for conf in live:
        if conf.list_off is None:
            conf.team_rows = unions[conf.row]

    if len(used) != len(ctls.lists):
        writable = False
        notes.append("unmatched conference membership lists in the store")

    # counts for the conference store (stock doubled pairs, or the in-game
    # realignment's single-with-zero), in list order
    ordered = [c for c in confs if c.list_off is not None]
    ordered.sort(key=lambda c: c.list_off)
    pairs = _match_count_run(ctls.counts, [len(c.team_rows) for c in ordered])
    if pairs is None:
        writable = False
        notes.append("conference count table did not match parsed lists")
    else:
        for conf, idx in zip(ordered, pairs):
            conf.count_offs = [ctls.counts_off + i * 4 for i in idx]

    return ConferenceTable(conferences=confs, divisions=divisions,
                           records_off=records, strings_off=strings,
                           writable_membership=writable, notes=notes)


# --------------------------------------------------------------------------
# writing (in-place, same-length payload patches)
# --------------------------------------------------------------------------

def _fit(value: str, cap: int, what: str) -> bytes:
    raw = value.encode("latin1", "replace")
    if len(raw) >= cap:
        raise ValueError(f"{what} {value!r} is too long ({len(raw)} chars, max {cap - 1})")
    if b"\x00" in raw:
        raise ValueError(f"{what} may not contain NUL bytes")
    return raw + b"\x00" * (cap - len(raw))


def set_conference_strings(payload: bytearray, conf: Conference, *,
                           name: str | None = None, display: str | None = None,
                           champ_game: str | None = None) -> list[str]:
    """Rename a conference in place. Returns report lines."""
    if conf.blank:
        raise ValueError("cannot rename the blank conference slot")
    report = []
    for key, value in (("name", name), ("display", display), ("champ_game", champ_game)):
        if value is None:
            continue
        off, cap = CONF_FIELDS[key]
        payload[conf.strings_off + off:conf.strings_off + off + cap] = _fit(value, cap, f"conference {key}")
        report.append(f"conference row {conf.row}: {key} -> {value!r}")
    return report


def set_division_strings(payload: bytearray, div: Division, *,
                         name: str | None = None, display: str | None = None) -> list[str]:
    """Rename a division in place. Returns report lines."""
    report = []
    slot = div.strings_off  # points at the name field (+0 of the 53-byte slot)
    for key, value in (("name", name), ("display", display)):
        if value is None:
            continue
        off, cap = DIV_FIELDS[key]
        payload[slot + off:slot + off + cap] = _fit(value, cap, f"division {key}")
        report.append(f"division row {div.row}: {key} -> {value!r}")
    return report


def _write_list(payload: bytearray, off: int, capacity: int, rows: list[int], what: str) -> None:
    if len(rows) * 4 > capacity:
        raise ValueError(f"{what}: {len(rows)} teams exceed the list capacity ({capacity // 4})")
    team_ref = savetags.for_payload(payload).team
    data = b"".join(struct.pack(">I", (team_ref << 16) | r) for r in rows)
    payload[off:off + capacity] = data + b"\x00" * (capacity - len(data))


def set_memberships(payload: bytearray, table: ConferenceTable,
                    conference_teams: dict[int, list[int]],
                    division_teams: dict[int, list[int]]) -> list[str]:
    """Rewrite membership lists + their counts.

    `conference_teams` maps conference row -> complete team-row list (the
    Independents row is allowed and handled purely through its division);
    `division_teams` maps division row -> complete team-row list. Every
    conference's division lists must partition its conference list."""
    if not table.writable_membership:
        raise ValueError("membership tables were not parsed confidently; refusing to write")
    confs = {c.row: c for c in table.conferences}
    divs = {d.row: d for d in table.divisions}

    # validate before touching anything
    for row, rows in conference_teams.items():
        conf = confs[row]
        if conf.blank:
            raise ValueError("cannot assign teams to the blank conference slot")
        if len(set(rows)) != len(rows):
            raise ValueError(f"conference {conf.name!r}: duplicate teams")
        want = sorted(r for dr in conf.division_rows for r in division_teams.get(dr, divs[dr].team_rows))
        if sorted(rows) != want:
            raise ValueError(f"conference {conf.name!r}: division lists do not partition the member list")
        if conf.list_off is None:
            # only Independents (division-only membership) may lack a list slot
            if rows and not conf.direct_division:
                raise ValueError(f"conference {conf.name!r} has no membership list slot")
        elif len(rows) * 4 > conf.list_capacity:
            raise ValueError(f"conference {conf.name!r}: over capacity")
    for row, rows in division_teams.items():
        if len(rows) > MAX_LIST_TEAMS:
            raise ValueError(f"division {divs[row].name or row}: more than {MAX_LIST_TEAMS} teams")

    report: list[str] = []
    for row, rows in conference_teams.items():
        conf = confs[row]
        if conf.list_off is None:
            continue  # Independents: teams tracked in their division only
        _write_list(payload, conf.list_off, conf.list_capacity, rows,
                    f"conference {conf.name!r}")
        for off in conf.count_offs:
            struct.pack_into(">I", payload, off, len(rows))
        report.append(f"conference row {row} ({conf.name}): {len(rows)} teams")
    for row, rows in division_teams.items():
        div = divs[row]
        if div.list_off is None:
            raise ValueError(f"division {div.name or row} has no list slot")
        _write_list(payload, div.list_off, LIST_SLOT_BYTES, rows,
                    f"division {div.name or row!r}")
        for off in div.count_offs:
            struct.pack_into(">I", payload, off, len(rows))
        report.append(f"division row {row} ({div.name or 'unnamed'}): {len(rows)} teams")
    return report


def team_rows_by_name(payload: bytes) -> dict[str, int]:
    """Map full team name ('Alabama Crimson Tide') -> team row id."""
    return {t.name: i for i, t in enumerate(saveteams.parse_teams(payload))}


# --------------------------------------------------------------------------
# EXPERIMENTAL: activate the game's blank conference row as a real conference
# --------------------------------------------------------------------------
# The save carries exactly one dormant conference row (row 5) with a valid
# string quad, an empty string slot, and an empty membership list slot. The
# reference graph is closed (nothing else in the save references conferences
# by typed ref), so activation is: synthesize the record head the way the
# Independents row is built (a direct 0x3182 Division ref; every other ref
# field is provably optional), fill the strings, and give it a division. The
# game has no spare Division row, so the one multi-division conference (the
# Sun Belt) is flattened and its freed division is repurposed. The new
# conference is division-only like the Independents (no ConferenceTeamListStore
# entry), which sidesteps every count-table insert. In-game scheduling and
# championship behavior for an activated row is UNVERIFIED; callers must
# present this as experimental.

_NO_DIVS_STYLE = "NoDivsProtectedRivalsStyle"


def _divliststore_flatten(payload: bytearray, donor_rows: list[int]) -> int:
    """Shrink the donor conference's division list to its first entry.
    Returns the freed Division row."""
    at = payload.find(_DIVLIST_NAME + b"\x00")
    cmpc = payload.find(b"CMPC", at, at + 200)
    div_ref = savetags.for_payload(payload).div_ref
    pos = cmpc + 4
    while (_u32(payload, pos) >> 16) != div_ref:
        pos += 4
    data_off = pos
    # lists are 2-wide (8-byte) slots ending where the next block's type name
    # begins; find the donor's slot by content and count the total slots
    want = [(div_ref << 16) | r for r in donor_rows] + [0] * (2 - len(donor_rows))
    donor_idx, total = None, 0
    while True:
        a = _u32(payload, data_off + total * 8)
        b = _u32(payload, data_off + total * 8 + 4)
        if not all(v == 0 or (v >> 16) == div_ref for v in (a, b)):
            break
        if [a, b] == want:
            donor_idx = total
        total += 1
        if total > 64:
            raise ValueError("DivisionListStore did not terminate")
    if donor_idx is None:
        raise ValueError("donor division list not found in DivisionListStore")
    struct.pack_into(">I", payload, data_off + donor_idx * 8 + 4, 0)
    # the header's last `total` values are the per-list counts, in list order
    count_off = data_off - 4 * (total - donor_idx)
    if _u32(payload, count_off) != len(donor_rows):
        raise ValueError("DivisionListStore count did not match the donor list")
    struct.pack_into(">I", payload, count_off, 1)
    return donor_rows[-1]


def activate_blank_conference(payload: bytearray, table: ConferenceTable, *,
                              name: str, display: str, champ_game: str,
                              team_rows: list[int],
                              division_name: str = "") -> list[str]:
    """Turn the blank conference row into a real conference (EXPERIMENTAL)."""
    if not table.writable_membership:
        raise ValueError("membership tables were not parsed confidently; refusing to write")
    blank = next((c for c in table.conferences if c.blank), None)
    if blank is None:
        raise ValueError("the save has no blank conference slot left")
    if not 4 <= len(set(team_rows)) <= MAX_LIST_TEAMS or len(set(team_rows)) != len(team_rows):
        raise ValueError(f"a conference needs 4 to {MAX_LIST_TEAMS} distinct teams")
    report: list[str] = []

    # 1) free a Division row by flattening the multi-division conference
    donor = next((c for c in table.conferences if len(c.division_rows) > 1), None)
    if donor is None:
        raise ValueError("no multi-division conference to free a division from")
    keep_row, taken_row = donor.division_rows[0], donor.division_rows[-1]
    if len(donor.team_rows) > MAX_LIST_TEAMS:
        raise ValueError(f"{donor.display} cannot merge into one division")
    _divliststore_flatten(payload, donor.division_rows)
    off, cap = CONF_FIELDS["style"]
    payload[donor.strings_off + off:donor.strings_off + off + cap] = _fit(
        _NO_DIVS_STYLE, cap, "schedule style")
    report.append(f"{donor.display} merged into a single division to free one "
                  f"for the new conference")

    # 2) move the new conference's teams out of their current conferences and
    #    collapse the donor's divisions, all through the validated writer
    taken = set(team_rows)
    conf_teams: dict[int, list[int]] = {}
    div_teams: dict[int, list[int]] = {}
    for conf in table.conferences:
        if conf.blank:
            continue
        lost = [r for r in conf.team_rows if r in taken]
        if conf.row == donor.row:
            merged = [r for r in donor.team_rows if r not in taken]
            conf_teams[conf.row] = merged
            div_teams[keep_row] = merged
            div_teams[taken_row] = []
            continue
        if not lost:
            continue
        remaining = [r for r in conf.team_rows if r not in taken]
        if not conf.direct_division and len(remaining) < 4:
            raise ValueError(f"{conf.display or conf.name} would drop under 4 teams")
        conf_teams[conf.row] = remaining
        for dr in conf.division_rows:
            div_teams[dr] = [r for r in table.divisions[dr].team_rows if r not in taken]
    # the donor keeps two division rows in the parsed table, so its partition
    # (kept division = all members, freed division = empty) stays valid here
    donor.division_rows = [keep_row, taken_row]
    report += set_memberships(payload, table, conf_teams, div_teams)

    # 3) the freed division now belongs to the new conference: name + members.
    # The donor's kept division loses its name too, matching how every other
    # single-division conference stores an unnamed division.
    set_division_strings(payload, table.divisions[keep_row], name="", display="")
    div = table.divisions[taken_row]
    set_division_strings(payload, div, name=division_name or "",
                         display=division_name or "")
    _write_list(payload, div.list_off, LIST_SLOT_BYTES, team_rows, "new conference division")
    for c_off in div.count_offs:
        struct.pack_into(">I", payload, c_off, len(team_rows))

    # 4) the record head: direct Division ref + next free instance id + enum
    t = savetags.for_payload(payload)
    rec = table.records_off + blank.row * CONF_RECORD_SIZE
    struct.pack_into(">I", payload, rec, (t.div << 16) | taken_row)
    next_id = max(struct.unpack_from(">H", payload, table.records_off + c.row *
                                     CONF_RECORD_SIZE + 38)[0]
                  for c in table.conferences if not c.blank) + 1
    struct.pack_into(">HH", payload, rec + 36, t.conf, next_id)
    enums = [struct.unpack_from(">H", payload, table.records_off + c.row *
                                CONF_RECORD_SIZE + 58)[0]
             for c in table.conferences if not c.blank]
    enum = max(e for e in enums if e < 22) + 1  # skip the Independents' 22
    struct.pack_into(">HH", payload, rec + 56, enum + 10, enum)

    # 5) the strings
    slot = blank.strings_off
    for key, value in (("name", name), ("champ_game", champ_game),
                       ("display", display), ("style", _NO_DIVS_STYLE)):
        off, cap = CONF_FIELDS[key]
        payload[slot + off:slot + off + cap] = _fit(value, cap, f"conference {key}")

    report.append(f"activated the game's dormant conference slot as {display!r} "
                  f"({len(team_rows)} teams, enum {enum}, instance {next_id})")
    report.append("EXPERIMENTAL: the game has never had a 12th conference; verify "
                  "scheduling and standings in game before committing a season to it")
    return report


# --------------------------------------------------------------------------
# EXPERIMENTAL: grow the tables (byte insertion) for conferences 13+
# --------------------------------------------------------------------------
# The payload is a sequential block stream: 2407 SPBF/ASTO blocks (the count
# in the FrTk header), every cross-reference is (type,row) or block-relative,
# and probing block start offsets finds no absolute-offset directory. So
# tables can GROW: insert a record + string slot and patch the block's size
# and row-count header fields. Every patch is located by expected current
# VALUE with an exact occurrence count, and the writer refuses on any
# mismatch rather than guessing.


def _patch_header_values(payload: bytearray, lo: int, hi: int,
                         changes: dict[int, tuple[int, int]]) -> None:
    """In [lo,hi), replace u32be `old` with `new`, requiring exactly `count`
    occurrences per entry. changes: {old: (new, count)}."""
    for old, (new, count) in changes.items():
        offs = []
        pos = lo
        needle = struct.pack(">I", old)
        while True:
            i = payload.find(needle, pos, hi)
            if i == -1:
                break
            offs.append(i)
            pos = i + 1
        if len(offs) != count:
            raise ValueError(f"header patch: expected {count} x {old:#x} in "
                             f"[{lo},{hi}), found {len(offs)}")
        for off in offs:
            struct.pack_into(">I", payload, off, new)


def _grown(payload: bytes, inserts: list[tuple[int, bytes]]) -> bytearray:
    """Apply (offset, blob) insertions; offsets refer to the ORIGINAL payload."""
    out = bytearray()
    last = 0
    for off, blob in sorted(inserts):
        out += payload[last:off]
        out += blob
        last = off
    out += payload[last:]
    return out


def add_conference(payload_in: bytes, table: ConferenceTable, *,
                   name: str, display: str, champ_game: str,
                   team_rows: list[int],
                   division_name: str = "") -> tuple[bytearray, list[str]]:
    """Create a brand-new conference row + division row by GROWING the save's
    tables (EXPERIMENTAL). Returns (new payload, report)."""
    if not table.writable_membership:
        raise ValueError("membership tables were not parsed confidently; refusing to write")
    if not 4 <= len(set(team_rows)) <= MAX_LIST_TEAMS or len(set(team_rows)) != len(team_rows):
        raise ValueError(f"a conference needs 4 to {MAX_LIST_TEAMS} distinct teams")
    payload = bytearray(payload_in)
    report: list[str] = []
    n_conf = len(table.conferences)
    n_div = len(table.divisions)

    # 1) move the new conference's teams out of their current homes (in place,
    #    before any insertion shifts offsets)
    taken = set(team_rows)
    conf_teams: dict[int, list[int]] = {}
    div_teams: dict[int, list[int]] = {}
    for conf in table.conferences:
        if conf.blank:
            continue
        lost = [r for r in conf.team_rows if r in taken]
        if not lost:
            continue
        remaining = [r for r in conf.team_rows if r not in taken]
        if not conf.direct_division and len(remaining) < 4:
            raise ValueError(f"{conf.display or conf.name} would drop under 4 teams")
        conf_teams[conf.row] = remaining
        for dr in conf.division_rows:
            div_teams[dr] = [r for r in table.divisions[dr].team_rows if r not in taken]
    if conf_teams:
        report += set_memberships(payload, table, conf_teams, div_teams)

    # 2) header patches, all by exact expected value (sizes decompose as
    #    field-table + rows*stride; ASTO dataSize = 32 + counts + slots)
    # windows end where each block's field bit-offset table (or count run)
    # begins, so table values can never collide with the patch targets
    conf_records = table.records_off
    conf_strings_end = table.strings_off + n_conf * CONF_STRING_SLOT
    _patch_header_values(payload, conf_records - 260, conf_records - 168, {
        200 + n_conf * CONF_RECORD_SIZE: (200 + (n_conf + 1) * CONF_RECORD_SIZE, 2),
        n_conf * CONF_STRING_SLOT: ((n_conf + 1) * CONF_STRING_SLOT, 1),
        200 + n_conf * (CONF_RECORD_SIZE + CONF_STRING_SLOT):
            (200 + (n_conf + 1) * (CONF_RECORD_SIZE + CONF_STRING_SLOT), 1),
        n_conf: (n_conf + 1, 3),
    })

    div_name_at = payload.find(_DIVSTORE_NAME + b"\x00")
    # locate the record region via the store header, not the per-record self-tag
    # (some saves carry a runtime handle in a record's leading bytes; see
    # _bsft_store), so growth works on those saves too
    div_records = _division_store_offset(payload)
    div_strings = div_records + n_div * DIV_RECORD_SIZE
    div_strings_end = div_strings + n_div * DIV_STRING_SLOT
    # window starts past the name string (its length prefix can equal a count)
    _patch_header_values(payload, div_name_at + len(_DIVSTORE_NAME) + 1, div_records - 16, {
        48 + n_div * DIV_RECORD_SIZE: (48 + (n_div + 1) * DIV_RECORD_SIZE, 2),
        n_div * DIV_STRING_SLOT: ((n_div + 1) * DIV_STRING_SLOT, 1),
        48 + n_div * (DIV_RECORD_SIZE + DIV_STRING_SLOT):
            (48 + (n_div + 1) * (DIV_RECORD_SIZE + DIV_STRING_SLOT), 1),
        n_div: (n_div + 1, 4),
    })

    t = savetags.for_payload(payload)
    dsto_at = payload.find(_DSTO_NAME + b"\x00")
    dsto_cmpc = payload.find(b"CMPC", dsto_at, dsto_at + 200)
    pos = dsto_cmpc + 12
    while (_u32(payload, pos) >> 16) != t.team:
        pos += 4
    dsto_data = pos
    dsto_end = dsto_data + n_div * LIST_SLOT_BYTES
    _patch_header_values(payload, dsto_at + len(_DSTO_NAME) + 1, dsto_data - n_div * 4, {
        32 + n_div * (4 + LIST_SLOT_BYTES): (32 + (n_div + 1) * (4 + LIST_SLOT_BYTES), 3),
        n_div: (n_div + 1, 3),
    })

    # 3) build the new rows and insert (original offsets; _grown sorts them)
    new_div = n_div
    new_row = n_conf
    div_record = struct.pack(">HHIII", t.div, new_div,
                             new_div * DIV_STRING_SLOT + DIV_FIELDS["display"][0],
                             new_div * DIV_STRING_SLOT, 0)
    div_slot = bytearray(DIV_STRING_SLOT)
    div_slot[0:DIV_FIELDS["name"][1]] = _fit(division_name or "", DIV_FIELDS["name"][1], "division name")
    div_slot[DIV_FIELDS["display"][0]:DIV_FIELDS["display"][0] + DIV_FIELDS["display"][1]] = \
        _fit(division_name or "", DIV_FIELDS["display"][1], "division display")

    member_slot = bytearray(LIST_SLOT_BYTES)
    for k, r in enumerate(team_rows):
        struct.pack_into(">I", member_slot, k * 4, (t.team << 16) | r)

    conf_record = bytearray(CONF_RECORD_SIZE)
    struct.pack_into(">I", conf_record, 0, (t.div << 16) | new_div)
    next_id = max(struct.unpack_from(">H", payload, conf_records + c.row *
                                     CONF_RECORD_SIZE + 38)[0]
                  for c in table.conferences if not c.blank) + 1
    struct.pack_into(">HH", conf_record, 36, t.conf, next_id)
    struct.pack_into(">4I", conf_record, 40, *(new_row * CONF_STRING_SLOT + off for off, _ in
                     (CONF_FIELDS["name"], CONF_FIELDS["style"],
                      CONF_FIELDS["champ_game"], CONF_FIELDS["display"])))
    enums = [struct.unpack_from(">H", payload, conf_records + c.row *
                                CONF_RECORD_SIZE + 58)[0]
             for c in table.conferences if not c.blank]
    enum = max([e for e in enums if e < 22] + [10]) + 1
    struct.pack_into(">HH", conf_record, 56, enum + 10, enum)

    conf_slot = bytearray(CONF_STRING_SLOT)
    for key, value in (("name", name), ("champ_game", champ_game),
                       ("display", display), ("style", _NO_DIVS_STYLE)):
        off, cap = CONF_FIELDS[key]
        conf_slot[off:off + cap] = _fit(value, cap, f"conference {key}")

    grown = _grown(bytes(payload), [
        (conf_strings_end, bytes(conf_slot)),
        (table.strings_off, bytes(conf_record)),     # records end = strings start
        (div_strings_end, bytes(div_slot)),
        (div_strings, div_record),                   # records end = strings start
        (dsto_data, struct.pack(">I", len(team_rows))),  # the new count entry
        (dsto_end, bytes(member_slot)),
    ])

    report.append(f"grew the conference table to {n_conf + 1} rows: added {display!r} "
                  f"({len(team_rows)} teams, division row {new_div}, enum {enum}, "
                  f"instance {next_id})")
    report.append("EXPERIMENTAL: table growth is byte insertion into the save's "
                  "block stream; verify the save loads in game before trusting it")
    return grown, report
