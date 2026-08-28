"""Save discovery, selection, and snapshots for Dynasty+ Tools.

Responsibilities:
  * Own the "current" dynasty pointer (year/week).
  * Read dynasty state from the real CFB 27 saves folder (each registered
    dynasty resolves to its own autosave via the college profile); archive each
    week's snapshot so past weeks stay browsable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import confsetup, dynasty_paths
from .saveparse import cfb27

# Per-dynasty runtime state lives at data/dynasties/<id>/state.json.

# Per-week snapshots of the save, so browsing a past week shows that week's
# dynasty rather than the live one. The generated module content (cache.py) is
# the historical record; this keeps the raw dynasty dict consistent alongside it.
# Snapshots live at data/dynasties/<id>/archive/<year>/<week>.json.

# --- runtime app state (current pointer) ---------------------------------
def _state_file() -> Path:
    """The current dynasty's runtime state file, scoped under its own directory."""
    return dynasty_paths.current_root() / "state.json"


def _load_app_state() -> dict[str, Any]:
    path = _state_file()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            pass
    return {"year": 2026, "week": 1}


def _save_app_state(state: dict[str, Any]) -> None:
    path = _state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
    except OSError:
        pass


def current_pointer() -> dict[str, int]:
    s = _load_app_state()
    return {"year": s["year"], "week": s["week"]}


def set_pointer(year: int, week: int) -> None:
    s = _load_app_state()
    s["year"], s["week"] = year, week
    _save_app_state(s)


def status() -> dict[str, Any]:
    return {"running": False, "module": None, "progress": 0, "total": 0}


# --- dynasty loading ------------------------------------------------------
def _read_save() -> dict[str, Any] | None:
    """The CURRENT dynasty's live state, parsed from its own save in the game's
    saves folder (the college profile maps each dynasty to its autosave, so two
    dynasties never shadow each other). PROFILE-COLLEGE only keeps rows for
    recently touched sessions, so when the current dynasty's row has rotated
    away its save is read through the registry (save file name + school hint)
    instead of silently falling back to a DIFFERENT dynasty's save. The
    newest-save fallback remains only for the never-scanned cold start."""
    from . import dynasties
    # Respect a context-bound identity (used by the live playoff sync). Scan
    # may change the registry pointer concurrently, but one read transaction
    # must never jump from the save it began with to the newly selected save.
    cur = dynasty_paths.current_id()
    found = cfb27.discover()
    entry = next((e for e in found if e["dynasty_id"] == cur), None)
    if entry is not None:
        return cfb27.read_save(entry["save_path"], entry["slot"])
    reg = dynasties.get(cur) if cur else None
    if reg and reg.get("save_name"):
        path = cfb27.saves_dir() / reg["save_name"]
        d = cfb27.read_save(str(path), school=reg.get("school"),
                            dynasty_numeric_id=(reg.get("game_id") or None))
        if d is not None:
            return d
    # Newest-save fallback ONLY when nothing is selected yet (cold start): with a
    # current dynasty whose save cannot be located, returning another dynasty's
    # save would leak its recruits/board/texts into this one. Better to serve
    # nothing and let the UI ask for a rescan.
    if cur is None and found:
        return cfb27.read_save(found[0]["save_path"], found[0]["slot"])
    return None


def _archive(dynasty: dict[str, Any], year: int, week: int) -> None:
    """Snapshot a week's save under ITS OWN dynasty (keyed by meta.dynasty_id), so
    an archived week is always filed under the dynasty it belongs to, regardless of
    which dynasty is currently selected."""
    did = (dynasty.get("meta") or {}).get("dynasty_id")
    path = dynasty_paths.root_for(did) / "archive" / str(year) / f"{week}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(dynasty, fh, indent=2, default=str)
    except OSError:
        pass


