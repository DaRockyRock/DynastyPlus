"""The college profile (PROFILE-COLLEGE): the game's own save-slot metadata.

The CFB 27 saves folder holds one PROFILE-COLLEGE file next to the DYNASTY-*
saves. It is an FBCHUNKS container (best-compression zlib, 78 da) whose payload
carries, among binary profile state, one pipe-delimited metadata row per
dynasty autosave slot. This is what the game's own load screen renders, and it
is the companion's source of truth for dynasty identity and season position:

    DYNASTY-WEEK3-AUTOSAVE|3364487982|Charlotte| @ Tulsa|Chas|Nolte|Week|13|1|19|4|6
    <save file name>      |<dynasty id>|<school>|<next game>|<coach first>|<coach last>
                          |<label>|<week>|<season #>|<team row>|<wins>|<losses>

Field notes (verified against live dynasties):
  * dynasty id   - a numeric id unique per dynasty world, shared by every save
                   of that dynasty and stable across weeks. It appears nowhere
                   inside the dynasty saves themselves, only here.
  * school       - the user-controlled program ("Charlotte", "Nebraska").
  * next game    - display string for the next matchup (" @ Tulsa", " vs Ohio
                   State", empty when none is scheduled).
  * label + week - the game's own week position ("Week 13"). A fresh dynasty
                   starts at Week 1. A later game update merges a phase counter
                   into the label and zeroes the week field ("Bowl Season1|0");
                   read_slots() splits that back into label "Bowl Season", week 1.
  * season #     - 1-based dynasty season; season 1 is 2026.
  * team row     - the user's row in the save's team table.
  * wins/losses  - the user's current overall record.

Rows can be STALE: slots for saves the user has deleted linger with their last
known metadata, so callers must join rows against the files actually on disk.
Manual saves (DYNASTY-WEEK3, DYNASTY-T15) have no row of their own; only
autosave slots are listed, and every dynasty always has one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import container

PROFILE_NAME = "PROFILE-COLLEGE"
FIRST_SEASON_YEAR = 2026  # CFB 27's opening dynasty season

# save-name|dynasty-id|school|next|first|last|label|week|season|teamrow|w|l
#
# The label field carries the game's week phase. Older saves wrote a bare word
# with the week in the next field ("Week|13"); a later game update merges a
# phase counter into the label itself and zeroes the week field ("Bowl Season1|0").
# So the label class allows digits, and read_slots() splits a merged trailing
# number back out (see below). Matching letters/digits/spaces keeps both formats.
_ROW = re.compile(
    rb"([A-Za-z0-9_.-]+)\|(\d+)\|([^|\x00]*)\|([^|\x00]*)\|([^|\x00]*)\|([^|\x00]*)"
    rb"\|([A-Za-z0-9 ]+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)"
)

# Trailing number merged into the label ("Bowl Season1" -> "Bowl Season", 1).
_LABEL_NUM = re.compile(r"^(.*?)(\d+)$")


@dataclass(frozen=True)
class Slot:
    """One dynasty-save slot row from the profile."""

    save_name: str      # file name in the saves folder, e.g. "DYNASTY-WEEK3-AUTOSAVE"
    dynasty_id: str     # the game's numeric dynasty id, e.g. "3364487982"
    school: str         # the user-controlled program, e.g. "Charlotte"
    next_game: str      # display string, e.g. "@ Tulsa" / "vs Ohio State" / ""
    coach_first: str
    coach_last: str
    week_label: str     # the game's label word, e.g. "Week"
    week: int           # current week number (1-based; a fresh dynasty is Week 1)
    season: int         # 1-based dynasty season
    team_row: int       # the user's row in the save's team table
    wins: int
    losses: int

    @property
    def year(self) -> int:
        return FIRST_SEASON_YEAR + self.season - 1

    @property
    def coach_name(self) -> str:
        return f"{self.coach_first} {self.coach_last}".strip()

    @property
    def record(self) -> str:
        return f"{self.wins}-{self.losses}"


def profile_path(saves_dir: str | Path) -> Path:
    return Path(saves_dir) / PROFILE_NAME


def read_slots(saves_dir: str | Path) -> list[Slot]:
    """Every dynasty-save slot row in the profile (stale rows included; join
    against the files on disk). Empty list when the profile is missing or
    unreadable, so callers fall back cleanly."""
    path = profile_path(saves_dir)
    if not path.exists() or not container.is_fbchunks(path):
        return []
    try:
        payload = container.decode(path).payload
    except Exception:  # noqa: BLE001 - torn/corrupt profile: no slots
        return []
    slots: list[Slot] = []
    for m in _ROW.finditer(payload):
        try:
            week_label = m.group(7).decode("latin1").strip()
            week = int(m.group(8))
            # Newer saves merge a phase counter into the label and leave the
            # week field 0 ("Bowl Season1|0"). Split it back into a clean label
            # and week. Older saves ("Week|13") have no trailing digit and a
            # real week, so they pass through untouched.
            if week == 0:
                nm = _LABEL_NUM.match(week_label)
                if nm and nm.group(1).strip():
                    week_label = nm.group(1).strip()
                    week = int(nm.group(2))
            slots.append(Slot(
                save_name=m.group(1).decode("latin1"),
                dynasty_id=m.group(2).decode("latin1"),
                school=m.group(3).decode("latin1").strip(),
                next_game=m.group(4).decode("latin1").strip(),
                coach_first=m.group(5).decode("latin1").strip(),
                coach_last=m.group(6).decode("latin1").strip(),
                week_label=week_label,
                week=week,
                season=int(m.group(9)),
                team_row=int(m.group(10)),
                wins=int(m.group(11)),
                losses=int(m.group(12)),
            ))
        except (ValueError, UnicodeDecodeError):
            continue
    return slots


def slot_for(save_path: str | Path, slots: list[Slot] | None = None) -> Slot | None:
    """The profile row for one save file (by file name), or None. Manual saves
    have no row; only autosave slots are listed."""
    p = Path(save_path)
    rows = read_slots(p.parent) if slots is None else slots
    return next((s for s in rows if s.save_name == p.name), None)
