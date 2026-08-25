"""Real team metadata (logos, colors, abbreviations) from the ESPN public API.

ESPN exposes a public, unauthenticated college football teams endpoint that
returns each team's id, abbreviation, display name, primary/alternate colors,
and logo URLs. We fetch it once and cache to disk. Logos resolve to:

    https://a.espncdn.com/i/teamlogos/ncaa/500/<espn_id>.png

The frontend uses those PNGs as the real team icons and falls back to a
color-accurate helmet SVG (rendered client-side) when an image is missing.
"""
from __future__ import annotations

import json
import time
from typing import Any

import requests

from . import config

ESPN_TEAMS_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/football/"
    "college-football/teams?limit=400"
)
LOGO_URL_TEMPLATE = "https://a.espncdn.com/i/teamlogos/ncaa/500/{id}.png"
CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # one week

# Curated seed used by the mock generator and as an offline fallback so the
# app never hard-depends on the network. Colors are the schools' primaries.
SEED_TEAMS: dict[str, dict[str, Any]] = {
    "Nebraska Cornhuskers": {"espn_id": 158, "abbr": "NEB", "color": "e41c38", "alt": "f5f5f5"},
    "Ohio State Buckeyes": {"espn_id": 194, "abbr": "OSU", "color": "bb0000", "alt": "666666"},
    "Michigan Wolverines": {"espn_id": 130, "abbr": "MICH", "color": "00274c", "alt": "ffcb05"},
    "Penn State Nittany Lions": {"espn_id": 213, "abbr": "PSU", "color": "041e42", "alt": "ffffff"},
    "Iowa Hawkeyes": {"espn_id": 2294, "abbr": "IOWA", "color": "000000", "alt": "ffcd00"},
    "Wisconsin Badgers": {"espn_id": 275, "abbr": "WIS", "color": "c5050c", "alt": "ffffff"},
    "Minnesota Golden Gophers": {"espn_id": 135, "abbr": "MINN", "color": "7a0019", "alt": "ffcc33"},
    "Illinois Fighting Illini": {"espn_id": 356, "abbr": "ILL", "color": "e84a27", "alt": "13294b"},
    "Indiana Hoosiers": {"espn_id": 84, "abbr": "IND", "color": "990000", "alt": "ffffff"},
    "Maryland Terrapins": {"espn_id": 120, "abbr": "MD", "color": "e03a3e", "alt": "ffd520"},
    "Michigan State Spartans": {"espn_id": 127, "abbr": "MSU", "color": "18453b", "alt": "ffffff"},
    "Rutgers Scarlet Knights": {"espn_id": 164, "abbr": "RUT", "color": "cc0033", "alt": "5f6a72"},
    "Purdue Boilermakers": {"espn_id": 2509, "abbr": "PUR", "color": "ceb888", "alt": "000000"},
    "Northwestern Wildcats": {"espn_id": 77, "abbr": "NW", "color": "4e2a84", "alt": "ffffff"},
    "USC Trojans": {"espn_id": 30, "abbr": "USC", "color": "990000", "alt": "ffc72c"},
    "UCLA Bruins": {"espn_id": 26, "abbr": "UCLA", "color": "2d68c4", "alt": "f2a900"},
    "Oregon Ducks": {"espn_id": 2483, "abbr": "ORE", "color": "154733", "alt": "fee123"},
    "Washington Huskies": {"espn_id": 264, "abbr": "WASH", "color": "4b2e83", "alt": "b7a57a"},
    "Colorado Buffaloes": {"espn_id": 38, "abbr": "COLO", "color": "cfb87c", "alt": "000000"},
    "Notre Dame Fighting Irish": {"espn_id": 87, "abbr": "ND", "color": "0c2340", "alt": "c99700"},
    "Texas Longhorns": {"espn_id": 251, "abbr": "TEX", "color": "bf5700", "alt": "ffffff"},
    "Georgia Bulldogs": {"espn_id": 61, "abbr": "UGA", "color": "ba0c2f", "alt": "000000"},
    "Alabama Crimson Tide": {"espn_id": 333, "abbr": "ALA", "color": "9e1b32", "alt": "ffffff"},
    "Oklahoma Sooners": {"espn_id": 201, "abbr": "OU", "color": "841617", "alt": "ffffff"},
    "Tennessee Volunteers": {"espn_id": 2633, "abbr": "TENN", "color": "ff8200", "alt": "ffffff"},
    "LSU Tigers": {"espn_id": 99, "abbr": "LSU", "color": "461d7c", "alt": "fdd023"},
    "Florida Gators": {"espn_id": 57, "abbr": "FLA", "color": "0021a5", "alt": "fa4616"},
    "Florida State Seminoles": {"espn_id": 52, "abbr": "FSU", "color": "782f40", "alt": "ceb888"},
    "Clemson Tigers": {"espn_id": 228, "abbr": "CLEM", "color": "f56600", "alt": "522d80"},
    "Miami Hurricanes": {"espn_id": 2390, "abbr": "MIA", "color": "f47321", "alt": "005030"},
}

