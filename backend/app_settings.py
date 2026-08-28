"""Persisted user paths: the CFB 27 install root, the dynasty saves folder,
and (optionally) the MMC Modding Tools folder.

The first two are the machine-specific locations the app needs. Both are
auto-detected on first run (backend/gamefind.py) and can be changed from the
in-app Setup screen (a native folder picker), so a non-standard install or a
saves folder on another drive works without editing env vars or restarting.

Persisted to data/app_settings.json. Resolution precedence for each path:
  1. the value the user set in Setup (persisted here)
  2. the matching env var, folded into config (CFBMOD_SAVE_PATH / CFBMOD_GAME_ROOT)
  3. the platform default (Documents saves folder / Steam install path)

A near-leaf module: it depends only on config, and is read by
saveparse.cfb27 (saves folder) and the extraction path (install root).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from . import config

_lock = threading.Lock()
_STORE_FILE = config.DATA_DIR / "app_settings.json"
_KEYS = ("save_path", "game_root", "modtools_path")


def _load_raw() -> dict[str, Any]:
    try:
        return json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _load() -> dict[str, Any]:
    data = _load_raw()
    return {k: data.get(k) for k in _KEYS if data.get(k)}


def _persist(store: dict[str, Any]) -> None:
    _STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STORE_FILE.write_text(json.dumps(store, indent=1), encoding="utf-8")


def set_paths(*, save_path: str | None = None, game_root: str | None = None,
              modtools_path: str | None = None) -> dict[str, Any]:
    """Persist any of the paths. Pass a value to set it, "" to clear it back to
    the default, or None to leave it unchanged."""
    with _lock:
        store = _load_raw()  # preserve other settings (e.g. autosync_enabled)
        for key, val in (("save_path", save_path), ("game_root", game_root),
                         ("modtools_path", modtools_path)):
            if val is None:
                continue
            val = val.strip()
            if val:
                store[key] = val
            else:
                store.pop(key, None)
        _persist(store)
        return {k: store.get(k) for k in _KEYS if store.get(k)}


def autosync_enabled() -> bool:
    """Whether the background auto-sync (the save watcher's automatic poll
    push and playoff writes) is on. Default on; a per-app persisted setting,
    so the preference remains local to this installation."""
    val = _load_raw().get("autosync_enabled")
    return True if val is None else bool(val)


def set_autosync_enabled(enabled: bool) -> bool:
    """Persist the auto-sync master switch. Returns the new value."""
    with _lock:
        store = _load_raw()
        store["autosync_enabled"] = bool(enabled)
        _persist(store)
    return bool(enabled)


def _looks_like_saves(d: Path) -> bool:
    """Whether a folder holds the game's dynasty saves (the profile file or
    any DYNASTY-* save)."""
    try:
        return (d / "PROFILE-COLLEGE").exists() or any(d.glob("DYNASTY-*"))
    except OSError:
        return False


def _normalize_save_dir(p: Path) -> Path:
    """Forgive an off-by-one-level folder pick. A directory picker hides
    files, so users picking the saves location sometimes land one level up
    (the game's 'EA SPORTS College Football 27' folder): when the chosen
    folder does not itself hold saves but has a 'saves' child, use the child.
    A single save FILE resolves to its containing folder, as before."""
    if p.is_file():
        return p.parent
    try:
        child = p / "saves"
        if p.is_dir() and not _looks_like_saves(p) and child.is_dir():
            return child
    except OSError:
        pass
    return p


def resolve_save_path() -> Path:
    """The saves folder to scan: user override, else env/default (config)."""
    override = _load().get("save_path")
    raw = (override or config.SAVE_PATH or "").strip()
    if raw:
        return _normalize_save_dir(Path(raw).expanduser())
    return Path.home() / "Documents" / "EA SPORTS College Football 27" / "saves"


def resolve_game_root() -> Path:
    """The CFB 27 install folder for art extraction: user override, else default."""
    override = _load().get("game_root")
    return Path((override or config.GAME_ROOT).strip()).expanduser()


def resolve_modtools_path() -> Path | None:
    """The MMC Modding Tools folder the user pointed at, or None when unset
    (backend.modtools falls back to auto-discovery)."""
    override = _load().get("modtools_path")
    return Path(override).expanduser() if override else None


def status() -> dict[str, Any]:
    """What the UI needs: the resolved paths, whether each exists, and whether
    the user has explicitly set them (vs falling back to a default)."""
    store = _load()
    save = resolve_save_path()
    game = resolve_game_root()
    return {
        "save_path": str(save),
        "save_path_set": bool(store.get("save_path")),
        "save_path_exists": save.is_dir(),
        "game_root": str(game),
        "game_root_set": bool(store.get("game_root")),
        "game_root_exists": game.is_dir(),
        "autosync_enabled": autosync_enabled(),
    }