def _read_archive(year: int, week: int) -> dict[str, Any] | None:
    path = dynasty_paths.current_root() / "archive" / str(year) / f"{week}.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def load_dynasty(year: int | None = None, week: int | None = None) -> dict[str, Any]:
    """Return the dynasty state for a (year, week).

    The current week comes from the live CFB 27 save; past weeks come from the
    per-week archive captured as each week was current.
    """
    ptr = current_pointer()
    year = year if year is not None else ptr["year"]
    week = week if week is not None else ptr["week"]

    save = _read_save()
    if save is not None:
        s_year = int(save["season"]["year"])
        s_week = int(save["season"]["week"])
        _archive(save, s_year, s_week)
        if (year, week) == (s_year, s_week):
            return confsetup.apply_overlay(save)

    archived = _read_archive(year, week)
    if archived is not None:
        # Snapshots taken before national entries carried espn_id would render
        # every logo/helmet as a monogram; repair them on read.
        cfb27.backfill_national_ids(archived)
        return confsetup.apply_overlay(archived)
    if save is not None:
        return confsetup.apply_overlay(save)  # best effort: live state for an un-archived week
    return {"meta": {"source": "none"}, "season": {"year": year, "week": week},
            "team": {}, "schedule": {}, "national": {}}


def load_live_dynasty() -> dict[str, Any]:
    """The dynasty as of the SAVE's own current week, never an archived
    snapshot.

    load_dynasty(pointer) serves an ARCHIVED week whenever the app pointer
    lags the save, and the pointer only advances on Scan/select (the Tools
    app has no watcher moving it). The playoff sync runs off autosaves, so
    reading through the pointer at the CCG -> bowl-week boundary handed it
    the CCG week's pre-championship snapshot: the field froze with stale
    rankings and records, and with conference_champions empty the champion
    auto-bids fell back to each conference's best-RANKED team (observed:
    Ole Miss picked over actual SEC champion Florida; Alabama seeded 2 off
    its pre-CCG rank). Save-state consumers must read through this instead."""
    save = _read_save()
    if save is not None:
        _archive(save, int(save["season"]["year"]), int(save["season"]["week"]))
        return confsetup.apply_overlay(save)
    ptr = current_pointer()
    return load_dynasty(ptr["year"], ptr["week"])


def save_present() -> bool:
    return _read_save() is not None


def save_pointer() -> dict[str, Any]:
    """The save's CURRENT season/week + hash, independent of where the companion
    is pointed. The live watch compares this to the entered week to auto-advance
    when the real game moves the week forward."""
    save = _read_save()
    if save is None:
        return {"present": False, "year": None, "week": None, "hash": None}
    return {
        "present": True,
        "year": int(save["season"]["year"]),
        "week": int(save["season"]["week"]),
        "hash": save["meta"].get("hash"),
    }


