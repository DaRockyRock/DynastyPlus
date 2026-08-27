"""Resolve per-dynasty data directories.

Every companion-generated store (narrative, messages, feed, world reactions,
interviews, the per-week content cache, the dynasty archive, and the runtime
state pointer) is scoped to ONE dynasty so nothing leaks between dynasties. They
all live under data/dynasties/<dynasty_id>/<store>/...

The "current" dynasty is whichever the registry (dynasties.json) points at, set
on Scan / select. Stores resolve their directory through sub("<name>"); their
public APIs still take (year, week) and are unchanged, so callers do not thread a
dynasty id around: the active dynasty is read from the registry here.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import config

_ROOT = config.DATA_DIR / "dynasties"
# Home used before any dynasty has been scanned. The companion shows the library
# and does not generate until Scan, so stores are not normally hit first, but a
# stable fallback keeps reads/writes safe.
_UNSCANNED = "_unscanned"


def _safe(dynasty_id: object) -> str:
    """A filesystem-safe directory name for a dynasty id (which may be an opaque
    id from the game, or our '<school-slug>-<seed>')."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", str(dynasty_id or "")).strip("-")
    return s or _UNSCANNED


def current_id() -> str | None:
    from . import dynasties  # lazy: avoids an import cycle (dynasties imports config only)
    return dynasties.current_id()


def root_for(dynasty_id: object) -> Path:
    return _ROOT / _safe(dynasty_id)


def current_root() -> Path:
    return root_for(current_id())


def sub(name: str) -> Path:
    """The current dynasty's <name> subdirectory, created on demand."""
    p = current_root() / name
    p.mkdir(parents=True, exist_ok=True)
    return p
