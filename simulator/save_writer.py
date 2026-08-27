"""Writes the dynasty save file the Dynasty+ companion watches.

The save is the full schema-conforming dynasty dict that sim/adapter.build_dynasty
already produces (with the embedded budget snapshot + meta.hash). Writes are
atomic: temp file then os.replace, which surfaces to the companion's watchdog as
an on_moved event on the save path (the same atomic-save pattern real games use).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from backend import config, schema
from backend.sim import adapter, state as sim_state

_SAVE = Path(config.SAVE_PATH)
_TMP = Path(str(config.SAVE_PATH) + ".tmp")


def _current_week(year: int) -> int:
    return sim_state.status(year).get("week", 1)


def write(year: int, week: int | None = None) -> dict[str, Any] | None:
    """Build and atomically write the save for `year` at `week` (defaults to the
    sim's current week). No-op when no season is active. Returns the dynasty dict."""
    if not sim_state.is_active(year):
        return None
    if week is None:
        week = _current_week(year)
    dynasty = adapter.build_dynasty(year, week)
    problems = schema.validate(dynasty)
    if problems:
        # Never write a malformed save; the companion would reject it anyway.
        raise ValueError("save failed validation: " + "; ".join(problems))
    _SAVE.parent.mkdir(parents=True, exist_ok=True)
    with _TMP.open("w", encoding="utf-8") as fh:
        json.dump(dynasty, fh, indent=2, default=str)
    os.replace(_TMP, _SAVE)
    return dynasty


def clear() -> None:
    """Remove the save (e.g. on season reset) so the companion shows cold start."""
    try:
        _SAVE.unlink()
    except OSError:
        pass
