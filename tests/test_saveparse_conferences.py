"""Tests for the conference/division structures parser + writer
(`backend.saveparse.conferences`) and the FBCHUNKS encoder."""
import os
import struct
import zlib
from pathlib import Path

import pytest

from backend.saveparse import conferences as confmod
from backend.saveparse import container

# ---------------------------------------------------------------------------
# synthetic payload: a miniature save carrying every structure the parser
# reads, laid out exactly like the real one (12 conference rows with the
# blank slot at row 5 and Independents at row 6)
# ---------------------------------------------------------------------------

CONFS = [
    # (name, champ game, display, style) per row; None = the blank slot
    ("ACC", "ACC Championship", "ACC", "NoDivsProtectedRivalsStyle"),
    ("American", "American Championship", "American", "NoDivsProtectedRivalsStyle"),
    ("Big_12", "Big 12 Championship", "Big 12", "NoDivsProtectedRivalsStyle"),
    ("Big_Ten", "Big Ten Championship", "Big Ten", "NoDivsProtectedRivalsStyle"),
    ("C_USA", "Conference USA Championship", "CUSA", "NoDivsProtectedRivalsStyle"),
    None,
    ("FBS_Independents", "", "Independent", ""),
    ("MAC", "MAC Championship", "MAC", "NoDivsProtectedRivalsStyle"),
    ("MWC", "Mountain West Championship", "MWC", "NoDivsProtectedRivalsStyle"),
    ("Pac_12", "Pac-12 Championship", "Pac-12", "NoDivsProtectedRivalsStyle"),
    ("SEC", "SEC Championship", "SEC", "NoDivsProtectedRivalsStyle"),
    ("Sun_Belt", "Sun Belt Championship", "Sun Belt", "EvenDivsOverlappingGamesStyle"),
]
DIV_NAMES = ["", "", "", "", "", "FBS Independents", "", "", "", "", "East", "West"]
# division row -> team rows; divisions 0-4 and 6-9 mirror their conference,
# Independents (5) hold two teams, the Sun Belt splits across East/West
DIV_TEAMS = {
    0: [0, 1, 2, 3], 1: [4, 5, 6, 7], 2: [8, 9, 10, 11], 3: [12, 13, 14, 15],
    4: [16, 17, 18, 19], 5: [90, 91], 6: [20, 21, 22, 23, 80, 81, 82, 83],
    7: [24, 25, 26, 27],
    8: [28, 29, 30, 31], 9: [32, 33, 34, 35], 10: [36, 37], 11: [38, 39],
}
# non-blank conference (in row order) -> division rows
CONF_DIVS = [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9], [10, 11]]


def _pad(s: str, cap: int) -> bytes:
    raw = s.encode("latin1")
    assert len(raw) < cap
    return raw + b"\x00" * (cap - len(raw))


