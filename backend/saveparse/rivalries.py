"""The game's own rivalry table: every named rivalry with its team pair.

Decoded 2026-07-12 from a live bowl-week save (DYNASTY-PLAYOFFTEST) and
verified against known rivalry names (Iron Bowl, Bayou Bucket Classic,
Battle for the Wagon Wheel). The `Rivalry` SPBF store (same BSFT framing as
bowls.py: 290 records x 40 bytes in that save) is followed immediately by
its string pool. Record layout (big-endian u32 words):

    +0   opaque handle (0x80xxxxxx; 0 on some live rows, not significant)
    +4   team ref A (0x317C|teamRow)
    +8   team ref B (0x317C|teamRow)
    +12  string-pool offset: a third, usually empty slot
    +16  string-pool offset: DISPLAY name ("Iron Bowl")
    +20  string-pool offset: internal name ("Alabama_Auburn_Game")
    +24.. series bookkeeping (packed records/last-winner style data; unread)

Unused tail rows are zero-filled, so a row is live only when BOTH team
slots carry a real 0x317C ref and the rows differ. READ-ONLY: the companion
uses the names to label protected rivalries in the schedule editor; nothing
writes here.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from . import bowls as savebowls
from . import tags as savetags

TEAM_REF = savetags.RL1.team  # baseline only; runtime resolves per payload


@dataclass(frozen=True)
class Rivalry:
    a_row: int          # team row (teams.parse_teams order)
    b_row: int
    name: str           # display name, e.g. "Iron Bowl"
    internal: str       # internal key, e.g. "Alabama_Auburn_Game"


def parse(payload: bytes) -> list[Rivalry]:
    """Every live rivalry row in the save's Rivalry store (empty list when
    the store cannot be located, so callers degrade gracefully)."""
    try:
        rec0, stride, count, _ = savebowls._find_store(payload, b"Rivalry")
    except ValueError:
        return []
    team_ref = savetags.for_payload(payload).team
    pool = rec0 + stride * count

    def cstr(off: int) -> str:
        end = payload.find(b"\x00", pool + off, pool + off + 128)
        if end == -1:
            return ""
        return payload[pool + off:end].decode("latin1", errors="replace")

    out: list[Rivalry] = []
    for row in range(count):
        base = rec0 + row * stride
        a_ref, b_ref = struct.unpack_from(">II", payload, base + 4)
        if (a_ref >> 16) != team_ref or (b_ref >> 16) != team_ref:
            continue
        a, b = a_ref & 0xFFFF, b_ref & 0xFFFF
        if a == b:
            continue
        display_off, internal_off = struct.unpack_from(">II", payload, base + 16)
        name = cstr(display_off)
        internal = cstr(internal_off)
        if not name and not internal:
            continue
        out.append(Rivalry(a_row=a, b_row=b,
                           name=name or internal.replace("_", " "),
                           internal=internal))
    return out
