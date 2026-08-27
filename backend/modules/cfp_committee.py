"""CFP committee.

Models the real College Football Playoff selection committee (2025-26 roster of
twelve) as independent agents. Each member carries a factual biography, a
conference affiliation (for the logo badge), and a neutral "lens" describing how
this simulation models their perspective from their professional background.

The members are real public figures; the ballots they produce here rank the
fictional dynasty teams, so every ranking is clearly a simulation artifact, not
a real-world opinion. Photos are intentionally omitted (each member uses an
initials avatar); a `photo` URL can be supplied if licensed imagery is added.
"""
from __future__ import annotations

import os
from typing import Any

from .. import conferences, customization, narrative, progress
from . import base

MODULE = "cfp_committee"

# The real selection committee does not convene until late in the season; before then a
# seeded 12-team bracket built off 0-0 records is an artifact, not a ranking. The members
# project a field year-round, but the seeded BRACKET is withheld until this week (the real
# committee's first reveal is typically around week 10). Tunable via the env var.
_REVEAL_WEEK = int(os.getenv("CFBMOD_CFP_REVEAL_WEEK", "10"))

# The committee is user-editable (see customization.py). It ships as the real
# 2025-26 roster; role/bio are factual public info and lens is a simulated
# tendency. Read at call time so edits take effect immediately.
def _members():
    return customization.section("cfp_committee")


def _initials(name: str) -> str:
    return "".join(w[0] for w in name.split()[:2]).upper()


def _seed(name: str) -> int:
    return sum(ord(c) for c in name) or 7


def _ballot(base_order: list[dict], seed: int) -> list[dict[str, Any]]:
    """Deterministic per-member top-25 from the base AP order.

    The top of the board stays largely stable (committee consensus); the middle
    and back shuffle via a seeded PRNG so ballots differ believably.
    """
    order = list(base_order)
    rng = seed
    n = len(order)

    def nxt() -> int:
        nonlocal rng
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        return rng

    swaps = 7
    for _ in range(swaps):
        i = 4 + (nxt() % max(1, n - 5))
        if i + 1 < n:
            order[i], order[i + 1] = order[i + 1], order[i]

    return [dict(t, rank=idx + 1) for idx, t in enumerate(order)]


def _lower_on(ballot: list[dict], base_index: dict[str, int]) -> str | None:
    """Abbreviation of the team this member dropped furthest below consensus."""
    worst_team, worst_delta = None, 0
    for t in ballot:
        base_rank = base_index.get(t["team"])
        if base_rank is None:
            continue
        delta = t["rank"] - base_rank
        if delta > worst_delta:
            worst_delta, worst_team = delta, t
    return (worst_team.get("abbr") or worst_team.get("team")) if worst_team else None


def _team_meta(name: str, base_order: list[dict]) -> dict[str, Any]:
    for t in base_order:
        if t["team"] == name:
            return {"team": name, "abbr": t.get("abbr"), "espn_id": t.get("espn_id"), "record": t.get("record", "")}
    return {"team": name, "abbr": name[:3].upper(), "espn_id": None, "record": ""}


def _build_bracket(final: list[str], base_order: list[dict]) -> dict[str, Any]:
    seeds = [dict(_team_meta(t, base_order), seed=i + 1) for i, t in enumerate(final[:12])]
    byes = seeds[:4]
    first_round = [
        {"home": seeds[4], "away": seeds[11]},
        {"home": seeds[5], "away": seeds[10]},
        {"home": seeds[6], "away": seeds[9]},
        {"home": seeds[7], "away": seeds[8]},
    ]
    return {"byes": byes, "first_round": first_round}


def _member_meta(m: dict) -> dict[str, Any]:
    return {
        "member": m["name"], "role": m["role"], "affiliation": m["affiliation"],
        "conference": m["conference"], "conference_id": conferences.conf_id(m["conference"]),
        "bio": m["bio"], "lens": m["lens"], "initials": _initials(m["name"]),
        "photo": m.get("image") or None,
    }


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    base_order = dynasty["national"].get("ap_top25") or []
    if not base_order:
        base_order = dynasty["national"].get("cfp_top12") or []
    base_index = {t["team"]: t["rank"] for t in base_order}

    ballots: list[dict[str, Any]] = []
    for m in _members():
        progress.set_sub_step(m["name"])
        ballot = _ballot(base_order, _seed(m["name"]))
        top1 = ballot[0]["team"] if ballot else ""
        justification = (
            f"{m['lens']} On my ballot {top1} sits at No. 1, with real separation through the first "
            "four. The nine-through-twelve range is where I part ways with the room."
        )
        ballots.append(dict(_member_meta(m),
                            top25=ballot, justification=justification,
                            lower_on=_lower_on(ballot, base_index)))

    # synthesis: average rank across ballots -> final order
    scores: dict[str, float] = {}
    counts: dict[str, int] = {}
    for b in ballots:
        for t in b["top25"]:
            scores[t["team"]] = scores.get(t["team"], 0) + t["rank"]
            counts[t["team"]] = counts.get(t["team"], 0) + 1
    final = sorted(scores.keys(), key=lambda t: scores[t] / counts[t])
    final_top12 = final[:12]

    # persist member stances for week-over-week continuity
    for b in ballots:
        narrative.update_persona(year, b["member"], {
            "affiliation": b["affiliation"], "bias": b["lens"],
            "last_take": f"had {b['top25'][0]['team']} No. 1 in {dynasty['season']['week_label']}",
        })

    convened = int(week or 0) >= _REVEAL_WEEK
    if convened:
        bracket = _build_bracket(final_top12, base_order)
        synthesis = (
            "The committee reconciled twelve independent ballots. The top four held firm across "
            "nearly every member, while the nine-through-twelve range drew the sharpest disagreement "
            "and several pointed dissents.")
    else:
        # Pre-reveal: the members still project a field, but there is no official seeded
        # bracket yet. Present it plainly as a projection so a week-1 12-seed bracket off
        # 0-0 records never masquerades as a committee ranking.
        bracket = None
        wk = (dynasty.get("season", {}) or {}).get("week_label") or f"Week {week}"
        synthesis = (
            f"The selection committee has not convened yet ({wk}); it releases its first official "
            f"rankings around Week {_REVEAL_WEEK}. These are way-too-early projections from the "
            "members, built off the preseason poll, not an official seeding, so there is no seeded "
            "bracket to show yet.")

    data = {
        "module": MODULE, "source": "mock",
        "convened": convened,
        "reveal_week": _REVEAL_WEEK,
        "members": [_member_meta(m) for m in _members()],
        "ballots": ballots,
        "final_top12": final_top12,
        "bracket": bracket,
        "synthesis": synthesis,
    }
    return base.sanitize(data)