def build_payload(count_shape: str = "doubled") -> bytes:
    """`count_shape`: 'doubled' is the stock ConferenceTeamListStore layout
    (each count written twice); 'single' is the shape CFB 27 writes after an
    in-game dynasty realignment (each count once, followed by a zero)."""
    buf = bytearray(b"FrTk" + b"\x00" * 40)
    # SPBF/BSFT header fields the growth writer patches by exact value:
    # sizes (field-table + rows*stride), the string bytes, the total, and the
    # row count (x3), followed by a stand-in for the 168-byte bit-offset table
    buf += struct.pack(">7I", 12, 200 + 12 * 80, 12 * 136, 200 + 12 * (80 + 136),
                       200 + 12 * 80, 12, 12)
    buf += b"\x00" * (92 - 28)
    buf += b"\x01" * 168

    # --- conference records + strings -------------------------------------
    tag_id = 0
    for row, spec in enumerate(CONFS):
        rec = bytearray(confmod.CONF_RECORD_SIZE)
        quad = tuple(row * confmod.CONF_STRING_SLOT + off for off, _ in
                     (confmod.CONF_FIELDS["name"], confmod.CONF_FIELDS["style"],
                      confmod.CONF_FIELDS["champ_game"], confmod.CONF_FIELDS["display"]))
        struct.pack_into(">4I", rec, 40, *quad)
        if spec is not None:
            # f0 ref: Independents point at their Division directly; everyone
            # else references their DivisionList entry (list k = element 2k,
            # matching the real save's encoding)
            if spec[0] == "FBS_Independents":
                struct.pack_into(">I", rec, 0, (confmod.DIV_TAG << 16) | 5)
            else:
                struct.pack_into(">I", rec, 0, (confmod.DIVLIST_TAG << 16) | (2 * tag_id))
            struct.pack_into(">HH", rec, 36, confmod.CONF_TAG, tag_id)
            tag_id += 1
        buf += rec
    for spec in CONFS:
        slot = bytearray(confmod.CONF_STRING_SLOT)
        if spec is not None:
            name, champ, disp, style = spec
            for key, val in (("name", name), ("champ_game", champ),
                             ("display", disp), ("style", style)):
                off, cap = confmod.CONF_FIELDS[key]
                slot[off:off + cap] = _pad(val, cap)
        buf += slot

    # --- DivisionStore ------------------------------------------------------
    buf += b"\x00" * 8 + b"DivisionStore\x00"
    buf += struct.pack(">8I", 48 + 12 * 16, 12 * 53, 48 + 12 * (16 + 53),
                       48 + 12 * 16, 12, 12, 12, 12)
    buf += b"\x01" * 16  # stand-in for the 4-field bit-offset table
    for row in range(confmod.DIV_COUNT):
        buf += struct.pack(">HHIII", confmod.DIV_TAG, row,
                           row * confmod.DIV_STRING_SLOT + 21,
                           row * confmod.DIV_STRING_SLOT, 0)
    for name in DIV_NAMES:
        slot = bytearray(confmod.DIV_STRING_SLOT)
        slot[0:21] = _pad(name, 21)
        slot[21:53] = _pad(name, 32)
        buf += slot

    # --- DivisionListStore (11 lists of division refs, 2-wide slots) --------
    buf += b"\x00" * 8 + b"DivisionListStore\x00"
    while (len(buf) + 4 + 8) % 4:
        buf += b"\x00"
    buf += b"CMPC" + struct.pack(">2I", 0xA4, 0xA4) + struct.pack(">5I", 2, 11, 2, 19, 11)
    buf += struct.pack(">11I", *([1] * 10 + [2]))  # per-list division counts
    for rows in CONF_DIVS:
        slot = [(confmod.DIV_REF << 16) | r for r in rows] + [0] * (2 - len(rows))
        buf += struct.pack(">2I", *slot)
    buf += b"Next[]\x00\x00"

    # --- ConferenceTeamListStore --------------------------------------------
    conf_team_lists = [DIV_TEAMS[0], DIV_TEAMS[1], DIV_TEAMS[2], DIV_TEAMS[3],
                       DIV_TEAMS[4], DIV_TEAMS[6], DIV_TEAMS[7], DIV_TEAMS[8],
                       DIV_TEAMS[9], DIV_TEAMS[10] + DIV_TEAMS[11]]
    buf += b"\x00" * 8 + b"ConferenceTeamListStore\x00"
    while (len(buf) + 4 + 8) % 4:
        buf += b"\x00"
    buf += b"CMPC" + struct.pack(">2I", 0x704, 0x704)
    if count_shape == "single":
        # in-game-realignment shape: each count once, then a zero separator;
        # a stray extra zero mid-run and a non-zero trailing value, both as in
        # the real DYNASTY-INITIALWYOMING saves
        counts = [20, 21, 20, 29, 0, 0]
        for i, lst in enumerate(conf_team_lists):
            counts += [len(lst), 0]
            if i == 4:
                counts.append(0)
        counts.append(2)
    else:
        counts = [20, 21, 20, 29, 6]
        for i, lst in enumerate(conf_team_lists):
            counts += [len(lst), len(lst)]
            if i == 4:
                counts.append(3)  # stray single value, as in the real save
        counts.append(13)
    buf += struct.pack(f">{len(counts)}I", *counts)
    buf += b"\x00" * 8  # zero padding between counts and data
    for i, lst in enumerate(conf_team_lists):
        slot = bytearray(confmod.LIST_SLOT_BYTES)
        for k, r in enumerate(lst):
            struct.pack_into(">I", slot, k * 4, (confmod.TEAM_REF << 16) | r)
        buf += slot
        lone = bytearray(confmod.LIST_SLOT_BYTES)  # interleaved bare value slot
        struct.pack_into(">I", lone, 0, 7 + i)
        buf += lone
    buf += b"Team[]\x00\x00"

    # --- DivisionTeamListStore ------------------------------------------------
    buf += b"\x00" * 8 + b"DivisionTeamListStore\x00"
    while (len(buf) + 4 + 8) % 4:
        buf += b"\x00"
    buf += struct.pack(">2I", 12, 0x410)  # ASTO numLists + dataSize
    buf += b"CMPC" + struct.pack(">2I", 0x410, 0x410) + struct.pack(">5I", 20, 12, 20, 20, 12)
    buf += struct.pack(">12I", *[len(DIV_TEAMS[r]) for r in range(12)])
    for row in range(12):
        slot = bytearray(confmod.LIST_SLOT_BYTES)
        for k, r in enumerate(DIV_TEAMS[row]):
            struct.pack_into(">I", slot, k * 4, (confmod.TEAM_REF << 16) | r)
        buf += slot
    buf += b"Team[]\x00\x00"
    return bytes(buf)


