"""The Continuity Ledger: what the newsroom already ran.

So coverage follows up instead of repeating ("for the third straight week...",
"the saga continues") and never runs the same headline twice. Records the beats
rendered each week (type + subjects + headline) and answers continuity questions
the brief builder asks. Persisted per dynasty+year under the editorial store.
"""
from __future__ import annotations

import json
import threading
from typing import Any

from .. import dynasty_paths

_lock = threading.Lock()


def _path(year: int):
    return dynasty_paths.sub("editorial") / f"{year}_ledger.json"


def _read(year: int) -> dict[str, Any]:
    p = _path(year)
    if not p.exists():
        return {"year": year, "weeks": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and "weeks" in data else {"year": year, "weeks": {}}
    except (OSError, ValueError):
        return {"year": year, "weeks": {}}


def record(year: int, week: int, beats: list[dict[str, Any]]) -> None:
    """Persist the week's rendered beats. Idempotent per week (overwrites the
    week's entry, so a regenerate replaces rather than appends)."""
    with _lock:
        data = _read(year)
        data["weeks"][str(week)] = [
            {"type": b.get("type") or b.get("candidate_type"),
             "subjects": b.get("subjects") or [],
             "headline": b.get("headline") or ""}
            for b in beats if isinstance(b, dict)
        ]
        try:
            _path(year).write_text(json.dumps(data, indent=1), encoding="utf-8")
        except OSError:
            pass


def _streak_for(data: dict, week: int, type_: str, subject: str, lookback: int = 4) -> int:
    """How many consecutive prior weeks ran a beat of this type about this subject."""
    run = 0
    for w in range(week - 1, max(0, week - 1 - lookback), -1):
        rows = data["weeks"].get(str(w)) or []
        if any(r.get("type") == type_ and subject in (r.get("subjects") or []) for r in rows):
            run += 1
        else:
            break
    return run


def continuity_note(year: int, week: int, type_: str, subjects: list[str]) -> str:
    """A short callback line for the brief, or "" when the story is fresh. Keyed on
    the primary subject's recent run for this story type."""
    if not subjects:
        return ""
    data = _read(year)
    subj = subjects[0]
    run = _streak_for(data, week, type_, subj, lookback=4)
    if run <= 0:
        return ""
    if type_ in ("recruiting_battle", "hot_seat_watch"):
        return "This thread has been building for weeks; treat it as an ongoing saga, not new news."
    if run >= 2:
        return f"This has been a storyline for {run} straight weeks; frame it as a continuing thread."
    return "This followed last week's coverage; acknowledge it as a follow-up."


def seen_headlines(year: int, week: int, lookback: int = 2) -> set[str]:
    """Normalized headlines from recent weeks, so an identical one is not re-run."""
    data = _read(year)
    out: set[str] = set()
    for w in range(week - 1, max(0, week - 1 - lookback), -1):
        for r in data["weeks"].get(str(w)) or []:
            h = (r.get("headline") or "").strip().lower()
            if h:
                out.add(h)
    return out
