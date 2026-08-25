"""Conference metadata + logos.

Conference (group) logos come from the same ESPN CDN used for team logos:
    https://a.espncdn.com/i/teamlogos/ncaa_conf/500/<espn_group_id>.png
Exposed via /api/conferences so the frontend can render affiliation icons.
"""
from __future__ import annotations

from typing import Any

LOGO_TEMPLATE = "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/{id}.png"

# ESPN group ids (verified against the CDN).
CONFERENCES: dict[str, dict[str, Any]] = {
    "SEC": {"id": 8, "abbr": "SEC"},
    "Big Ten": {"id": 5, "abbr": "B1G"},
    "Big 12": {"id": 4, "abbr": "B12"},
    "ACC": {"id": 1, "abbr": "ACC"},
    "Pac-12": {"id": 9, "abbr": "PAC"},
    "Mountain West": {"id": 17, "abbr": "MW"},
    "American": {"id": 151, "abbr": "AAC"},
    "Conference USA": {"id": 12, "abbr": "CUSA"},
    "MAC": {"id": 15, "abbr": "MAC"},
    "Sun Belt": {"id": 37, "abbr": "SBC"},
    "FBS Independents": {"id": 18, "abbr": "IND"},
}

ALIASES = {
    "AAC": "American", "American Athletic": "American",
    "C-USA": "Conference USA", "CUSA": "Conference USA",
    "Mid-American": "MAC",
    "Independent": "FBS Independents", "Independents": "FBS Independents",
    "Pac 12": "Pac-12", "Big-12": "Big 12", "B1G": "Big Ten",
}


def logo_url(group_id: Any) -> str | None:
    return LOGO_TEMPLATE.format(id=group_id) if group_id not in (None, "") else None


def resolve(name_or_id: Any) -> dict[str, Any] | None:
    if isinstance(name_or_id, int):
        for key, rec in CONFERENCES.items():
            if rec["id"] == name_or_id:
                return {"name": key, **rec, "logo": logo_url(rec["id"])}
        return None
    if not name_or_id:
        return None
    key = ALIASES.get(name_or_id, name_or_id)
    rec = CONFERENCES.get(key)
    if not rec:
        return None
    return {"name": key, **rec, "logo": logo_url(rec["id"])}


def conf_id(name_or_id: Any) -> int | None:
    rec = resolve(name_or_id)
    return rec["id"] if rec else None


def all_conferences() -> dict[str, dict[str, Any]]:
    return {k: {"name": k, **v, "logo": logo_url(v["id"])} for k, v in CONFERENCES.items()}