@pytest.fixture()
def payload() -> bytes:
    return build_payload()


def test_parse_conferences(payload):
    t = confmod.parse(payload)
    assert [c.name for c in t.conferences if not c.blank] == [s[0] for s in CONFS if s]
    assert t.conferences[5].blank
    acc = t.by_name("ACC")
    assert acc.team_rows == [0, 1, 2, 3]
    assert acc.champ_game == "ACC Championship"
    assert acc.list_capacity == confmod.LIST_SLOT_BYTES
    sb = t.by_name("Sun_Belt")
    assert sb.division_rows == [10, 11]
    assert [t.divisions[r].name for r in sb.division_rows] == ["East", "West"]
    assert sb.team_rows == [36, 37, 38, 39]
    ind = t.independents
    assert ind.name == "FBS_Independents"
    assert ind.team_rows == [90, 91]
    assert ind.list_off is None
    assert t.writable_membership, t.notes


def test_rename_roundtrip(payload):
    buf = bytearray(payload)
    t = confmod.parse(payload)
    confmod.set_conference_strings(buf, t.by_name("Pac_12"), name="Pacific",
                                   display="Pacific Coast", champ_game="Pacific Title Game")
    confmod.set_division_strings(buf, t.divisions[10], name="North", display="North")
    t2 = confmod.parse(bytes(buf))
    pac = t2.conferences[9]
    assert (pac.name, pac.display, pac.champ_game) == ("Pacific", "Pacific Coast", "Pacific Title Game")
    assert t2.divisions[10].name == "North"
    assert t2.by_name("Sun_Belt").team_rows == [36, 37, 38, 39]  # neighbours untouched


def test_rename_rejects_too_long_and_nul(payload):
    buf = bytearray(payload)
    t = confmod.parse(payload)
    with pytest.raises(ValueError):
        confmod.set_conference_strings(buf, t.by_name("SEC"), display="X" * 21)
    with pytest.raises(ValueError):
        confmod.set_conference_strings(buf, t.by_name("SEC"), name="bad\x00name")
    with pytest.raises(ValueError):
        confmod.set_conference_strings(buf, t.conferences[5], name="NewConf")  # blank slot


