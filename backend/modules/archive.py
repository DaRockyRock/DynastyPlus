"""Dynasty archive.

A persistent document that grows each season: season retrospectives, program
milestones, coaching-tree tracking, player legacy pages, and a decade
retrospective every ten seasons. Reads from the narrative memory layer so it
accumulates across the dynasty.

Scaffold: assembles a structured archive from current state + narrative memory.
"""
from __future__ import annotations

from typing import Any

from .. import narrative, progress
from . import base

MODULE = "archive"


def _wl(rec: str) -> tuple[int, int]:
    try:
        w, l = str(rec).split("-")[:2]
        return int(w), int(l)
    except (ValueError, AttributeError):
        return 0, 0


def _mock(dynasty: dict, year: int) -> dict[str, Any]:
    """Build the archive from ONLY what is true in the dynasty state, so it never
    invents a milestone or a game that did not happen. Empty sections (a fresh
    season with no results) are fine; the archive fills as the season is played."""
    team = dynasty["team"]
    hc = team["head_coach"]
    state = narrative.load(year)
    rec = team["record"]["overall"]
    w, l = _wl(rec)
    cfp = team["rankings"].get("cfp")
    ap = team["rankings"].get("ap")
    ranks = (team.get("stats") or {}).get("ranks") or {}
    off_rank = (ranks.get("points_per_game") or {}).get("national")
    def_rank = (ranks.get("points_allowed") or {}).get("national")
    recent = (dynasty.get("schedule", {}) or {}).get("recent_results") or []
    history = dynasty.get("history") or []

    # Milestones: only real, verifiable achievements from actual results / rankings
    # / prior seasons. Nothing is asserted that the state does not support.
    milestones: list[dict[str, Any]] = []
    for r in recent:
        if r.get("result") == "W" and r.get("rank_matchup"):
            milestones.append({
                "season": year, "title": "Ranked win",
                "detail": f"{team['name']} beat {r['rank_matchup']} {r.get('score', '')}".strip() + ".",
            })
    if cfp:
        milestones.append({
            "season": year, "title": "In the playoff field",
            "detail": f"{team['name']} reached No. {cfp} in the CFP projection at {rec}.",
        })
    elif ap:
        milestones.append({
            "season": year, "title": "Ranked nationally",
            "detail": f"{team['name']} are No. {ap} in the AP poll at {rec}.",
        })
    if history and history[0].get("overall"):
        last = history[0]
        milestones.append({
            "season": last.get("year", year - 1), "title": "Last season",
            "detail": (f"Finished {last['overall']}"
                       + (f", {last.get('result')}" if last.get("result") else "")
                       + (f" under {last.get('coach')}" if last.get("coach") else "") + "."),
        })

    legacy_pages = [{
        "player": p["name"], "position": p["position"], "years": p["year"],
        "summary": f"{p['stat_line']}. {p['note']}",
        "legacy": ("On track for the program record book" if p.get("rating", 0) >= 90
                   else "A foundational piece of the program"),
    } for p in team_key_players(dynasty)]

    coaching_tree = {
        "head_coach": hc["name"],
        "alma_mater": hc["alma_mater"],
        "tenure": f"{hc['tenure_years']} seasons",
        "branches": [
            {"name": c["name"], "role": c["role"], "note": c["notable"]}
            for c in dynasty["coaching_staff"] if c["role"] != "Head Coach"
        ],
    }

    # Season retrospective: factual, conditioned on whether games have been played
    # and what the rankings/stat ranks actually say (no invented superlatives).
    if w + l == 0:
        headline = f"{year}: {team['name']} open the season"
        parts = [f"{team['name']} begin {year}"]
        if history and history[0].get("overall"):
            parts.append(f"a season after going {history[0]['overall']}")
        parts.append(f"under {hc['name']}")
        body = ", ".join(parts) + "."
    else:
        headline = f"{year}: {team['name']} at {rec}"
        parts = [f"{team['name']} are {rec}"]
        if cfp:
            parts.append(f"No. {cfp} in the playoff projection")
        elif ap:
            parts.append(f"No. {ap} in the AP poll")
        if off_rank and off_rank <= 25:
            parts.append(f"No. {off_rank} nationally in scoring offense")
        if def_rank and def_rank <= 25:
            parts.append(f"No. {def_rank} in scoring defense")
        body = ", ".join(parts) + f". The {hc['name']} era continues to take shape."
    season_retros = [{"season": year, "headline": headline, "body": body}]

    decade_retro = None
    if year % 10 == 0 and history:
        spans = "; ".join(f"{h.get('year')} {h.get('overall')}" for h in history[:10] if h.get("overall"))
        if spans:
            decade_retro = {"decade": f"{year - 9}-{year}",
                            "summary": f"Season by season: {spans}."}

    return {
        "season": year,
        "milestones": milestones,
        "season_retrospectives": season_retros,
        "player_legacies": legacy_pages,
        "coaching_tree": coaching_tree,
        "decade_retrospective": decade_retro,
        "narrative_threads": state.get("threads", [])[-15:],
        "weekly_log": state.get("weekly_log", []),
    }


def team_key_players(dynasty: dict) -> list[dict[str, Any]]:
    return dynasty["roster"]["key_players"][:5]


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    progress.set_sub_step("Season retrospective")
    data = _mock(dynasty, year)
    return base.sanitize(dict(data, module=MODULE, source="mock"))
