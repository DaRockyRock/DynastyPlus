"""Resolve the per-dynasty files used by the save editors.

Playoff, bowl, poll, and recruiting settings are scoped to one selected save
under ``data/dynasties/<dynasty_id>/`` so edits never cross dynasty files.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import re
from pathlib import Path
from typing import Iterator

from . import config

_ROOT = config.DATA_DIR / "dynasties"
# Stable home used before any dynasty has been scanned.
_UNSCANNED = "_unscanned"
_UNBOUND = object()
_BOUND_ID: ContextVar[object] = ContextVar("dynasty_paths_bound_id",
                                           default=_UNBOUND)


def _safe(dynasty_id: object) -> str:
    """A filesystem-safe directory name for a dynasty id (which may be an opaque
    id from the game, or our '<school-slug>-<seed>')."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", str(dynasty_id or "")).strip("-")
    return s or _UNSCANNED


def current_id() -> str | None:
    bound = _BOUND_ID.get()
    if bound is not _UNBOUND:
        return bound  # type: ignore[return-value]
    from . import dynasties  # lazy: avoids an import cycle (dynasties imports config only)
    return dynasties.current_id()


@contextmanager
def bind_current(dynasty_id: str | None) -> Iterator[None]:
    """Pin all per-dynasty paths in this execution context to one identity.

    A Scan or library selection can change the registry's current pointer while
    a background playoff sync is still running. Without a binding, that sync
    can read one dynasty's format/save, then resolve ``live.json`` again after
    the pointer changes and write the old bracket into the newly selected
    dynasty. Context-local binding keeps every read, state file, snapshot, and
    save lookup in one sync attached to the identity captured at its start.
    """
    token = _BOUND_ID.set(dynasty_id)
    try:
        yield
    finally:
        _BOUND_ID.reset(token)


def root_for(dynasty_id: object) -> Path:
    return _ROOT / _safe(dynasty_id)


def current_root() -> Path:
    return root_for(current_id())


def sub(name: str) -> Path:
    """The current dynasty's <name> subdirectory, created on demand."""
    p = current_root() / name
    p.mkdir(parents=True, exist_ok=True)
    return p