def test_membership_move(payload):
    buf = bytearray(payload)
    t = confmod.parse(payload)
    acc, sec = t.by_name("ACC"), t.by_name("SEC")
    conf_teams = {acc.row: [0, 1, 2], sec.row: [32, 33, 34, 35, 3]}
    div_teams = {0: [0, 1, 2], 9: [32, 33, 34, 35, 3]}
    confmod.set_memberships(buf, t, conf_teams, div_teams)
    t2 = confmod.parse(bytes(buf))
    assert t2.by_name("ACC").team_rows == [0, 1, 2]
    assert t2.by_name("SEC").team_rows == [32, 33, 34, 35, 3]
    assert t2.writable_membership, t2.notes


def test_membership_move_to_independents(payload):
    buf = bytearray(payload)
    t = confmod.parse(payload)
    acc, ind = t.by_name("ACC"), t.independents
    confmod.set_memberships(
        buf, t,
        {acc.row: [0, 1, 2], ind.row: [90, 91, 3]},
        {0: [0, 1, 2], 5: [90, 91, 3]})
    t2 = confmod.parse(bytes(buf))
    assert t2.independents.team_rows == [90, 91, 3]
    assert t2.by_name("ACC").team_rows == [0, 1, 2]


def test_membership_validation(payload):
    buf = bytearray(payload)
    t = confmod.parse(payload)
    acc = t.by_name("ACC")
    with pytest.raises(ValueError):  # divisions must partition the conference
        confmod.set_memberships(buf, t, {acc.row: [0, 1]}, {0: [0, 1, 2]})
    with pytest.raises(ValueError):  # over slot capacity
        confmod.set_memberships(buf, t, {acc.row: list(range(21))}, {0: list(range(21))})
    with pytest.raises(ValueError):  # duplicates
        confmod.set_memberships(buf, t, {acc.row: [0, 0, 1]}, {0: [0, 0, 1]})


def test_encode_roundtrip(payload):
    original = _fbchunks(payload, pad=100_000)
    out = container.encode(original, payload)
    assert out == original[:len(out)] + b"" or container.decode(out).payload == payload
    assert len(out) == len(original)
    # a patched payload decodes back and the compressed-length field tracks it
    patched = bytearray(payload)
    t = confmod.parse(payload)
    confmod.set_conference_strings(patched, t.by_name("SEC"), display="Super East")
    out2 = container.encode(original, bytes(patched))
    c2 = container.decode(out2)
    assert confmod.parse(c2.payload).conferences[10].display == "Super East"
    assert c2.compressed_len == len(zlib.compress(bytes(patched), 6))


def test_encode_rejects_oversized(payload):
    original = _fbchunks(payload, pad=0)[:100]  # slot far too small
    with pytest.raises(ValueError):
        container.encode(original, payload + os.urandom(200_000))


def _fbchunks(payload: bytes, pad: int) -> bytes:
    buf = bytearray(82)
    buf[0:8] = container.MAGIC
    struct.pack_into("<H", buf, 8, 1)
    struct.pack_into("<6H", buf, 22, 2026, 7, 6, 12, 0, 0)
    build = b"College-27-RL1-9039126\x00"
    buf[34:34 + len(build)] = build
    stream = zlib.compress(payload, 6)
    struct.pack_into("<I", buf, 74, len(stream))  # compressed-length field
    return bytes(buf) + stream + b"\x00" * pad


