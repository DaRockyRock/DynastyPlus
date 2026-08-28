"""Registry of dynasties the companion has scanned in.

The companion does not auto-watch or auto-generate. The user plays CFB 27, then
clicks Scan: the companion reads the game's saves folder and registers/updates
one entry per dynasty found there (keyed by the game's own dynasty id from the
college profile). The landing screen lists them so the user picks which to
continue. Each entry tracks the latest scanned year/week, record, coach, and
which save file backs it.

One JSON document at data/dynasties.json:
    {"dynasties": [ {entry}, ... ], "current": "<id>",
     "hidden": ["<id>", ...]}

Removing a card only hides it from Dynasty+. It never deletes the CFB 27 save
or the per-dynasty companion store. Hidden live saves stay hidden across Scan;
the explicit Import flow unhides them.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
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
                d.setdefault("hidden", [])
                return d
        except (OSError, ValueError):
            pass
    return {"dynasties": [], "current": None, "hidden": []}


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


def is_hidden(dynasty_id: str) -> bool:
    return dynasty_id in set(_load().get("hidden") or [])


def unhide(dynasty_id: str) -> bool:
    """Make a previously removed save visible again. Returns whether it was
    hidden. The explicit Import flow calls this before registering the file."""
    with _lock:
        d = _load()
        hidden = list(d.get("hidden") or [])
        if dynasty_id not in hidden:
            return False
        d["hidden"] = [x for x in hidden if x != dynasty_id]
        _save(d)
        return True


def upsert_from_save(save: dict[str, Any], *, save_name: str | None = None,
                     game_id: str | None = None,
                     make_current: bool = True) -> dict[str, Any]:
    """Register or update ONE save file from its dynasty-save dict.

    Keyed by the save's per-FILE id (the game's numeric dynasty id plus the
    file name, stamped into meta by the parser), so every save file is its own
    library entry and its per-file editor settings
    never touch another file. `game_id` is the shared dynasty world (for
    grouping/display); `save_name` is the file in the game's saves folder."""
    team = save.get("team", {}) or {}
    season = save.get("season", {}) or {}
    # Fall back to school+file when the parser could not stamp a per-file id:
    # a bare school slug would make two different dynasties for the same school
    # share one id and overwrite each other's editor settings.
    did = ((save.get("meta") or {}).get("dynasty_id")
           or _slug(" ".join(filter(None, [team.get("school") or team.get("name"), save_name]))))
    entry = {
        "id": did,
        "game_id": game_id,
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
        "next_game": ((save.get("schedule") or {}).get("upcoming") or {}).get("opponent"),
        "hash": (save.get("meta") or {}).get("hash"),
        "save_name": save_name,
        "last_scanned": _now(),
    }
    with _lock:
        d = _load()
        existing = next((x for x in d["dynasties"] if x["id"] == did), None)
        entry["created"] = existing.get("created") if existing else _now()
        d["dynasties"] = [entry] + [x for x in d["dynasties"] if x["id"] != did]
        if make_current or d.get("current") is None:
            d["current"] = did
        _save(d)
    return entry


def adopt_legacy(new_id: str, school: str | None) -> str | None:
    """One-time migration: re-key an entry created before the game's numeric
    dynasty id was parsed (an old save-derived id like
    'cfb27-college-27-rl1-…-charlotte') onto its real id, moving the
    per-dynasty store directory with it so archives/cache/media survive.
    Only save-derived legacy ids ('cfb27-…') are eligible; obsolete
    entries are pruned instead. Returns the old id when a migration ran."""
    if not school:
        return None
    with _lock:
        d = _load()
        if any(x["id"] == new_id for x in d["dynasties"]):
            return None
        old = next((x for x in d["dynasties"]
                    if x["id"] != new_id and x["id"].startswith("cfb27-")
                    # only the old build-id form ('cfb27-college-27-...') is legacy;
                    # anything keyed by the game's numeric id ('cfb27-<digits>...',
                    # incl. per-save-file ids) is current and must NOT be re-keyed
                    and not re.match(r"cfb27-\d+", x["id"])
                    and (x.get("school") or "").lower() == school.lower()), None)
        if old is None:
            return None
        old_id = old["id"]
        from . import dynasty_paths
        src, dst = dynasty_paths.root_for(old_id), dynasty_paths.root_for(new_id)
        if src.is_dir() and not dst.exists():
            try:
                shutil.move(str(src), str(dst))
            except OSError:
                return None
        old["id"] = new_id
        if d.get("current") == old_id:
            d["current"] = new_id
        _save(d)
        return old_id


def migrate_store(old_id: str, new_id: str) -> bool:
    """Move a per-dynasty store directory from an old id to a new one when the
    identity scheme changes (dynasty-keyed -> per-save-file keyed), so archives,
    cache, media, and the conference setup survive. No-op unless the source
    exists and the destination does not. Returns True when a move ran."""
    if old_id == new_id:
        return False
    from . import dynasty_paths
    src, dst = dynasty_paths.root_for(old_id), dynasty_paths.root_for(new_id)
    if not src.is_dir() or dst.exists():
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return True
    except OSError:
        return False


def prune_missing(valid_ids: set[str]) -> list[str]:
    """Drop entries not backed by a dynasty in the game's saves folder (deleted
    dynasties and obsolete test entries). The per-dynasty store directory is
    left on disk untouched. Returns the removed ids."""
    with _lock:
        d = _load()
        removed = [x["id"] for x in d["dynasties"] if x["id"] not in valid_ids]
        hidden = [x for x in d.get("hidden") or [] if x in valid_ids]
        if not removed and hidden == (d.get("hidden") or []):
            return []
        d["dynasties"] = [x for x in d["dynasties"] if x["id"] in valid_ids]
        d["hidden"] = hidden
        if d.get("current") not in valid_ids:
            d["current"] = d["dynasties"][0]["id"] if d["dynasties"] else None
        _save(d)
        return removed


def set_current(dynasty_id: str) -> bool:
    with _lock:
        d = _load()
        if any(x["id"] == dynasty_id for x in d["dynasties"]):
            d["current"] = dynasty_id
            _save(d)
            return True
    return False


def remove(dynasty_id: str) -> bool:
    """Hide one library card without deleting its save or companion data.

    Returns False when the id was not registered. A later explicit Import
    unhides it; ordinary Scan leaves it hidden while the backing save exists.
    """
    with _lock:
        d = _load()
        if not any(x["id"] == dynasty_id for x in d["dynasties"]):
            return False
        d["dynasties"] = [x for x in d["dynasties"] if x["id"] != dynasty_id]
        hidden = list(d.get("hidden") or [])
        if dynasty_id not in hidden:
            hidden.append(dynasty_id)
        d["hidden"] = hidden
        if d.get("current") == dynasty_id:
            d["current"] = d["dynasties"][0]["id"] if d["dynasties"] else None
        _save(d)
        return True
