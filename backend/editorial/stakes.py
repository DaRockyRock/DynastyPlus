"""The Stakes Computer: what this week MEANS, as deterministic schedule math.

Real coverage is mostly forward-looking ("a loss Saturday eliminates them"), and
all of it is arithmetic over the remaining schedule: bowl-eligibility counts,
clinch/elimination conditions, streak context, the spread of the next game, the
hot-seat line. Every stake is emitted as a ready-to-quote string plus a weight
that feeds the salience scorer, so the briefs can lead with what matters without
asking the model to do math (it never does arithmetic, per the design).
"""
from __future__ import annotations

from typing import Any

from . import ratings
from .state import WorldState

BOWL_WINS = 6


def compute(dynasty: dict, state: WorldState, year: int) -> list[dict[str, Any]]:
    """The user's program stakes for this week: [{text, weight, tags}]."""
    out: list[dict[str, Any]] = []
    w, l = state.record
    team = state.team_name

    # season-opening projection: the baseline everything is measured against
    if state.season_open:
        proj = ratings.projected_wins(year, dynasty)
        hist = (dynasty.get("history") or [])
        last_season = f" after going {hist[0].get('overall')} last season" if hist else ""
        out.append({"text": f"The model projects {team} around {proj:.0f} wins{last_season}; "
                            f"year {state.coach_tenure} is the season the trajectory has to show",
                    "weight": 0.5, "tags": ["projection"]})

    # bowl math: countdown, clinch, elimination (all pure arithmetic)
    if not state.season_open and state.games_remaining >= 0:
        need = BOWL_WINS - w
        if need <= 0 and w - 1 < BOWL_WINS:
            out.append({"text": f"{team} clinched bowl eligibility at {w}-{l}",
                        "weight": 0.9, "tags": ["bowl", "clinched"]})
        elif need > 0 and need == state.games_remaining:
            out.append({"text": f"{team} must win out: {need} wins needed with {state.games_remaining} to play",
                        "weight": 0.95, "tags": ["bowl", "must_win_out"]})
        elif need > state.games_remaining:
            out.append({"text": f"{team} is eliminated from bowl contention at {w}-{l}",
                        "weight": 0.9, "tags": ["bowl", "eliminated"]})
        elif 0 < need <= 2 and state.games_remaining <= 5:
            out.append({"text": f"{team} sits {need} win{'s' if need > 1 else ''} from bowl eligibility "
                                f"with {state.games_remaining} to play",
                        "weight": 0.6, "tags": ["bowl", "countdown"]})

    # the next game, framed by its own expectation
    up = state.next_game
    if up and up.get("opponent"):
        opp = up["opponent"]
        opp_rank = up.get("opponent_rank")
        p = ratings.game_prob(year, dynasty, team, opp, a_home=bool(up.get("home")),
                              line=up.get("spread"),
                              a_abbr=(dynasty.get("team") or {}).get("abbreviation"))
        venue = "at home" if up.get("home") else "on the road"
        if p <= 0.35:
            tag = f"a live upset shot ({p * 100:.0f} percent)" if p >= 0.15 else \
                  f"a heavy underdog ({p * 100:.0f} percent)"
            out.append({"text": f"{team} is {tag} {venue} against "
                                f"{('No. ' + str(opp_rank) + ' ') if opp_rank else ''}{opp}",
                        "weight": 0.7, "tags": ["next_game", "underdog"]})
        elif p >= 0.75:
            out.append({"text": f"{team} is expected to handle {opp} {venue} "
                                f"({p * 100:.0f} percent); anything else is a story",
                        "weight": 0.5, "tags": ["next_game", "favorite"]})
        else:
            out.append({"text": f"{team} against {opp} {venue} is close to a coin flip "
                                f"({p * 100:.0f} percent)",
                        "weight": 0.6, "tags": ["next_game", "tossup"]})
        if state.rivalry_next:
            note = next((r.get("note") for r in (dynasty.get("rivals") or [])
                         if isinstance(r, dict) and r.get("name") == opp and r.get("note")), None)
            out.append({"text": f"Rivalry week: {team} and {opp}" + (f", {note}" if note else ""),
                        "weight": 0.85, "tags": ["rivalry"]})

    # streak context
    if state.streak >= 3:
        out.append({"text": f"{team} carries a {state.streak}-game winning streak",
                    "weight": 0.55, "tags": ["streak", "winning"]})
    elif state.streak <= -3:
        out.append({"text": f"{team} has dropped {abs(state.streak)} straight",
                    "weight": 0.7, "tags": ["streak", "losing"]})

    # the hot-seat line: expectation, not record, is the bar
    if not state.season_open:
        if state.expectation_delta <= -1.5 or state.seat_temp >= 70:
            out.append({"text": f"{state.coach_name} is trending below the program baseline "
                                f"({state.expectation_delta:+.1f} wins vs expectation); the seat is live",
                        "weight": 0.8, "tags": ["hot_seat"]})
        elif state.expectation_delta >= 1.5:
            out.append({"text": f"{state.coach_name} is running {state.expectation_delta:+.1f} wins "
                                "ahead of expectation",
                        "weight": 0.55, "tags": ["overperforming"]})

    return out
