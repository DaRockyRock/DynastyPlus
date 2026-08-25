"""Delete Dynasty+ Tools playthrough state and return a small summary."""
from __future__ import annotations

import shutil
from pathlib import Path

from . import config

# Directories whose entire contents are wiped on a full reset.
_PURGE_DIRS = [config.SIM_DIR, config.BUDGET_DIR]

_PURGE_FILES = [
    Path(config.SAVE_PATH),
    config.DATA_DIR / "customization_game.json",
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
    """Wipe all tools state and reset customization to its defaults."""
    cleared = {p.name: _empty_dir(p) for p in _PURGE_DIRS}
    removed_files = [f.name for f in _PURGE_FILES if _remove_file(f)]
    return {"cleared": cleared, "removed_files": removed_files}
