"""The weekly rundown and its rendering as grounding for the news generators.

build_rundown() runs the deterministic editorial pass (state -> ratings ->
stakes -> candidates -> score -> seeded MMR selection), persists the scored
rundown for debuggability ("why did this story run?"), and the render functions
turn it into the compact, authoritative grounding blocks the existing news
prompts consume. This is build-plan step 1: the editorial brain decides the
slate, the current generators still write it.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .. import dynasty_paths
from . import arcs as arc_registry
from . import candidates as cand
from . import profile, ratings, scorer, stakes
from .state import WorldState, extract

# Slate sizes for the grounding brief (the generator writes 3-4 articles per
# scope; give it one extra thread of material to choose from).
NATIONAL_SLOTS = 5
PROGRAM_SLOTS = 5


def build_rundown(dynasty: dict, year: int, week: int) -> dict[str, Any]:
    """The week's editorial decisions, deterministic for a given save."""
    expected = ratings.expected_wins_played(year, dynasty)
    state = extract(dynasty, year, week, expected_wins_so_far=expected)
    pool = cand.detect(dynasty, state, year, week)
    # The arc registry runs BEFORE scoring so a candidate that advances an open
    # storyline carries the follow_up salience signal (and a cross-week continuity
    # note) into the score. Idempotent per week.
    active_arcs = arc_registry.tick(dynasty, state, pool, year, week)
    seed = f"{dynasty_paths.current_id()}:{year}:{week}:{state.phase}"
    scorer.score(pool, seed=seed)
    rundown = {
        "year": year, "week": week, "phase": state.phase, "mood": state.mood,
        "state": asdict(state),
        "stakes": stakes.compute(dynasty, state, year),
        "arcs": active_arcs,
        "national": [asdict(c) for c in scorer.select(pool, NATIONAL_SLOTS, scope="national")],
        "program": [asdict(c) for c in scorer.select(pool, PROGRAM_SLOTS, scope="program")],
        "profile": asdict(profile.current()),
    }
    try:  # the dev/eval view: every story with its signals and score
        p = dynasty_paths.sub("editorial") / f"{year}_wk{week:02d}_rundown.json"
        p.write_text(json.dumps(rundown, indent=1, default=str), encoding="utf-8")
    except OSError:
        pass
    return rundown


def _coach_of(dynasty: dict, team: str | None) -> str | None:
    c = (dynasty.get("coaches") or {}).get(team or "")
    return (c.get("name") if isinstance(c, dict) else c) or None


def _story_lines(dynasty: dict, items: list[dict], *, numbered: bool = True) -> list[str]:
    """One compact line per chosen story: the facts, with each subject team's
    fictional coach inlined so a national story never reaches for a real name."""
    lines: list[str] = []
    for i, c in enumerate(items, 1):
        facts = "; ".join(str(v) for v in (c.get("facts") or {}).values() if v)
        coaches = ", ".join(f"{t}: {_coach_of(dynasty, t)}" for t in c.get("subjects") or []
                            if _coach_of(dynasty, t))
        line = f"{i}. [{c.get('type')}] {facts}"
        if coaches:
            line += f" (coaches: {coaches})"
        lines.append(line if numbered else line[3:])
    return lines


def national_brief(dynasty: dict, year: int, week: int,
                   rundown: dict[str, Any] | None = None) -> str:
    """The NATIONAL grounding block: the editorial slate, ranked, with previews
    explicitly marked, plus the poll top and the carousel watch. Replaces mining
    the dynasty JSON: the model writes THESE stories, in this order."""
    r = rundown or build_rundown(dynasty, year, week)
    blocks: list[str] = []
    items = r.get("national") or []
    if items:
        previews = any(c.get("phase") == "preview" for c in items)
        head = "This week's national stories, ranked by the news desk. Write THESE, biggest first"
        if previews:
            head += " (items marked NOT PLAYED are previews: no scores, no winners, nothing that happened)"
        blocks.append(head + ":\n" + "\n".join("  " + l for l in _story_lines(dynasty, items)))
    ap = [x for x in ((dynasty.get("national") or {}).get("ap_top25") or []) if x.get("team")]
    if ap:
        blocks.append("Top of the AP poll: " + ", ".join(
            f"{x['rank']}. {x['team']} ({x.get('record', '0-0')})" for x in ap[:8]) + ".")
    if not blocks:
        return ""
    user = (dynasty.get("team") or {}).get("name") or "the user's team"
    return (f"=== NATIONAL RUNDOWN (authoritative; cover these stories with these facts; "
            f"do NOT cover {user} here; never invent a player, stat, or score) ===\n"
            + "\n\n".join(blocks))