# --- explicit scan (the user-driven handoff) ------------------------------
def scan() -> dict[str, Any]:
    """Read the game's saves folder and register/update every visible dynasty
    found there (the Scan button). A library card the user removed stays hidden
    while its backing save exists; Import is the explicit way to bring it back.
    Entries no longer backed by a save are pruned. Sets the pointer to the
    current dynasty's week and archives its snapshot. Does not generate, so
    opening the app stays instant; tabs generate their content on demand."""
    from . import dynasties
    found = cfb27.discover()
    if not found:
        # PROFILE-COLLEGE only retains rows for recently touched sessions, so
        # discover() can come up empty even though registered dynasties still
        # have their save files on disk (observed mid-playoff). Do NOT report
        # "no save" and prune everything in that case: keep the registry as-is
        # so the current dynasty stays usable and the Scan button does not
        # 404 with a spurious popup.
        reg = dynasties.list_all()
        entries = reg.get("dynasties") or []
        alive = [e for e in entries
                 if e.get("save_name") and (cfb27.saves_dir() / e["save_name"]).exists()]
        if alive:
            return {"present": True, "registered_only": True,
                    "dynasties": entries, "current": reg.get("current")}
        return {"present": False}

    previous_current = dynasties.current_id()
    # One-time migration to the per-save-file identity: a dynasty world's store
    # (keyed by the old numeric id) moves to its NEWEST save's per-file id, so
    # the conference setup / archives / media carry over. `found` is newest-first.
    migrated: set[str] = set()
    for e in found:
        if e["game_id"] in migrated:
            continue
        migrated.add(e["game_id"])
        dynasties.migrate_store(f"cfb27-{e['game_id']}", e["dynasty_id"])

    registered: list[dict[str, Any]] = []
    saves_by_id: dict[str, dict[str, Any]] = {}
    hidden_live_ids = {e["dynasty_id"] for e in found
                       if dynasties.is_hidden(e["dynasty_id"])}
    for e in found:
        if e["dynasty_id"] in hidden_live_ids:
            continue
        save = cfb27.read_save(e["save_path"], e["slot"])
        if save is None:
            continue
        # Entries scanned before the game's numeric dynasty id was parsed keep
        # their archives/cache by re-keying onto the real id.
        dynasties.adopt_legacy(e["dynasty_id"], (save.get("team") or {}).get("school"))
        entry = dynasties.upsert_from_save(save, save_name=e["save_name"],
                                           game_id=e["game_id"], make_current=False)
        _archive(save, int(save["season"]["year"]), int(save["season"]["week"]))
        registered.append(entry)
        saves_by_id[entry["id"]] = save

    # PROFILE-COLLEGE only keeps rows for recently touched sessions, so a live
    # dynasty's row can rotate away between play sessions. Registry entries
    # whose save FILE still exists are re-read through the registry's own
    # school hint (and stay registered) instead of being pruned as deleted.
    for reg in list(dynasties.list_all().get("dynasties") or []):
        if reg["id"] in saves_by_id or not reg.get("save_name"):
            continue
        path = cfb27.saves_dir() / reg["save_name"]
        if not path.is_file():
            continue
        save = cfb27.read_save(str(path), school=reg.get("school"),
                               dynasty_numeric_id=(reg.get("game_id") or None))
        if save is None:
            registered.append(reg)  # keep the stale card rather than pruning
            continue
        entry = dynasties.upsert_from_save(save, save_name=reg["save_name"],
                                           game_id=reg.get("game_id"),
                                           make_current=False)
        _archive(save, int(save["season"]["year"]), int(save["season"]["week"]))
        registered.append(entry)
        saves_by_id[entry["id"]] = save

    # Preserve hidden cards only while their backing files remain discoverable.
    # This makes Remove persistent across Scan without making a deleted file's
    # identity stay hidden forever if a new save later reuses its name.
    valid_ids = {x["id"] for x in registered} | hidden_live_ids
    dynasties.prune_missing(valid_ids)
    if not registered:
        return {"present": True, "dynasties": [], "current": None,
                "hidden": len(hidden_live_ids)}

    # Stay on the dynasty the user was in when it still exists; otherwise the
    # most recently played one (discover() returns newest first).
    current_id = previous_current if previous_current in saves_by_id else registered[0]["id"]
    dynasties.set_current(current_id)
    confsetup.invalidate_caches()
    save = saves_by_id[current_id]
    entry = next(x for x in registered if x["id"] == current_id)
    s_year = int(save["season"]["year"])
    s_week = int(save["season"]["week"])
    set_pointer(s_year, s_week)
    state = _load_app_state()
    state["last_seen_hash"] = save["meta"].get("hash")
    _save_app_state(state)
    return {"present": True, "dynasty": entry, "dynasties": registered,
            "year": s_year, "week": s_week}


def select_dynasty(dynasty_id: str) -> dict[str, Any] | None:
    """Make a previously scanned dynasty current and point the app at its week."""
    from . import dynasties
    if not dynasties.set_current(dynasty_id):
        return None
    confsetup.invalidate_caches()
    entry = dynasties.get(dynasty_id)
    if entry:
        set_pointer(entry["year"], entry["week"])
    return entry


