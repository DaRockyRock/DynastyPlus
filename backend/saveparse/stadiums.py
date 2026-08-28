"""Stadium identity + neutral-venue pools in the FrTk payload.

Decoded 2026-07-07. The save has NO stadium names/cities/capacities: stadiums
are opaque 0x80xxxxxx uid handles (per dynasty), and identity is positional:

- The 183-element `Stadium[]` ASTO (~25.85MB, the largest Stadium[] array)
  lists every stadium's handle; its ORDER is the game's static stadium DB and
  is identical across dynasties, so the array index (0..182) is a stable
  cross-dynasty stadium id. Handles must be resolved through this array per
  save.
- Team -> home stadium: the `TeamStore` record store (143 x 788 bytes, rows
  in teams.parse_teams order) carries the home stadium handle at +152.
- A game's venue: SeasonGameStore record +4 (0 = home team's stadium); see
  schedule.py. Writing a different handle there moves the game.
- Neutral pools: three smaller Stadium[] handle ASTOs are the game's own
  venue sets: ~20 elements (every venue neutral scheduling uses, incl. CCG
  sites), ~42 (all bowl venues + neutrals), ~10 (the marquee/title pool).

Display names are derived, not parsed: bowl-venue names come from the bowls
store joined with the companion's bowl catalog, team homes from the school
they belong to. `annotate` returns the full picker list.
"""
from __future__ import annotations

import os
import re
import struct
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from . import bowls as savebowls
from . import teams as saveteams

_TEAMSTORE_ANCHOR = b"\x00\x09TeamStore\x00"
_TEAM_RECORD = 788
_TEAM_STADIUM_OFF = 152

# The schema-backed Stadium store has 183 fixed 128-byte records. Its second
# table is also fixed size: 210 string bytes per record. The field recipe is
# the sixth string slot, 148 bytes into that record's string block, with a
# 24-byte capacity. Stock stadium rows leave the pointer at zero because the
# game supplies their database defaults. The value round-trips through the
# schema, but CFB's playoff renderer ignores it for a CFP identity at a custom
# neutral venue. It remains decoded for diagnostics and legacy-save cleanup.
_STADIUM_RECORD = 128
_STADIUM_STRINGS_PER_RECORD = 210
_FIELD_RECIPE_PTR_OFF = 32
_FIELD_RECIPE_SLOT_OFF = 148
_FIELD_RECIPE_CAP = 24


def _stadium_store(payload: bytes) -> tuple[int, int, int]:
    """Return (record zero, count, second-table strings) for Stadium."""
    at = payload.find(b"\x00Stadium\x00")
    if at == -1:
        raise ValueError("Stadium store not found")
    bsft = payload.find(b"BSFT", at, at + 400)
    if bsft == -1:
        raise ValueError("Stadium BSFT header not found")
    words = struct.unpack_from(">6I", payload, bsft + 4)
    count = words[3]
    fields = words[4] + 1
    rec0 = bsft + 4 + 24 + fields * 4
    stride = (words[0] - 28 - fields * 4) // count
    if stride != _STADIUM_RECORD:
        raise ValueError(f"unexpected Stadium record size {stride}")
    return rec0, count, rec0 + count * stride


def field_recipe_name(payload: bytes, stadium_index: int) -> str:
    """The save-level field recipe override for one stable stadium index."""
    rec0, count, strings = _stadium_store(payload)
    if not 0 <= stadium_index < count:
        raise IndexError(f"stadium index {stadium_index} out of range")
    base = rec0 + stadium_index * _STADIUM_RECORD
    offset = struct.unpack_from(">I", payload, base + _FIELD_RECIPE_PTR_OFF)[0]
    if not offset:
        return ""
    end_limit = count * _STADIUM_STRINGS_PER_RECORD
    if offset >= end_limit:
        raise ValueError(f"stadium {stadium_index}: bad field recipe offset {offset}")
    start = strings + offset
    end = payload.find(b"\x00", start, start + _FIELD_RECIPE_CAP)
    if end == -1:
        end = start + _FIELD_RECIPE_CAP
    return payload[start:end].decode("latin1", "replace")