def test_activate_blank_conference(payload):
    buf = bytearray(payload)
    t = confmod.parse(payload)
    # 4 MAC teams leave for the new league (MAC keeps 4); the Sun Belt merges
    rep = confmod.activate_blank_conference(
        buf, t, name="Heartland", display="Heartland",
        champ_game="Heartland Championship", team_rows=[80, 81, 82, 83])
    assert any("dormant" in line for line in rep)
    t2 = confmod.parse(bytes(buf))
    assert len([c for c in t2.conferences if not c.blank]) == 12
    heart = t2.by_name("Heartland")
    assert heart.row == 5 and heart.direct_division
    assert heart.team_rows == [80, 81, 82, 83]
    assert heart.champ_game == "Heartland Championship"
    assert t2.independents.name == "FBS_Independents"  # not confused with the new conf
    assert t2.by_name("MAC").team_rows == [20, 21, 22, 23]
    sb = t2.by_name("Sun_Belt")
    assert sb.division_rows == [10] and sorted(sb.team_rows) == [36, 37, 38, 39]
    assert sb.style == "NoDivsProtectedRivalsStyle"
    assert t2.writable_membership, t2.notes
    # the one dormant slot is spent
    with pytest.raises(ValueError, match="no blank conference slot"):
        confmod.activate_blank_conference(buf, t2, name="X", display="X",
                                          champ_game="X", team_rows=[0, 1, 2, 3])


def test_activate_guards(payload):
    t = confmod.parse(payload)
    with pytest.raises(ValueError, match="4 to 20"):
        confmod.activate_blank_conference(bytearray(payload), t, name="X",
                                          display="X", champ_game="X", team_rows=[80])
    with pytest.raises(ValueError, match="under 4 teams"):
        confmod.activate_blank_conference(bytearray(payload), t, name="X",
                                          display="X", champ_game="X",
                                          team_rows=[0, 1, 2, 3])  # guts the ACC


def test_add_conference_growth(payload):
    t = confmod.parse(payload)
    grown, rep = confmod.add_conference(
        payload, t, name="Heartland", display="Heartland",
        champ_game="Heartland Championship", team_rows=[80, 81, 82, 83])
    assert any("grew the conference table" in line for line in rep)
    assert len(grown) == len(payload) + 80 + 136 + 16 + 53 + 4 + 80
    t2 = confmod.parse(bytes(grown))
    heart = t2.by_name("Heartland")
    assert heart.row == 12 and heart.direct_division
    assert heart.team_rows == [80, 81, 82, 83]
    assert len(t2.divisions) == 13
    assert t2.by_name("MAC").team_rows == [20, 21, 22, 23]
    sb = t2.by_name("Sun_Belt")
    assert sb.division_rows == [10, 11]  # divisions intact, no sacrifice
    assert t2.conferences[5].blank      # the dormant row is untouched too
    assert t2.writable_membership, t2.notes
    # and it can grow again
    t3 = confmod.parse(bytes(grown))
    grown2, _ = confmod.add_conference(
        bytes(grown), t3, name="Plains", display="Plains",
        champ_game="Plains Championship", team_rows=[84, 85, 86, 87])
    t4 = confmod.parse(bytes(grown2))
    assert t4.by_name("Plains").row == 13
    assert len(t4.divisions) == 14
    assert t4.by_name("Heartland").team_rows == [80, 81, 82, 83]


# --- stale runtime-handle tolerance (DYNASTY-MICHIGAN regression) ----------
# A real save (DYNASTY-MICHIGAN) carried runtime handle values where the parser
# expected canonical self-tags: some DivisionStore records read 0x2cc2/0x2524
# instead of 0x3182|row, and the second slot of DivisionListStore rows held a
# stale ref (0x2178|n) instead of 0. The old readers bailed ("DivisionStore
# records not found") and stopped after the first division list, which blanked
# BOTH the Conferences and the Rankings pages ("No CFB 27 save was found").

