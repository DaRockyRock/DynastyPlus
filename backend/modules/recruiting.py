"""Recruiting board.

247-style recruit rankings with star ratings, scouting reports, crystal-ball
predictions, visit recaps, and NIL narrative. Fictional analysts disagree on
prospects. Grounded in the dynasty recruiting data (commits + targets).

Scaffold: rich mock content now; LLM prompt wired for when generation is on.
"""
from __future__ import annotations

from typing import Any

from .. import customization, llm, progress
from . import base

MODULE = "recruiting"

# Analysts are user-editable (see customization.py); read at call time.
def _analysts():
    return customization.section("recruiting_analysts")

SYSTEM = (
    "You are a recruiting desk producing a 247-style board: star ratings, "
    "scouting reports, crystal-ball predictions, visit recaps, and NIL angles. "
    "Multiple analysts may disagree. Ground everything in the dynasty data. "
    "Never use dashes as punctuation; use commas or periods, never dashes."
)


def _prompt(dynasty: dict) -> str:
    return (
        f"Build the recruiting board for {dynasty['team']['name']} in "
        f"{dynasty['season']['week_label']}. Use the commits and targets in the "
        "dynasty data. Return STRICT JSON with keys: \"class_summary\" (string), "
        "\"commits\" (array), \"targets\" (array), \"crystal_balls\" (array), "
        "\"visit_recaps\" (array), \"nil_narrative\" (string). For each prospect "
        "include name, position, stars, rating, hometown, scouting_report, and "
        "for analysts include differing analyst_takes. JSON only."
    )


def _scout(pos: str) -> str:
    lib = {
        "QB": "Quick processor with live arm and easy velocity to the boundary. Needs to speed up his clock under pressure.",
        "WR": "Smooth route runner who separates late and high-points the football. Adds play strength after a year in the program.",
        "EDGE": "Bendy edge with a violent first step and a developing counter. High motor, plays to the whistle.",
        "OT": "Massive frame with heavy hands and a wide base in pass pro. Footwork in space is the swing skill.",
        "CB": "Twitchy press corner who mirrors well and trusts his eyes. Must add ballast to hold up on the perimeter.",
        "LB": "Downhill thumper who diagnoses fast and fills with bad intentions. Coverage range is the question.",
        "RB": "One-cut slasher with contact balance and a second gear. Three-down upside if the hands develop.",
        "S": "Rangy center-fielder with closing burst and a nose for the football. Tackling angles need cleanup.",
        "DT": "Stout interior anchor who eats doubles and resets the line of scrimmage. Pass-rush plan is a work in progress.",
    }
    return lib.get(pos, "Versatile prospect with a high floor and room to grow within the scheme.")


def _mock(dynasty: dict) -> dict[str, Any]:
    rec = dynasty["recruiting"]
    team = dynasty["team"]["name"]

    commits = []
    for c in rec["commits"]:
        commits.append(dict(c, scouting_report=_scout(c["position"]),
                            analyst_takes=[
                                {"analyst": "Theo Marsh", "take": f"Bought in early; the {c['stars']}-star grade is fair and could rise."},
                                {"analyst": "Bianca Ruiz", "take": "Like the film more than the ranking. Plug-and-play in two years."},
                            ]))

    targets = []
    for t in rec["targets"]:
        targets.append(dict(t, scouting_report=_scout(t["position"]),
                            analyst_takes=[
                                {"analyst": "Theo Marsh", "take": f"Momentum is real; {t['leader']} is the team to beat."},
                                {"analyst": "Coach Del Ray", "take": f"Scheme fit is clean. Predicting {t['predicted']}."},
                            ]))

    crystal_balls = []
    for t in rec["targets"]:
        confident = t["predicted"] == team
        crystal_balls.append({
            "prospect": t["name"], "position": t["position"], "stars": t["stars"],
            "analyst": "Theo Marsh", "prediction": t["predicted"],
            "confidence": 8 if confident else 5,
            "note": f"Logged a crystal ball to {t['predicted']} after the latest visit chatter.",
        })

    visit_recaps = []
    if rec["targets"]:
        top = rec["targets"][0]
        visit_recaps = [{
            "prospect": top["name"], "position": top["position"],
            "type": "Official visit", "when": "This weekend",
            "recap": (f"{top['name']} is on campus for an official visit during the "
                      f"{dynasty['schedule']['upcoming']['opponent']} game: a player-led tour, a sit-down "
                      "with the coordinators, and a night-game atmosphere. A pivotal date in the recruitment."),
        }]

    rank_nat = rec.get("class_rank_national")
    rank_conf = rec.get("class_rank_conference")
    n_commits = len(rec.get("commits") or [])
    if rank_nat:
        nil = (f"With the No. {rank_nat} class nationally, the {team} collective leans on player "
               "development and brand reach in its NIL pitch rather than pure dollars.")
        class_summary = (f"{team} hold the No. {rank_nat} class nationally"
                         + (f" (No. {rank_conf} in the conference)" if rank_conf else "")
                         + f", built on {n_commits} commitment{'s' if n_commits != 1 else ''}.")
    else:
        nil = (f"The {team} collective leans on player development and brand reach in its NIL "
               "pitch rather than pure dollars.")
        class_summary = (f"{team} are assembling their class with {n_commits} "
                         f"commitment{'s' if n_commits != 1 else ''} so far this cycle.")

    return {
        "class_summary": class_summary,
        "class_rank_national": rec["class_rank_national"],
        "class_rank_conference": rec["class_rank_conference"],
        "analysts": _analysts(),
        "commits": commits, "targets": targets,
        "crystal_balls": crystal_balls, "visit_recaps": visit_recaps,
        "nil_narrative": nil,
    }


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    progress.set_sub_step("Targets, commits, and visits")
    source = "mock"
    if use_llm and base.llm_available():
        try:
            context = base.build_context(dynasty, year, week)
            data = llm.generate_json(SYSTEM, _prompt(dynasty), cached_context=context,
                                     grounding=base.reactive_grounding(dynasty, year, week), max_tokens=4096)
            data.setdefault("analysts", _analysts())
            source = "llm"
        except Exception:
            data = _mock(dynasty)
    else:
        data = _mock(dynasty)
    return base.sanitize(dict(data, module=MODULE, source=source))