def set_field_recipe(payload: bytearray, stadium_index: int, recipe: str) -> bool:
    """Write the Stadium field-recipe schema value.

    The SeasonGame Stadium handle remains unchanged, so the stadium structure,
    crowd, scoreboards, and location remain unchanged. CFB 27 does not honor
    this value for a CFP identity at a custom neutral venue, so playoff code
    must use the native Team.Stadium relationship instead. An empty recipe
    restores the stock database default. Returns True only when storage changed.
    """
    rec0, count, strings = _stadium_store(bytes(payload))
    if not 0 <= stadium_index < count:
        raise IndexError(f"stadium index {stadium_index} out of range")
    raw = recipe.encode("ascii", "strict")
    if len(raw) >= _FIELD_RECIPE_CAP:
        raise ValueError(f"field recipe {recipe!r} exceeds 23 characters")
    base = rec0 + stadium_index * _STADIUM_RECORD
    current = field_recipe_name(bytes(payload), stadium_index)
    if current == recipe:
        return False
    slot_offset = (stadium_index * _STADIUM_STRINGS_PER_RECORD
                   + _FIELD_RECIPE_SLOT_OFF)
    slot = strings + slot_offset
    payload[slot:slot + _FIELD_RECIPE_CAP] = b"\x00" * _FIELD_RECIPE_CAP
    if raw:
        payload[slot:slot + len(raw)] = raw
        struct.pack_into(">I", payload, base + _FIELD_RECIPE_PTR_OFF, slot_offset)
    else:
        struct.pack_into(">I", payload, base + _FIELD_RECIPE_PTR_OFF, 0)
    return True


def _recipe_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


@lru_cache(maxsize=1)
def _field_recipe_catalog() -> dict[str, str]:
    """School key to field-recipe asset name, read from the local game.

    Only bundle names are read. No game asset is copied or changed. Returning
    an empty catalog is safe: the caller leaves the stadium's default alone.
    """
    try:
        from ..assets.frostbite import superbundle, toc
        from ..assets.frostbite.gamefs import DEFAULT_GAME_ROOT, GameFS

        game_root = Path(os.environ.get("CFBMOD_GAME_PATH") or DEFAULT_GAME_ROOT)
        fs = GameFS(game_root)
        payload = toc.read_payload(fs.toc_path("Win32/stadiumswappables_sb"))
        bundles = superbundle.parse(payload).bundles
    except Exception:  # noqa: BLE001, an unavailable install is a safe no-op
        return {}
    pattern = re.compile(
        r"/recipes/stadiums/([^/]+)/([^/]+)_recipe_stadium_swappables_brt$")
    out: dict[str, str] = {}
    for bundle in bundles:
        match = pattern.search(bundle.name.lower())
        if not match:
            continue
        folder, asset = match.groups()
        recipe = f"{asset}_recipe"
        if len(recipe) < _FIELD_RECIPE_CAP:
            out[_recipe_key(folder)] = recipe
    return out


def field_recipe_for_team(team: saveteams.Team) -> str | None:
    """Resolve a real team's field recipe from the installed game's catalog."""
    catalog = _field_recipe_catalog()
    for value in (team.school, team.slug, team.abbreviation):
        recipe = catalog.get(_recipe_key(value or ""))
        if recipe:
            return recipe
    return None


def _asto_arrays_of_handles(payload: bytes) -> list[tuple[int, list[int]]]:
    """Every `Stadium[]` ASTO as (offset, [handles])."""
    out = []
    i = 0
    while True:
        i = payload.find(b"Stadium[]\x00", i + 1)
        if i == -1:
            break
        # skip non-Stadium arrays that merely end with the same suffix
        if payload[i - 1:i] not in (b"\x00", b""):
            prev = payload[i - 16:i]
            if b"Neutral" in prev or b"HighSchool" in prev or b"TeamBuilder" in prev:
                continue
        cmpc = payload.find(b"CMPC", i, i + 400)
        if cmpc == -1:
            continue
        used = struct.unpack_from(">I", payload, cmpc + 32)[0]
        if not 0 < used <= 400:
            continue
        vals = list(struct.unpack_from(f">{used}I", payload, cmpc + 36))
        if vals and all(v >> 24 == 0x80 for v in vals):
            out.append((i, vals))
    return out


def stadium_table(payload: bytes) -> list[int]:
    """Index -> handle for the full stadium DB (the largest Stadium[] array)."""
    arrays = _asto_arrays_of_handles(payload)
    if not arrays:
        raise ValueError("Stadium[] handle arrays not found")
    return max(arrays, key=lambda a: len(a[1]))[1]


def neutral_pools(payload: bytes) -> dict[str, list[int]]:
    """The game's own neutral-venue handle sets, by rough size class."""
    arrays = sorted((a[1] for a in _asto_arrays_of_handles(payload)), key=len)
    pools: dict[str, list[int]] = {}
    for vals in arrays:
        if len(vals) >= 100:
            continue  # the full table
        if len(vals) >= 30:
            pools["bowl_and_neutral"] = vals
        elif len(vals) >= 15:
            pools["neutral_scheduling"] = vals
        elif len(vals) >= 8:
            pools["marquee"] = vals
    return pools


def _team_store(payload: bytes) -> tuple[int, int]:
    """Return (record zero, count) for the main TeamStore."""
    at = payload.find(_TEAMSTORE_ANCHOR)
    if at == -1:
        raise ValueError("TeamStore not found")
    bsft = payload.find(b"BSFT", at, at + 400)
    if bsft == -1:
        raise ValueError("TeamStore BSFT header not found")
    w = struct.unpack_from(">6I", payload, bsft + 4)
    count = w[3]
    fields = w[4] + 1
    rec0 = bsft + 4 + 24 + fields * 4
    return rec0, count