def _bsft_division_store(div_names, tag_overrides=None) -> bytes:
    """A DivisionStore block with a real BSFT header (as every real save has),
    optionally clobbering some records' leading 2-byte tag with a runtime handle
    instead of DIV_TAG. Layout: name, pre-BSFT store words, BSFT + 6 header u32s,
    a 5-entry bit-offset table, n 16-byte records, then n 53-byte string slots."""
    tag_overrides = tag_overrides or {}
    n = len(div_names)
    total = 28 + 5 * 4 + n * confmod.DIV_RECORD_SIZE  # BSFT hdr + fieldtable + records
    blk = bytearray()
    blk += b"\x00" * 8 + confmod._DIVSTORE_NAME + b"\x00"
    blk += struct.pack(">6I", 0x410018, 0x8E, 0xC, 0, 0xF0, 0x27C)  # pre-BSFT store words
    blk += b"BSFT" + struct.pack(">6I", total, total + n * confmod.DIV_STRING_SLOT, 4, n, 4, n)
    blk += b"\x01" * 20  # 5-field bit-offset table (fields = w[4] + 1)
    for row in range(n):
        tag = tag_overrides.get(row, confmod.DIV_TAG)
        second = row if tag == confmod.DIV_TAG else 0  # real save zeros the low half too
        blk += struct.pack(">HHIII", tag, second,
                           row * confmod.DIV_STRING_SLOT + 21, row * confmod.DIV_STRING_SLOT, 0)
    for name in div_names:
        slot = bytearray(confmod.DIV_STRING_SLOT)
        slot[0:21] = _pad(name, 21)
        slot[21:53] = _pad(name, 32)
        blk += slot
    return bytes(blk)


def test_parse_divisions_bsft_tolerates_stale_record_handles():
    names = ["", "", "", "", "", "FBS Independents", "", "", "", "", "East", "West"]
    blk = _bsft_division_store(names, tag_overrides={0: 0x2CC2, 2: 0x2CBC, 3: 0x2524})
    payload = b"FrTk" + b"\x00" * 64 + blk
    divs = confmod._parse_divisions(payload)
    assert [d.name for d in divs] == names
    assert divs[10].name == "East" and divs[11].name == "West"


def test_parse_asto_empty_leading_slot():
    """An ASTO team-list store whose FIRST slots are EMPTY (zeros, sometimes a
    stray value) must still locate its 80-byte data grid. The DYNASTY-NCAA27
    regression: undivided conferences left the leading division slots empty, so
    the old 'scan for the first team ref' either mis-placed the grid or ran off
    the end ('count run too long'), blanking both the Conferences and Rankings
    pages. With the slot count known, the grid is pinned by the store's
    terminator instead."""
    TEAM = confmod.TEAM_REF
    slots = [[], [], [10, 11], [20, 21, 22]]  # first two divisions empty
    buf = bytearray(b"\x00" * 16 + confmod._DSTO_NAME + b"\x00")
    while len(buf) % 4:
        buf += b"\x00"
    buf += b"CMPC" + struct.pack(">2I", 0, 0)
    buf += struct.pack(">4I", 0, 0, 2, 3)     # count run: one per slot
    for k, teams in enumerate(slots):
        slot = bytearray(confmod.LIST_SLOT_BYTES)
        if k == 0:
            struct.pack_into(">I", slot, 0, 1)  # stray value in the empty slot
        for j, r in enumerate(teams):
            struct.pack_into(">I", slot, j * 4, (TEAM << 16) | r)
        buf += slot
    buf += b"Team[]\x00\x00"

    asto = confmod._parse_asto(bytes(buf), confmod._DSTO_NAME, data_slots=len(slots))

    def slot_rows(k):
        rows = []
        for j in range(confmod.MAX_LIST_TEAMS):
            v = struct.unpack_from(">I", bytes(buf), asto.data_off + k * 80 + j * 4)[0]
            if (v >> 16) != TEAM:
                break
            rows.append(v & 0xFFFF)
        return rows

    # data_off lands on the TRUE first (empty) slot, so per-slot indexing holds
    assert slot_rows(0) == []
    assert slot_rows(2) == [10, 11]
    assert slot_rows(3) == [20, 21, 22]


