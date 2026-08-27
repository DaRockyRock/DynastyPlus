"""The Arc Registry: storylines that live across weeks.

A recruiting battle, a hot seat, a playoff push: each is a long-lived object with
its own qualities, that OPENS when conditions arise, ADVANCES week to week, and
RESOLVES (a commit, a coach saved, an elimination). Arcs are what make the media
feel like a season instead of disconnected weeks: a candidate that advances an
open arc gets a salience boost (the news "follow_up" value) and a cross-week
continuity note ("week 3 of the saga"), so coverage threads instead of resetting.

The weekly tick is idempotent (per-arc week guards), so the several rundown builds
in a week never double-advance an arc. Persisted per dynasty+year.
"""
from __future__ import annotations

import json
import threading
from typing import Any

from .. import dynasty_paths
from .state import WorldState

_lock = threading.Lock()


def _path(year: int):
    return dynasty_paths.sub("editorial") / f"{year}_arcs.json"


def _read(year: int) -> dict[str, Any]:
    p = _path(year)
    if not p.exists():
        return {"year": year, "arcs": []}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("arcs"), list) else {"year": year, "arcs": []}
    except (OSError, ValueError):
        return {"year": year, "arcs": []}


def _write(year: int, data: dict[str, Any]) -> None:
    try:
        _path(year).write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass


def _arc_id(type_: str, subjects: list[str]) -> str:
    return f"{type_}:" + "|".join(sorted(subjects))


# --- open detection ---------------------------------------------------------
def _detect_opens(state: WorldState, dynasty: dict, week: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rec = dynasty.get("recruiting") or {}
    committed = {c.get("name") for c in rec.get("commits") or []}
    targets = sorted((t for t in rec.get("targets") or [] if t.get("name")),
                     key=lambda t: -((t.get("stars") or 0) * (t.get("interest") or 0)))
    for t in targets[:4]:
        if (t.get("stars") or 0) >= 4 and (t.get("interest") or 0) >= 50 and t["name"] not in committed:
            out.append({"type": "recruiting_battle", "subjects": [t["name"]],
                        "q": {"interest": t.get("interest", 0), "stars": t.get("stars", 0)}})
    if not state.season_open and (state.seat_temp >= 60 or state.expectation_delta <= -2.0):
        out.append({"type": "hot_seat", "subjects": [state.coach_name],
                    "q": {"pressure": state.seat_temp}})
    if not state.season_open and week >= 6 and (state.cfp_rank or state.record[0] >= state.record[1] + 3):
        out.append({"type": "playoff_push", "subjects": [state.team_name], "q": {}})
    return out


def _close_reason(arc: dict, state: WorldState, dynasty: dict) -> str | None:
    t = arc["type"]
    if t == "recruiting_battle":
        name = arc["subjects"][0]
        rec = dynasty.get("recruiting") or {}
        if any(c.get("name") == name for c in rec.get("commits") or []):
            return "committed"
        tgt = next((x for x in rec.get("targets") or [] if x.get("name") == name), None)
        if tgt is None:
            return "off the board"
        if (tgt.get("interest") or 0) < 20:
            return "interest cooled"
        return None
    if t == "hot_seat":
        return "pressure eased" if state.seat_temp < 40 else None
    if t == "playoff_push":
        return "eliminated" if state.record[1] >= 5 else None
    return None


def _update_qualities(arc: dict, state: WorldState, dynasty: dict) -> None:
    t = arc["type"]
    q = arc.setdefault("arc_qualities", {})
    if t == "recruiting_battle":
        tgt = next((x for x in (dynasty.get("recruiting") or {}).get("targets") or []
                    if x.get("name") == arc["subjects"][0]), None)
        if tgt:
            q["interest"] = tgt.get("interest", q.get("interest", 0))
    elif t == "hot_seat":
        q["pressure"] = state.seat_temp


def _continuity(arc: dict, week: int) -> str:
    weeks = week - int(arc.get("opened_week", week)) + 1
    if weeks < 2:
        return ""        # week 1 of an arc is fresh, no callback yet
    subj = arc["subjects"][0] if arc["subjects"] else "this"
    last = subj.split()[-1]
    if arc["type"] == "recruiting_battle":
        return (f"The {last} recruitment has been a running storyline (week {weeks} of the saga); "
                "frame it as an ongoing thread, not brand-new news.")
    if arc["type"] == "hot_seat":
        return f"The heat on {subj} has been building for {weeks} weeks; continue that thread."
    if arc["type"] == "playoff_push":
        return "The playoff push has been the season's throughline; keep it in that arc."
    return ""


def _boosts(arc: dict, cand) -> bool:
    """cand is a StoryCandidate dataclass (attribute access, not dict)."""
    if not set(arc["subjects"]) & set(getattr(cand, "subjects", []) or []):
        return False
    t, ct = arc["type"], getattr(cand, "type", None)
    if t == "recruiting_battle":
        return ct in ("recruiting_battle", "commit", "decommit")
    if t == "hot_seat":
        return ct in ("hot_seat_watch", "user_result")
    if t == "playoff_push":
        return ct in ("user_result", "poll_jump", "poll_fall")
    return False


def tick(dynasty: dict, state: WorldState, pool: list, year: int, week: int) -> list[dict[str, Any]]:
    """Open/advance/close arcs for the week (idempotent), then annotate the candidate
    pool: arc-advancing candidates get the follow_up salience signal and a continuity
    note. Returns the active arcs (for the rundown + briefs)."""
    with _lock:
        data = _read(year)
        arcs = data["arcs"]
        by_id = {a["id"]: a for a in arcs}
        # CLOSE (idempotent: setting resolved twice is a no-op)
        for a in arcs:
            if a["status"] == "active":
                reason = _close_reason(a, state, dynasty)
                if reason:
                    a.update(status="resolved", close_reason=reason, closed_week=week)
        # OPEN (idempotent: skip if an arc with this id already exists)
        for spec in _detect_opens(state, dynasty, week):
            aid = _arc_id(spec["type"], spec["subjects"])
            if aid not in by_id:
                arc = {"id": aid, "type": spec["type"], "subjects": spec["subjects"],
                       "status": "active", "arc_qualities": spec["q"], "beats": [week],
                       "opened_week": week, "last_advanced_week": week, "tension": 0.5}
                arcs.append(arc)
                by_id[aid] = arc
        # ADVANCE (idempotent: only once per week via last_advanced_week guard)
        for a in arcs:
            if a["status"] == "active" and int(a.get("last_advanced_week", 0)) < week:
                _update_qualities(a, state, dynasty)
                a["last_advanced_week"] = week
                a.setdefault("beats", []).append(week)
        _write(year, data)
        active = [a for a in arcs if a["status"] == "active"]

    # annotate the pool (StoryCandidate dataclasses; read-only re-application, runs on
    # every build_rundown call so it is deterministic regardless of when the tick ran)
    for c in pool:
        for a in active:
            if _boosts(a, c):
                c.arc_id = a["id"]
                note = _continuity(a, week)
                if note:
                    c.arc_note = note
                c.signals["follow_up"] = max(c.signals.get("follow_up", 0.0), 1.0)
                break
    return active
