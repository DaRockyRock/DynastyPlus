"""Registry of dynasties the companion has scanned in.

The companion does not auto-watch or auto-generate. The user creates a dynasty in
the Simulator (or, later, plays CFB 27), then clicks Scan: the companion reads the
save and registers/updates a dynasty here. The landing screen lists them so the
user picks which to continue. One entry per program (keyed by school slug); each
tracks the latest scanned year/week, record, and the save's content hash.

One JSON document at data/dynasties.json:
    {"dynasties": [ {entry}, ... ], "current": "<id>"}
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import threading
from typing import Any

from . import config

_FILE = config.DATA_DIR / "dynasties.json"
_lock = threading.Lock()


def _slug(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-") or "dynasty"


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _load() -> dict[str, Any]:
    if _FILE.exists():
        try:
            d = json.loads(_FILE.read_text())
            if isinstance(d, dict):
                d.setdefault("dynasties", [])
                d.setdefault("current", None)
                return d
        except (OSError, ValueError):
            pass
    return {"dynasties": [], "current": None}


def _save(d: dict[str, Any]) -> None:
    try:
        _FILE.write_text(json.dumps(d, indent=2))
    except OSError:
        pass


def list_all() -> dict[str, Any]:
    return _load()


def current() -> dict[str, Any] | None:
    d = _load()
    return next((x for x in d["dynasties"] if x["id"] == d.get("current")), None)


def current_id() -> str | None:
    """The id of the active dynasty (what per-dynasty stores scope themselves to),
    or None before anything has been scanned."""
    return _load().get("current")


def get(dynasty_id: str) -> dict[str, Any] | None:
    return next((x for x in _load()["dynasties"] if x["id"] == dynasty_id), None)


def upsert_from_save(save: dict[str, Any]) -> dict[str, Any]:
    """Register or update a dynasty from a dynasty-save dict; mark it current."""
    team = save.get("team", {}) or {}
    season = save.get("season", {}) or {}
    # Key by the save's unique dynasty id (the game, or the Simulator, stamps it
    # into meta). Two dynasties of the same school stay distinct, and every
    # per-dynasty store namespaces under this id. Fall back to the school slug for
    # legacy saves that predate the field.
    did = (save.get("meta") or {}).get("dynasty_id") or _slug(team.get("school") or team.get("name"))
    entry = {
        "id": did,
        "team_name": team.get("name"),
        "school": team.get("school"),
        "abbreviation": team.get("abbreviation"),
        "espn_id": team.get("espn_id"),
        "color": team.get("color"),
        "alt_color": team.get("alt_color"),
        "logo": team.get("logo") or "",
        "conference": team.get("conference"),
        "year": int(season.get("year", 0) or 0),
        "week": int(season.get("week", 0) or 0),
        "week_label": season.get("week_label"),
        "record": (team.get("record") or {}).get("overall"),
        "head_coach": (team.get("head_coach") or {}).get("name"),
        "hash": (save.get("meta") or {}).get("hash"),
        "last_scanned": _now(),
    }
    with _lock:
        d = _load()
        existing = next((x for x in d["dynasties"] if x["id"] == did), None)
        entry["created"] = existing.get("created") if existing else _now()
        d["dynasties"] = [entry] + [x for x in d["dynasties"] if x["id"] != did]
        d["current"] = did
        _save(d)
    return entry


def set_current(dynasty_id: str) -> bool:
    with _lock:
        d = _load()
        if any(x["id"] == dynasty_id for x in d["dynasties"]):
            d["current"] = dynasty_id
            _save(d)
            return True
    return False


def remove(dynasty_id: str) -> None:
    with _lock:
        d = _load()
        d["dynasties"] = [x for x in d["dynasties"] if x["id"] != dynasty_id]
        if d.get("current") == dynasty_id:
            d["current"] = d["dynasties"][0]["id"] if d["dynasties"] else None
        _save(d)
