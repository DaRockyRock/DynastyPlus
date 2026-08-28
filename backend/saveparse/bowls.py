"""Bowl / CFP-round identity structures in the FrTk payload.

Decoded 2026-07-07 (see docs/cfb27-schedule-format.md and the agent research
trail). Two record stores cooperate with the SeasonGameStore:

1. The `BowlGame` store (SPBF, anchor b"\\x00BowlGame\\x00", 45 records x 44
   bytes): what a game record's +16 ref (0x21B2|row) points at. Each row is a
   bowl or CFP-round identity: stadium handle, date-slot ref, two conference
   tie-in refs, and its display/internal names in the trailing string area
   (65-byte slots: internal at +0, display at +32). Rows in this build:
   7..10 = CFP First Round, 11 = National Championship, 12..15 = CFP
   Quarterfinal, 16..17 = CFP Semifinal, 20 = dead, 27 = Generic Bowl, the
   other 32 = the real bowl lineup.

2. The `PlayoffBowlsInfo` store (SPBF, 6 records x 32 bytes): the New Year's
   Six (Cotton, Fiesta, Orange, Peach, Rose, Sugar), each with its stadium
   handle and optional traditional tie-in list. The engine assigns QF/SF
   venues per season by writing these stadium handles into the game records'
   +4 field; matching a game's +4 against these handles names its bowl.

Stadium identity is an opaque 0x80xxxxxx handle (no names in the save); the
stable cross-dynasty stadium INDEX comes from stadiums.py.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from . import tags as savetags

# baselines only (launch-build values); runtime resolves per payload through
# saveparse.tags.for_payload (game patches renumber the type table)
BOWL_REF_TAG = savetags.RL1.bowl
CONF_REF_TAG = savetags.RL1.conf_ref

# CFP-round rows in the BowlGame store (this build; verified by name strings,
# so parse() re-derives them from the names rather than trusting constants).
FIRST_ROUND_ROWS = (7, 8, 9, 10)
NCG_ROW = 11
QUARTERFINAL_ROWS = (12, 13, 14, 15)
SEMIFINAL_ROWS = (16, 17)
GENERIC_ROW = 27


def _cstr(payload: bytes, off: int, cap: int = 64) -> str:
    end = payload.find(b"\x00", off, off + cap)
    if end == -1:
        end = off + cap
    return payload[off:end].decode("latin1", "replace")


def _find_store(payload: bytes, name: bytes) -> tuple[int, int, int, int]:
    """(rec0, stride, count, strings_off) for an SPBF record store by name.

    Header math (verified across seven stores): after BSFT come six u32
    [w0 total][w1][w2][w3 count][w4][w5], a field table of (w4+1) u32, then
    record 0; stride = (w0 - 28 - (w4+1)*4) / count; the string area starts
    at rec0 + count*stride.
    """
    at = payload.find(b"\x00" + name + b"\x00")
    if at == -1:
        raise ValueError(f"{name.decode()} store not found")
    bsft = payload.find(b"BSFT", at, at + 400)
    if bsft == -1:
        raise ValueError(f"{name.decode()}: BSFT header not found")
    w = struct.unpack_from(">6I", payload, bsft + 4)
    count = w[3]
    fields = w[4] + 1
    rec0 = bsft + 4 + 24 + fields * 4
    stride = (w[0] - 28 - fields * 4) // count
    if stride * count != w[0] - 28 - fields * 4:
        raise ValueError(f"{name.decode()}: non-integral stride")
    return rec0, stride, count, rec0 + count * stride


# The display-name field is a fixed 32-byte slot in the 65-byte-per-row string
# area (internal name at slot+0, display at slot+32), so a name can be rewritten
# in place up to 31 chars + NUL without disturbing the next row.
NAME_CAP = 31


@dataclass(frozen=True)
class Bowl:
    row: int                  # the n in 0x21B2|n
    name: str                 # display name ("Alamo Bowl")
    internal: str             # internal key ("Alamo_Bowl")
    stadium_handle: int       # 0x80xxxxxx venue uid; 0 = no fixed venue
    tie_in_conf_rows: tuple[int, ...]
    record_off: int           # absolute offset (writer seam)
    disp_abs: int = 0         # absolute offset of the display-name string

    @property
    def is_cfp(self) -> bool:
        n = self.internal.lower()
        return "playoff" in n or "championship" in n or n.startswith("cfp") \
            or "first_round" in n or "quarterfinal" in n or "semifinal" in n


@dataclass(frozen=True)
class PlayoffBowl:
    row: int
    name: str
    internal: str
    stadium_handle: int
    record_off: int


@dataclass(frozen=True)
class BowlTable:
    bowls: list[Bowl]                 # index == BowlGame row
    playoff_bowls: list[PlayoffBowl]  # the New Year's Six

    def by_row(self, row: int) -> Bowl | None:
        return self.bowls[row] if 0 <= row < len(self.bowls) else None

    def name_for_venue(self, stadium_handle: int) -> str | None:
        """The NY6 bowl (or bowl-store) name hosting a venue handle."""
        for pb in self.playoff_bowls:
            if pb.stadium_handle == stadium_handle:
                return pb.name
        for b in self.bowls:
            if b.stadium_handle and b.stadium_handle == stadium_handle:
                return b.name
        return None


def parse(payload: bytes) -> BowlTable:
    rec0, stride, count, strings = _find_store(payload, b"BowlGame")
    conf_ref = savetags.for_payload(payload).conf_ref
    bowls: list[Bowl] = []
    for row in range(count):
        base = rec0 + row * stride
        stadium = struct.unpack_from(">I", payload, base)[0]
        confs = []
        for off in (8, 12):
            v = struct.unpack_from(">I", payload, base + off)[0]
            if (v >> 16) == conf_ref:
                confs.append(v & 0xFFFF)
        disp_off = struct.unpack_from(">I", payload, base + 20)[0]
        int_off = struct.unpack_from(">I", payload, base + 24)[0]
        bowls.append(Bowl(
            row=row,
            name=_cstr(payload, strings + disp_off),
            internal=_cstr(payload, strings + int_off),
            stadium_handle=stadium if stadium >> 24 == 0x80 else 0,
            tie_in_conf_rows=tuple(confs),
            record_off=base,
            disp_abs=strings + disp_off,
        ))

    prec0, pstride, pcount, pstrings = _find_store(payload, b"PlayoffBowlsInfo")
    playoff: list[PlayoffBowl] = []
    for row in range(pcount):
        base = prec0 + row * pstride
        stadium = struct.unpack_from(">I", payload, base)[0]
        disp_off = struct.unpack_from(">I", payload, base + 12)[0]
        int_off = struct.unpack_from(">I", payload, base + 16)[0]
        playoff.append(PlayoffBowl(
            row=row,
            name=_cstr(payload, pstrings + disp_off),
            internal=_cstr(payload, pstrings + int_off),
            stadium_handle=stadium if stadium >> 24 == 0x80 else 0,
            record_off=base,
        ))
    return BowlTable(bowls=bowls, playoff_bowls=playoff)


def set_display_name(payload: bytearray, bowl: Bowl, name: str) -> bool:
    """Rewrite a bowl's DISPLAY name in place (its 32-byte slot), e.g. to
    relabel a bowl record repurposed for a playoff round as 'CFP First Round'.
    Only the display string the game shows is touched; the internal key is
    left alone so logo/asset lookups keep working. Returns True if it changed.

    The name is truncated to fit the slot. Idempotent: a no-op when the name
    already matches (so stock CFP rows are never needlessly rewritten)."""
    if not bowl.disp_abs or bowl.name == name:
        return False
    raw = name.encode("latin1", "replace")[:NAME_CAP]
    payload[bowl.disp_abs:bowl.disp_abs + len(raw) + 1] = raw + b"\x00"
    return True


def set_stadium_handle(payload: bytearray, bowl: Bowl,
                       stadium_handle: int | None) -> bool:
    """Set the venue paired with a BowlGame presentation identity.

    Native home-site CFP presentation uses zero here and resolves the physical
    venue from HomeTeam.Stadium. Named bowls keep their fixed real-world handle.
    The custom playoff runtime uses this writer both to enter that native CFP
    shape and to restore presentation rows after a completed game.
    """
    value = stadium_handle or 0
    if value and value >> 24 != 0x80:
        raise ValueError(f"bowl {bowl.row}: {value:#x} is not a stadium handle")
    current = struct.unpack_from(">I", payload, bowl.record_off)[0]
    if current == value:
        return False
    struct.pack_into(">I", payload, bowl.record_off, value)
    return True