def _safe_save_path(save_path: str) -> Path | None:
    """Resolve a caller-supplied save path and confirm it is a file that lives
    directly in the game's saves folder, so the browse/import endpoints can
    never be pointed at an arbitrary file elsewhere on disk."""
    if not save_path:
        return None
    try:
        p = Path(save_path).resolve()
        base = cfb27.saves_dir().resolve()
    except (OSError, RuntimeError):
        return None
    return p if p.parent == base and p.is_file() else None


def browse_saves() -> list[dict[str, Any]]:
    """Every DYNASTY-* save file in the saves folder (the 'Import a save' list),
    annotated with the program the profile knows for it and whether it is already
    in the library. `discover()` only sees saves whose PROFILE-COLLEGE row is
    still live, so a dynasty whose row rotated away (or a manual save that never
    had one) is invisible to Scan; this lists them all so the user can import one
    by hand and pick their program when the save has no row. Newest first."""
    from . import dynasties
    from .saveparse import container, profile
    d = cfb27.saves_dir()
    if not d.is_dir():
        return []
    slots = {s.save_name: s for s in profile.read_slots(d)}
    reg_by_name: dict[str, dict[str, Any]] = {}
    for e in dynasties.list_all().get("dynasties") or []:
        if e.get("save_name"):
            reg_by_name.setdefault(e["save_name"], e)
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob("DYNASTY-*")):
        if not p.is_file() or p.suffix == ".bak":
            continue
        head = container.peek(p)
        if head is None:
            continue
        _version, saved_at, _build = head
        slot = slots.get(p.name)
        entry = reg_by_name.get(p.name)
        school = slot.school if slot else (entry.get("school") if entry else None)
        week_label = None
        if slot and slot.week_label:
            week_label = f"{slot.week_label} {slot.week}".strip() if slot.week else slot.week_label
        out.append({
            "save_name": p.name,
            "save_path": str(p),
            "saved_at": saved_at.isoformat() if saved_at else "",
            "school": school or None,
            "week_label": week_label,
            "has_profile_row": slot is not None,
            "registered": entry is not None,
            "dynasty_id": entry.get("id") if entry else None,
        })
    return sorted(out, key=lambda e: e["saved_at"] or "", reverse=True)


def save_team_options(save_path: str) -> list[dict[str, Any]] | None:
    """The team list from one save file (for the import team picker), or None
    when the path is outside the saves folder or not a readable CFB 27 save."""
    p = _safe_save_path(save_path)
    return cfb27.team_options(p) if p is not None else None


def import_save(save_path: str, school: str | None = None) -> dict[str, Any] | None:
    """Register ONE save file the user picked by hand, even when it has no
    profile row. Identity comes from the profile row when the save still has
    one, otherwise from the `school` the user chose in the picker; the numeric
    dynasty id (profile-only) rides along when present so the entry groups with
    the rest of its dynasty world. Returns the library entry, or None when the
    path is not a readable save or the program cannot be resolved."""
    from . import dynasties
    from .saveparse import profile
    p = _safe_save_path(save_path)
    if p is None:
        return None
    slot = profile.slot_for(p)
    numeric = slot.dynasty_id if slot else None
    save = cfb27.read_save(str(p), slot,
                           school=school or (slot.school if slot else None),
                           dynasty_numeric_id=numeric)
    if save is None:
        return None
    # Import is an explicit recovery action, so it reverses a prior Remove.
    dynasties.unhide(save["meta"]["dynasty_id"])
    dynasties.adopt_legacy(save["meta"]["dynasty_id"], (save.get("team") or {}).get("school"))
    entry = dynasties.upsert_from_save(save, save_name=p.name, game_id=numeric or None,
                                       make_current=False)
    _archive(save, int(save["season"]["year"]), int(save["season"]["week"]))
    return entry


def save_hash() -> str | None:
    """Hash of the currently selected live save, if one is readable."""
    save = _read_save()
    return (save.get("meta") or {}).get("hash") if save else None