def test_division_lists_tolerate_stale_second_slot(payload):
    clean = confmod.parse(payload)
    buf = bytearray(payload)
    dl_at = buf.find(confmod._DIVLIST_NAME + b"\x00")
    cmpc = buf.find(b"CMPC", dl_at, dl_at + 200)
    pos = cmpc + 4
    while (struct.unpack_from(">I", buf, pos)[0] >> 16) != confmod.DIV_REF:
        pos += 4
    # a stale runtime handle in the first list row's otherwise-unused second slot
    struct.pack_into(">I", buf, pos + 4, (0x2178 << 16) | 1)
    t = confmod.parse(bytes(buf))
    assert [c.name for c in t.conferences if not c.blank] == \
           [c.name for c in clean.conferences if not c.blank]
    assert t.by_name("Sun_Belt").division_rows == [10, 11]
    assert t.by_name("SEC").team_rows == clean.by_name("SEC").team_rows
    assert t.independents.team_rows == clean.independents.team_rows


# --- real-save coverage (opt-in) -------------------------------------------

@pytest.mark.skipif(not os.environ.get("CFB27_SAVE"), reason="set CFB27_SAVE to a real autosave to run")
def test_real_save_conferences():
    c = container.decode(os.environ["CFB27_SAVE"])
    t = confmod.parse(c.payload)
    names = [x.name for x in t.conferences if not x.blank]
    assert "SEC" in names and "Sun_Belt" in names and len(names) == 11
    sb = t.by_name("Sun_Belt")
    assert [t.divisions[r].name for r in sb.division_rows] == ["East", "West"]
    assert t.independents is not None
    assert t.writable_membership, t.notes
    assert all(4 <= len(x.team_rows) <= 20 for x in t.conferences
               if not x.blank and not x.direct_division)


@pytest.mark.skipif(not os.environ.get("CFB27_SAVE"), reason="set CFB27_SAVE to a real autosave to run")
def test_real_save_noop_reencode():
    raw = Path(os.environ["CFB27_SAVE"]).read_bytes()
    c = container.decode(raw)
    out = container.encode(raw, c.payload)
    assert len(out) == len(raw)
    assert container.decode(out).payload == c.payload


# --- count-table shapes: stock doubled vs in-game-realignment single --------
# The count run in the ConferenceTeamListStore has two shapes. Stock saves
# write each list count twice; a dynasty realigned through CFB 27's own
# in-game setup writes each count once, then a zero. The arrays below are the
# exact runs observed in DYNASTY-JUL15-04h28m43 (stock) and the two
# DYNASTY-INITIALWYOMING saves (realigned).

def test_match_count_pairs_stock():
    counts = [20, 21, 20, 29, 6, 17, 17, 14, 14, 16, 16, 18, 18, 10, 10, 3,
              13, 13, 10, 10, 8, 8, 16, 16, 14, 14, 13]
    lengths = [17, 14, 16, 18, 10, 13, 10, 8, 16, 14]
    assert confmod._match_count_pairs(counts, lengths) == [
        [5, 6], [7, 8], [9, 10], [11, 12], [13, 14], [16, 17],
        [18, 19], [20, 21], [22, 23], [24, 25]]
    # the single matcher must REJECT the doubled shape (no count is followed
    # by a zero), so the two shapes never cross-match
    assert confmod._match_count_singles(counts, lengths) is None


def test_match_count_singles_realigned():
    counts = [20, 21, 20, 29, 0, 0, 15, 0, 14, 0, 15, 0, 14, 0, 14, 0, 0,
              13, 0, 14, 0, 12, 0, 14, 0, 13, 2]
    lengths = [15, 14, 15, 14, 14, 13, 14, 12, 14, 13]
    assert confmod._match_count_singles(counts, lengths) == [
        [6], [8], [10], [12], [14], [17], [19], [21], [23], [25]]
    # the header values (20, 21, 20, 29) are never mistaken for counts
    assert confmod._match_count_pairs(counts, lengths) is None


