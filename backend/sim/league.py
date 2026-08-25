"""The FBS universe for a simulated season.

Loads the checked-in seed (data/league_seed.json, built by
scripts/build_league_seed.py) and turns it into a per-season universe: every
team gets a season `rating` (its seed base_rating plus deterministic jitter, so
each new season's balance of power differs), its conference, and its prestige.

The user's program (from the customization store) is spliced in: matched to its
seed entry by ESPN id or name so the user keeps the real conference and a real
rating, or inserted at a competitive default if it is a brand-new identity.

A "universe" is `{team_name: {name, espn_id, abbr, conference, division,
rating, prestige, is_user}}`. league.py owns no game logic, only the roster of
teams and how strong each one is.
"""
from __future__ import annotations

import json
from typing import Any

from .. import config
from .engine import make_rng

_SEED_FILE = config.DATA_DIR / "league_seed.json"

RATING_JITTER = 4.0       # season-to-season swing around a team's base rating
RATING_FLOOR, RATING_CEIL = 35, 99
USER_INSERT_RATING = 76   # rating for a brand-new user identity not in the seed


def load_seed() -> list[dict[str, Any]]:
    """The raw FBS seed rows. Empty list if the seed has not been built yet."""
    if not _SEED_FILE.exists():
        return []
    try:
        return json.loads(_SEED_FILE.read_text())
    except (OSError, ValueError):
        return []


def has_seed() -> bool:
    return _SEED_FILE.exists() and bool(load_seed())


def _season_rating(base: float, seed: int, year: int, name: str) -> int:
    jitter = make_rng(seed, year, "rating", name).gauss(0, RATING_JITTER)
    return int(max(RATING_FLOOR, min(RATING_CEIL, round(base + jitter))))


def build_universe(year: int, seed: int, user_team: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Build the season universe. user_team is the customization team() dict."""
    rows = load_seed()
    universe: dict[str, dict[str, Any]] = {}
    for r in rows:
        name = r["name"]
        universe[name] = {
            "name": name,
            "espn_id": r.get("espn_id"),
            "abbr": r.get("abbr"),
            "conference": r.get("conference"),
            "division": r.get("division"),
            "rating": _season_rating(r.get("base_rating", 55), seed, year, name),
            "prestige": r.get("prestige", 5),
            "is_user": False,
        }
    if user_team:
        _splice_user(universe, user_team)
    return universe


def _splice_user(universe: dict[str, dict[str, Any]], user_team: dict[str, Any]) -> None:
    """Mark the user's program in the universe, matched by espn id then name."""
    uid = user_team.get("espn_id")
    uname = user_team.get("name")
    match_key = None
    if uid is not None:
        match_key = next((k for k, v in universe.items() if v.get("espn_id") == uid), None)
    if match_key is None and uname in universe:
        match_key = uname

    if match_key is not None:
        entry = universe.pop(match_key)
        entry.update({
            "name": uname or entry["name"],
            "espn_id": uid if uid is not None else entry["espn_id"],
            "abbr": user_team.get("abbreviation") or entry["abbr"],
            "conference": user_team.get("conference") or entry["conference"],
            "is_user": True,
        })
        universe[entry["name"]] = entry
    else:
        # Brand-new identity not in the FBS seed: insert competitively.
        universe[uname] = {
            "name": uname,
            "espn_id": uid,
            "abbr": user_team.get("abbreviation") or (uname or "USR")[:4].upper(),
            "conference": user_team.get("conference") or "FBS Independents",
            "division": None,
            "rating": USER_INSERT_RATING,
            "prestige": 6,
            "is_user": True,
        }


def user_team_name(universe: dict[str, dict[str, Any]]) -> str | None:
    return next((k for k, v in universe.items() if v.get("is_user")), None)


def by_conference(universe: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for name, v in universe.items():
        out.setdefault(v.get("conference") or "FBS Independents", []).append(name)
    return out