_runtime_cache: dict[str, dict[str, Any]] | None = None


def _logo_url(espn_id: Any) -> str | None:
    if espn_id in (None, ""):
        return None
    return LOGO_URL_TEMPLATE.format(id=espn_id)


def _seed_index() -> dict[str, dict[str, Any]]:
    """Seed teams normalized into the standard record shape."""
    out: dict[str, dict[str, Any]] = {}
    for name, info in SEED_TEAMS.items():
        out[name] = {
            "name": name,
            "abbreviation": info["abbr"],
            "espn_id": info["espn_id"],
            "color": info["color"],
            "alternate_color": info["alt"],
            "logo": _logo_url(info["espn_id"]),
        }
    return out


def _load_disk_cache() -> dict[str, dict[str, Any]] | None:
    path = config.TEAMS_CACHE_FILE
    if not path.exists():
        return None
    try:
        if time.time() - path.stat().st_mtime > CACHE_TTL_SECONDS:
            return None
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _save_disk_cache(data: dict[str, dict[str, Any]]) -> None:
    try:
        with config.TEAMS_CACHE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except OSError:
        pass


def _fetch_from_espn() -> dict[str, dict[str, Any]] | None:
    try:
        resp = requests.get(ESPN_TEAMS_URL, timeout=12)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError):
        return None

    out: dict[str, dict[str, Any]] = {}
    try:
        groups = payload["sports"][0]["leagues"][0]["teams"]
    except (KeyError, IndexError, TypeError):
        return None

    for entry in groups:
        team = entry.get("team", {})
        name = team.get("displayName")
        if not name:
            continue
        logos = team.get("logos") or []
        logo = logos[0].get("href") if logos else _logo_url(team.get("id"))
        out[name] = {
            "name": name,
            "abbreviation": (team.get("abbreviation") or "").upper(),
            "espn_id": _safe_int(team.get("id")),
            "color": team.get("color") or "555555",
            "alternate_color": team.get("alternateColor") or "ffffff",
            "logo": logo or _logo_url(team.get("id")),
            # School + nickname split, used when swapping the user's program
            # identity. ESPN gives these cleanly (location = school, name =
            # nickname); a name-split fallback covers the seed/offline paths.
            "location": team.get("location"),
            "nickname": team.get("name"),
        }
    return out or None


def _safe_int(value: Any) -> Any:
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def get_all_teams(force_refresh: bool = False) -> dict[str, dict[str, Any]]:
    """Return {display_name: record}. ESPN-backed, cached, seed fallback."""
    global _runtime_cache
    if _runtime_cache is not None and not force_refresh:
        return _runtime_cache

    data: dict[str, dict[str, Any]] | None = None
    if not force_refresh:
        data = _load_disk_cache()
    if data is None:
        data = _fetch_from_espn()
        if data is not None:
            _save_disk_cache(data)
    if data is None:
        data = _seed_index()

    # Always make sure the seed teams exist (covers partial ESPN payloads and
    # keeps abbreviations stable for the schools used in mock data).
    seed = _seed_index()
    for name, rec in seed.items():
        data.setdefault(name, rec)

    _runtime_cache = data
    return data


def get_team(name: str) -> dict[str, Any]:
    """Best-effort lookup with a graceful generic fallback."""
    teams = get_all_teams()
    if name in teams:
        return teams[name]
    # loose match on the leading school token
    lowered = name.lower()
    for key, rec in teams.items():
        if key.lower() == lowered or key.lower().startswith(lowered):
            return rec
    return {
        "name": name,
        "abbreviation": (name[:3] or "FCS").upper(),
        "espn_id": None,
        "color": "555555",
        "alternate_color": "ffffff",
        "logo": None,
    }
