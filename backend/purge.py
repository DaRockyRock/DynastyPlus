"""Delete dynasty state, returning both apps to a clean slate.

Per-dynasty data lives under data/dynasties/<id>/ (narrative, messages, feed,
world, interviews, cache, archive, and the runtime state), fully isolated by
dynasty. On top of that sit the Simulator's game-data stores (sim seasons +
budget), the two boundary files (the dynasty save + companion inbox), the dynasty
registry, and the two customization stores.

delete_everything() wipes ALL of it for a full "start from scratch". Kept (not
dynasty state): the committed FBS league seed, the cached ESPN team metadata, the
per-team local-media research, the bundled mock content, uploaded images, and the
LLM connection settings.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import config

# Directories whose entire contents are wiped on a full reset.
_PURGE_DIRS = [
    config.DATA_DIR / "dynasties",        # all per-dynasty data (the isolated layout)
    config.SIM_DIR,                       # simulated seasons + recruiting classes
    config.BUDGET_DIR,                    # authoritative NIL / Dynasty Points spend
    # Legacy top-level stores from before per-dynasty isolation, cleared too so a
    # full reset leaves nothing behind.
    config.CACHE_DIR, config.NARRATIVE_DIR, config.FEED_DIR, config.MESSAGES_DIR,
    config.WORLD_DIR, config.INTERVIEWS_DIR, config.DATA_DIR / "dynasty_archive",
]

# Single files: the two boundary files, the registry, the legacy companion
# pointer, and both customization stores. Removing a customization store reverts
# it to its canonical defaults on the next read (the Store overlays edits).
_PURGE_FILES = [
    Path(config.SAVE_PATH),                       # data/save/dynasty.json
    Path(config.INBOX_PATH),                      # data/save/companion_inbox.json
    config.DATA_DIR / "dynasties.json",           # scanned-dynasty registry
    config.DATA_DIR / "app_state.json",           # legacy companion pointer
    config.DATA_DIR / "customization_game.json",  # team identity (Simulator)
    config.DATA_DIR / "customization.json",       # media flavor (companion)
]


def _empty_dir(path: Path) -> int:
    """Remove every child of `path` (files and subtrees); keep the dir itself."""
    if not path.exists():
        return 0
    removed = 0
    for child in path.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def _remove_file(path) -> bool:
    try:
        Path(path).unlink()
        return True
    except OSError:
        return False


def delete_everything() -> dict:
    """Wipe all dynasty state across both apps and reset customization to defaults.

    Idempotent: anything already gone is skipped. Returns a small summary of what
    was cleared, for the response and the confirmation toast."""
    cleared = {p.name: _empty_dir(p) for p in _PURGE_DIRS}
    removed_files = [f.name for f in _PURGE_FILES if _remove_file(f)]
    return {"cleared": cleared, "removed_files": removed_files}
