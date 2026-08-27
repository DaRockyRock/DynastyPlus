"""Per-team local media (real outlets + beat writers) for every FBS school.

A researched dataset, keyed by full team name, of the real local and regional
media that cover each program: the metro daily, the team's 247Sports / On3 /
Rivals site, the flagship radio home, the fan sites, and the named beat writers
behind the bylines. Stored in data/local_media.json.

The Simulator owns which team the user is (it writes team identity into the
save). The Dynasty+ companion seeds its local media (the media_orgs_local
outlets and the local-scope reporters) for whatever program the save names, so
only the user's school's real local writers cover the program week to week. The
national media is the same for everyone and is untouched.

This module just reads + reshapes the dataset; the actual swap into the media
store lives in customization.apply_local_media, fired by pipeline.scan when the
save names a new program. Team names are normalized so a save resolves even with
minor punctuation/accent differences.
"""
from __future__ import annotations

import json
from typing import Any

from . import config, personality
from .customization_base import clean

_FILE = config.DATA_DIR / "local_media.json"

# A dataset beat label -> a valid reporter beat (customization_base.BEATS).
_BEAT_MAP = {
    "program": "program", "beat": "program", "columnist": "program",
    "radio": "program", "tv": "program", "feature": "feature",
    "recruiting": "recruiting", "portal": "portal", "national": "program",
}

_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    data: dict[str, Any] = {}
    if _FILE.exists():
        try:
            raw = json.loads(_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except (OSError, ValueError):
            data = {}
    _cache = data
    return data


def reload() -> None:
    """Drop the in-memory cache (after the dataset file is regenerated)."""
    global _cache
    _cache = None


def _norm(name: str) -> str:
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def _index() -> dict[str, dict[str, Any]]:
    return {_norm(k): v for k, v in _load().items()}


def for_team(name: str) -> dict[str, list]:
    """{'orgs': [...], 'writers': [...]} for a team, empty lists if unknown."""
    entry = _load().get(name)
    if entry is None:
        entry = _index().get(_norm(name))
    if not isinstance(entry, dict):
        return {"orgs": [], "writers": []}
    return {"orgs": entry.get("orgs") or [], "writers": entry.get("writers") or []}


def has_team(name: str) -> bool:
    return name in _load() or _norm(name) in _index()


def orgs_for(name: str) -> list[dict[str, Any]]:
    """media_orgs_local records (name, voice, reliability) for a team."""
    out = []
    for o in for_team(name)["orgs"]:
        if not o.get("name"):
            continue
        out.append({
            "name": o.get("name", ""),
            "voice": o.get("voice", ""),
            "reliability": int(o.get("reliability") or 78),
        })
    return clean(out)


def reporters_for(name: str) -> list[dict[str, Any]]:
    """Local-scope reporter records for a team, shaped like customization's
    `reporters` items. Personality sliders are seeded deterministically from the
    writer's name (so they read the same every time, distinct from one another);
    the researched factual bio is preserved."""
    out = []
    for w in for_team(name)["writers"]:
        wname = w.get("name") or ""
        if not wname:
            continue
        beat = _BEAT_MAP.get((w.get("beat") or "program").lower(), "program")
        out.append({
            "name": wname,
            "outlet": w.get("outlet", ""),
            "scope": "local",
            "beat": beat,
            "reliability": int(w.get("reliability") or 80),
            "image": "",
            "bio": w.get("bio", ""),
            "traits": personality.random_traits(wname),
        })
    return clean(out)
