"""Awards watch.

Weekly trackers for the major awards (Heisman plus position honors) with a
fictional voter panel that updates its reasoning based on recent performance.
Grounded in the dynasty roster and national frontrunners.

Scaffold: rich mock content now; LLM prompt wired for later.
"""
from __future__ import annotations

from typing import Any

from .. import customization, llm, progress
from . import base

MODULE = "awards"

# Awards and the voter panel are user-editable (see customization.py).
def _awards():
    return customization.section("awards")


def _voter_panel():
    return customization.section("award_voters")

SYSTEM = (
    "You are an awards desk maintaining weekly watch lists with a voter panel "
    "that updates reasoning based on recent performance. Ground candidates in "
    "the dynasty roster and national frontrunners. Never use dashes as punctuation; use commas or periods, never dashes."
)


def _candidate(name: str, team: str, position: str, line: str, trend: str, blurb: str) -> dict[str, Any]:
    return {"name": name, "team": team, "position": position, "stat_line": line,
            "trend": trend, "blurb": blurb}


def _mock(dynasty: dict) -> dict[str, Any]:
    players = {p["position"]: p for p in dynasty["roster"]["key_players"]}
    qb = dynasty["roster"]["key_players"][0]
    team = dynasty["team"]["name"]
    heisman_field = dynasty["national"]["heisman_frontrunners"]

    heisman = [
        _candidate(qb["name"], team, "QB", qb["stat_line"], "up",
                   "Surging into the top tier after a road statement and a clean efficiency profile."),
    ]
    for h in heisman_field:
        if h["name"] != qb["name"]:
            heisman.append(_candidate(h["name"], h["team"], h["position"], "Frontrunner", "flat",
                                      "Holds preseason equity but has not separated in October."))
    heisman = heisman[:5]

    def pos_award(pos: str, default_name: str) -> list[dict[str, Any]]:
        p = players.get(pos)
        if p:
            return [_candidate(p["name"], team, pos, p["stat_line"], "up",
                               f"In the thick of the race with a {p['stat_line']} line.")]
        return [_candidate(default_name, "National field", pos, "Leading the position", "flat",
                           "Consensus frontrunner around the country.")]

    watch = {
        "heisman": heisman,
        "biletnikoff": pos_award("WR", "National WR1"),
        "butkus": pos_award("LB", "National LB1"),
        "outland": pos_award("OT", "National OL1"),
        "bednarik": pos_award("EDGE", "National EDGE1"),
    }

    panel_notes = [
        {"voter": "Dana Reyes", "award": "heisman",
         "note": f"Moving {qb['name']} up. The road win was the kind of moment a ballot remembers."},
        {"voter": "Marcus Hale", "award": "heisman",
         "note": f"Metrics back it: {qb['name']} is top-three in efficiency against a top-15 schedule."},
        {"voter": "Gabriela Soto", "award": "bednarik",
         "note": f"{players.get('EDGE', {}).get('name', 'The edge rusher')} is the best defender I have watched this month."},
    ]

    return {"awards": _awards(), "voter_panel": _voter_panel(), "watch": watch, "panel_notes": panel_notes}


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    progress.set_sub_step("Award watch lists")
    source = "mock"
    if use_llm and base.llm_available():
        try:
            context = base.build_context(dynasty, year, week)
            prompt = (
                f"Build the awards watch for {dynasty['season']['week_label']}. Return STRICT JSON "
                "with keys: \"watch\" (object keyed by award with candidate arrays) and "
                "\"panel_notes\" (array of {voter, award, note}). JSON only."
            )
            data = llm.generate_json(SYSTEM, prompt, cached_context=context,
                                     grounding=base.reactive_grounding(dynasty, year, week), max_tokens=1500)
            data.setdefault("awards", _awards())
            data.setdefault("voter_panel", _voter_panel())
            source = "llm"
        except Exception:
            data = _mock(dynasty)
    else:
        data = _mock(dynasty)
    return base.sanitize(dict(data, module=MODULE, source=source))