def team_home_handle(payload: bytes, team_row: int) -> int:
    """Read one team's Stadium reference, including a zero placeholder."""
    rec0, count = _team_store(payload)
    if not 0 <= team_row < count:
        raise IndexError(f"team row {team_row} out of range")
    return struct.unpack_from(
        ">I", payload, rec0 + team_row * _TEAM_RECORD + _TEAM_STADIUM_OFF)[0]


def set_team_home_handle(payload: bytearray, team_row: int,
                         stadium_handle: int | None) -> bool:
    """Temporarily point a team at another stadium.

    SeasonGame uses a zero Stadium reference for a native campus game, then
    resolves the physical venue through this TeamStore reference. The custom
    playoff runtime uses that native relationship for playable plain-neutral
    games so CFB loads the requested stadium through its working home-playoff
    field path. The caller owns restoring the original handle after the game.
    """
    value = stadium_handle or 0
    if value and value >> 24 != 0x80:
        raise ValueError(f"{value:#x} is not a stadium handle")
    current = team_home_handle(bytes(payload), team_row)
    if current == value:
        return False
    rec0, _ = _team_store(bytes(payload))
    struct.pack_into(">I", payload,
                     rec0 + team_row * _TEAM_RECORD + _TEAM_STADIUM_OFF,
                     value)
    return True


def team_home_handles(payload: bytes) -> dict[int, int]:
    """team row -> home stadium handle (0 for the FCS placeholder teams)."""
    rec0, count = _team_store(payload)
    out = {}
    for row in range(count):
        h = struct.unpack_from(">I", payload, rec0 + row * _TEAM_RECORD + _TEAM_STADIUM_OFF)[0]
        if h >> 24 == 0x80:
            out[row] = h
    return out


@dataclass(frozen=True)
class Stadium:
    index: int          # stable cross-dynasty stadium id
    handle: int         # this save's uid
    name: str           # best-derived display name
    city: str | None
    home_of: str | None  # school name when it is a campus stadium
    pools: tuple[str, ...]  # which game venue pools list it


# Venues identified by their stable stadium index but not derivable from a
# team home or a bowl tie-in (verified against the games played there: the
# Big Ten CCG at 102, the MAC CCG + EMU-CMU series at 58, Red River at 38).
INDEX_NAMES: dict[int, tuple[str, str]] = {
    38: ("Cotton Bowl (Fair Park)", "Dallas, TX"),
    58: ("Ford Field", "Detroit, MI"),
    102: ("Lucas Oil Stadium", "Indianapolis, IN"),
}


def annotate(payload: bytes, *, bowl_catalog: list[dict[str, Any]] | None = None,
             school_stadium_names: dict[str, str] | None = None) -> list[Stadium]:
    """The full stadium list with derived names, for the neutral-site picker.

    bowl_catalog: the companion's BOWLS list (backend/playoff.py) providing
    real venue/city strings per bowl name; school_stadium_names maps a school
    name to its real home stadium name (backend/school_sites.STADIUM_NAMES).
    Bowl-venue names win (they cover the marquee neutral sites), then school
    homes, then a plain fallback.
    """
    table = stadium_table(payload)
    handle_pos = {h: i for i, h in enumerate(table)}
    roster = saveteams.parse_teams(payload)
    homes = team_home_handles(payload)
    btable = savebowls.parse(payload)
    pools = neutral_pools(payload)

    by_bowl_venue: dict[int, str] = {}
    for b in btable.bowls:
        if b.stadium_handle and b.stadium_handle not in by_bowl_venue and not b.is_cfp:
            by_bowl_venue[b.stadium_handle] = b.name
    for pb in btable.playoff_bowls:
        by_bowl_venue.setdefault(pb.stadium_handle, pb.name)

    venue_meta: dict[str, tuple[str, str]] = {}
    for row in bowl_catalog or []:
        venue_meta[row["name"]] = (row.get("venue") or row["name"], row.get("city") or "")

    home_school = {h: roster[r].school for r, h in homes.items() if r < len(roster)}

    out: list[Stadium] = []
    for idx, handle in enumerate(table):
        school = home_school.get(handle)
        bowl_name = by_bowl_venue.get(handle)
        name, city = None, None
        if bowl_name and bowl_name in venue_meta:
            name, city = venue_meta[bowl_name]
        elif bowl_name:
            name = f"{bowl_name} stadium"
        if school and not name:
            name = (school_stadium_names or {}).get(school) or f"{school} home stadium"
        if not name and idx in INDEX_NAMES:
            name, city = INDEX_NAMES[idx]
        if not name:
            name = f"Stadium {idx}"
        in_pools = tuple(k for k, vals in pools.items() if handle in vals)
        out.append(Stadium(index=idx, handle=handle, name=name, city=city,
                           home_of=school, pools=in_pools))
    return out
