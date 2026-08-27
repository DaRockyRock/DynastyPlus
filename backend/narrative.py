"""Persistent narrative memory layer.

This is the continuity engine. It lives alongside the save-data layer and
grows every week. Every generation prompt receives a compact rendering of it
as context, so a transfer-portal rumor planted in Week 4 can resurface in the
offseason and committee members can reference prior stances week over week.

Stored as a single JSON document per season at data/narrative/<year>.json.
"""
from __future__ import annotations

import datetime as _dt
import json
from typing import Any

from . import dynasty_paths

MAX_THREADS = 80  # cap so prompt context stays bounded


def _path(year: int):
    return dynasty_paths.sub("narrative") / f"{year}.json"


def _empty(year: int) -> dict[str, Any]:
    return {
        "year": year,
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        # Ongoing storylines that should persist and be referenced.
        "threads": [],
        # Per-reporter / per-committee-member persistent opinions and track
        # records, keyed by name.
        "personas": {},
        # Short factual log of what happened each week (results, milestones).
        "weekly_log": [],
    }


def load(year: int) -> dict[str, Any]:
    path = _path(year)
    if not path.exists():
        return _empty(year)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        # backfill any newly-added keys
        base = _empty(year)
        base.update(data)
        return base
    except (OSError, ValueError):
        return _empty(year)


def save(state: dict[str, Any]) -> None:
    year = state.get("year")
    try:
        with _path(year).open("w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
    except OSError:
        pass


def add_thread(year: int, *, week: int, category: str, summary: str, tags: list[str] | None = None) -> None:
    """Record an ongoing storyline (rumor, hot-seat heat, recruiting battle...).

    Deduped by summary: re-running the weekly pipeline or several near-identical
    statements in one week must not flood the memory with the same line (a small
    model anchors hard on whatever it sees repeated, which was the cause of the
    'a pointed statement is reverberating' pollution). A repeat is a no-op."""
    summary = (summary or "").strip()
    if not summary:
        return
    state = load(year)
    norm = summary.lower()
    if any((t.get("summary") or "").strip().lower() == norm for t in state["threads"]):
        return
    state["threads"].append({
        "week": week,
        "category": category,
        "summary": summary,
        "tags": tags or [],
    })
    state["threads"] = state["threads"][-MAX_THREADS:]
    save(state)


def log_week(year: int, week: int, entries: list[str]) -> None:
    """Append a factual week summary used to anchor future generation."""
    state = load(year)
    # replace any existing entry for this week (idempotent regeneration)
    state["weekly_log"] = [e for e in state["weekly_log"] if e.get("week") != week]
    state["weekly_log"].append({"week": week, "entries": entries})
    state["weekly_log"].sort(key=lambda e: e.get("week", 0))
    save(state)


def update_persona(year: int, name: str, fields: dict[str, Any]) -> None:
    """Merge persistent attributes for a reporter or committee member."""
    state = load(year)
    persona = state["personas"].get(name, {})
    persona.update(fields)
    state["personas"][name] = persona
    save(state)


def render_context(year: int, *, up_to_week: int | None = None, max_threads: int = 30) -> str:
    """Compact text rendering injected into generation prompts."""
    state = load(year)
    lines: list[str] = [f"NARRATIVE MEMORY (season {year}). Continuity is the top priority.", ""]

    threads = state["threads"]
    if up_to_week is not None:
        threads = [t for t in threads if t.get("week", 0) <= up_to_week]
    if threads:
        # Collapse duplicate summaries (older data may carry repeats from before
        # add_thread deduped) so the same line is never shown twice.
        seen: set[str] = set()
        deduped = []
        for t in threads[-max_threads:]:
            norm = (t.get("summary") or "").strip().lower()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            deduped.append(t)
        lines.append("Ongoing storylines:")
        for t in deduped:
            lines.append(f"  - [W{t.get('week')}] ({t.get('category')}) {t.get('summary')}")
        lines.append("")

    log = state["weekly_log"]
    if up_to_week is not None:
        log = [e for e in log if e.get("week", 0) <= up_to_week]
    if log:
        lines.append("Season timeline:")
        for entry in log[-12:]:
            for item in entry.get("entries", []):
                lines.append(f"  - W{entry.get('week')}: {item}")
        lines.append("")

    if state["personas"]:
        lines.append("Established personas (keep their voices/stances consistent):")
        for name, p in list(state["personas"].items())[:20]:
            bits = []
            if p.get("affiliation"):
                bits.append(p["affiliation"])
            if p.get("bias"):
                bits.append("bias: " + p["bias"])
            if p.get("reliability") is not None:
                bits.append(f"reliability {p['reliability']}")
            if p.get("last_take"):
                bits.append("last take: " + p["last_take"])
            lines.append(f"  - {name}" + (f" ({'; '.join(bits)})" if bits else ""))
        lines.append("")

    return "\n".join(lines).strip()