def test_match_count_run_dispatches_and_rejects():
    doubled = [4, 4, 8, 8]
    single = [4, 0, 8, 0]
    assert confmod._match_count_run(doubled, [4, 8]) == [[0, 1], [2, 3]]
    assert confmod._match_count_run(single, [4, 8]) == [[0], [2]]
    assert confmod._match_count_run([1, 2, 3], [4, 8]) is None


def test_match_count_run_refuses_transitional_shape():
    # A just-realigned week-1 save (DYNASTY-INITIALWYOMINGSAVE) leaves the
    # count run in a transitional state: the new counts sit as singles
    # interleaved with STALE pre-realignment values and no zero separators.
    # There is no unambiguous per-list slot here, so the matcher must return
    # None (parse falls back to read-only) rather than guess a slot and risk
    # a corrupt write. The game normalizes this to the clean single-with-zero
    # shape once the season advances.
    transitional = [20, 21, 20, 29, 6, 17, 15, 14, 14, 16, 15, 18, 14, 10, 14,
                    3, 13, 13, 10, 14, 8, 12, 16, 14, 14, 13, 13]
    lengths = [15, 14, 15, 14, 14, 13, 14, 12, 14, 13]
    assert confmod._match_count_run(transitional, lengths) is None


def test_locate_count_window_division_counts():
    # the real RL2 DivisionTeamListStore run: header, then 12 per-division
    # counts ending in real zeros for two empty (merged-away) divisions
    counts = [20, 12, 20, 20, 1, 15, 0, 15, 0, 14, 0, 13, 0, 12, 14, 0, 0]
    lengths = [15, 0, 15, 0, 14, 0, 13, 0, 12, 14, 0, 0]
    assert confmod._locate_count_window(counts, lengths) == 5
    # padding after the real window must not shadow it (nearest-grid wins, but
    # the padded window would not match anyway)
    padded = counts + [0, 0]
    assert confmod._locate_count_window(padded, lengths) == 5
    # a header run that coincidentally repeats the lengths never wins over the
    # grid-adjacent one
    dup = lengths + [99] + lengths
    assert confmod._locate_count_window(dup, lengths) == len(lengths) + 1
    assert confmod._locate_count_window([1, 2], [3, 3, 3]) is None


@pytest.fixture()
def payload_single() -> bytes:
    return build_payload(count_shape="single")


def test_parse_realigned_is_writable(payload_single):
    t = confmod.parse(payload_single)
    assert t.writable_membership, t.notes
    acc = t.by_name("ACC")
    assert acc.team_rows == [0, 1, 2, 3]
    # a realigned conference count is a SINGLE run slot (its zero separator is
    # left out of count_offs so the writer never clobbers it)
    assert len(acc.count_offs) == 1
    assert t.by_name("Sun_Belt").team_rows == [36, 37, 38, 39]
    assert t.independents.team_rows == [90, 91]


def test_realigned_membership_move_roundtrips(payload_single):
    buf = bytearray(payload_single)
    t = confmod.parse(payload_single)
    acc, sec = t.by_name("ACC"), t.by_name("SEC")
    confmod.set_memberships(buf, t,
                            {acc.row: [0, 1, 2], sec.row: [32, 33, 34, 35, 3]},
                            {0: [0, 1, 2], 9: [32, 33, 34, 35, 3]})
    t2 = confmod.parse(bytes(buf))
    assert t2.by_name("ACC").team_rows == [0, 1, 2]
    assert t2.by_name("SEC").team_rows == [32, 33, 34, 35, 3]
    # still the single shape, still writable after a write (the zero separators
    # survive, so the count run is not silently converted to the doubled shape)
    assert t2.writable_membership, t2.notes
    assert len(t2.by_name("ACC").count_offs) == 1