def feed_brief(dynasty: dict, year: int, week: int,
               rundown: dict[str, Any] | None = None) -> str:
    """The editorial block the social feed prepends to its grounding: the week's
    mood (so fan posts carry the right emotional tone) and the ranked top stories
    (so the timeline skews to what actually matters, with room for pundits to
    disagree on the lead). Returns '' if the rundown is empty."""
    r = rundown or build_rundown(dynasty, year, week)
    team = (dynasty.get("team") or {}).get("name") or "the program"
    items = sorted((r.get("national") or []) + (r.get("program") or []),
                   key=lambda c: -float(c.get("score") or 0))[:6]
    if not items:
        return ""
    lines = [
        f"WEEK MOOD around {team}: {r.get('mood')}. Home-fan posts should carry this emotional "
        "tone (euphoric celebration, anxious hand-wringing, grim doom, or steady confidence).",
        "THE WEEK'S BIGGEST STORIES, ranked by the news desk (skew most posts toward these, "
        "biggest first, and let pundits with opposing takes disagree on the lead):",
    ]
    lines += ["  " + l for l in _story_lines(dynasty, items)]
    return "=== EDITORIAL DESK (the week, ranked) ===\n" + "\n".join(lines)


def presser_brief(dynasty: dict, year: int, week: int,
                  rundown: dict[str, Any] | None = None) -> str:
    """The week's program storylines + stakes for the press conference, so reporters
    ask about the real threads (the hot seat, a recruiting battle, the next opponent,
    the playoff race), not only the game just played. Returns '' when nothing fits."""
    r = rundown or build_rundown(dynasty, year, week)
    lines: list[str] = []
    for s in (r.get("stakes") or [])[:3]:
        lines.append(s["text"])
    for c in (r.get("program") or [])[:3]:
        facts = "; ".join(str(v) for k, v in (c.get("facts") or {}).items() if v and k != "note")
        if facts:
            lines.append(facts)
    if not lines:
        return ""
    return ("This week's storylines around the program (some reporters ask about these, not "
            "only the game):\n" + "\n".join("  - " + l for l in lines))


def program_brief(dynasty: dict, year: int, week: int,
                  rundown: dict[str, Any] | None = None) -> str:
    """The PROGRAM grounding block: mood, stakes, and the chosen program slate."""
    r = rundown or build_rundown(dynasty, year, week)
    team = (dynasty.get("team") or {}).get("name") or "the program"
    state = r.get("state") or {}
    coach = state.get("coach_name") or "the head coach"
    blocks: list[str] = [f"WEEK MOOD around {team}: {r.get('mood')} (let the tone reflect it)."]
    # State the coach's ACTUAL job standing so the model does not import a hot-seat
    # narrative from training priors (the validator also rejects it, but saying it
    # plainly here prevents the wasted draft).
    seat = int(state.get("seat_temp") or 0)
    if seat < 45 and float(state.get("expectation_delta") or 0) > -1.0:
        blocks.append(f"{coach} is SECURE: not on any hot seat (seat {seat}/100). Do NOT write that "
                      "his job is in jeopardy, that he could be fired, or that his future is uncertain.")
    elif seat >= 70:
        blocks.append(f"{coach} is genuinely on the hot seat (seat {seat}/100); the pressure is real.")
    stakes_lines = r.get("stakes") or []
    if stakes_lines:
        blocks.append("What this week means (lead with these, they are the real stakes):\n"
                      + "\n".join(f"  - {s['text']}" for s in stakes_lines))
    items = r.get("program") or []
    if items:
        blocks.append("This week's program stories, ranked by the news desk:\n"
                      + "\n".join("  " + l for l in _story_lines(dynasty, items)))
    return ("=== PROGRAM RUNDOWN (authoritative; these are the week's stories and stakes; "
            "never invent a player, stat, or score) ===\n" + "\n\n".join(blocks))
