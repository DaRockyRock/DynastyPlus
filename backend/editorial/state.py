"""World state extraction: the qualities every editorial decision gates on.

The editorial engine never reads the raw save twice: this module distills it once
per tick into a flat WorldState (the "qualities" of the design doc), including the
computed week `mood` that becomes the tone directive in every brief. Everything
here is a pure function of the passed dynasty dict, per the repo rule that game
data flows only through the save.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GameResult:
    week: int
    opponent: str
    won: bool
    score: str            # pre-formatted, e.g. "28-24"
    home: bool


@dataclass
class WorldState:
    year: int
    week: int
    phase: str                       # "preview" | "reaction"
    season_open: bool
    # user program
    team_name: str
    school: str
    coach_name: str
    coach_tenure: int
    record: tuple[int, int]
    conf_record: tuple[int, int]
    streak: int                      # + win streak, - loss streak, 0 none
    ap_rank: int | None
    cfp_rank: int | None
    seat_temp: int                   # 0..100
    expectation_delta: float         # actual wins minus expected wins, so far
    mood: str                        # euphoric | confident | steady | anxious | grim
    # this week
    last_result: GameResult | None   # the user's most recent final
    next_game: dict[str, Any] | None # schedule.upcoming verbatim (has spread/coach)
    rivalry_next: bool
    games_played: int
    games_remaining: int
    # rolling
    extras: dict[str, Any] = field(default_factory=dict)


def _wl(rec: Any) -> tuple[int, int]:
    try:
        w, l = str(rec).split("-")[:2]
        return int(w), int(l)
    except (ValueError, AttributeError):
        return 0, 0


def _user_results(dynasty: dict) -> list[GameResult]:
    """The user's finals this season, oldest first, from schedule.full (the
    season-long ledger) with recent_results as the fallback shape."""
    out: list[GameResult] = []
    for g in (dynasty.get("schedule") or {}).get("full") or []:
        res = g.get("result")
        if not res:
            continue
        won = str(res).strip().upper().startswith("W")
        out.append(GameResult(week=int(g.get("week") or 0), opponent=g.get("opponent") or "",
                              won=won, score=str(g.get("score") or ""), home=bool(g.get("home"))))
    if not out:
        for g in (dynasty.get("schedule") or {}).get("recent_results") or []:
            res = str(g.get("result") or "")
            if not res:
                continue
            out.append(GameResult(week=int(g.get("week") or 0), opponent=g.get("opponent") or "",
                                  won=res.upper().startswith("W"), score=str(g.get("score") or ""),
                                  home=bool(g.get("home"))))
        out.reverse()
    return out


def _streak(results: list[GameResult]) -> int:
    if not results:
        return 0
    run = 0
    won = results[-1].won
    for r in reversed(results):
        if r.won != won:
            break
        run += 1
    return run if won else -run


def _mood(phase: str, last: GameResult | None, streak: int, expectation_delta: float,
          seat_temp: int, season_open: bool) -> str:
    """One computed word that sets the emotional temperature of the whole week.
    Personas map it to their own register (a grim week reads somber from the beat
    writer, furious from fans, careful from the AD)."""
    if season_open:
        return "anxious" if seat_temp >= 55 else "steady"
    if phase == "preview" or last is None:
        if streak >= 3 or expectation_delta >= 1.0:
            return "confident"
        if streak <= -3 or expectation_delta <= -1.5 or seat_temp >= 70:
            return "grim"
        if streak <= -2 or seat_temp >= 55:
            return "anxious"
        return "steady"
    # reaction: the result leads, the season context shades it
    if last.won:
        if streak >= 4 or expectation_delta >= 1.5:
            return "euphoric"
        return "confident"
    if streak <= -3 or expectation_delta <= -1.5 or seat_temp >= 70:
        return "grim"
    return "anxious"


def extract(dynasty: dict, year: int, week: int, *, expected_wins_so_far: float | None = None) -> WorldState:
    """Build the week's WorldState. `expected_wins_so_far` comes from the ratings
    store (sum of pre-game win probabilities of played games); without it the
    expectation delta falls back to .500 ball as the baseline."""
    t = dynasty.get("team") or {}
    hc = t.get("head_coach") or {}
    season = dynasty.get("season") or {}
    sched = dynasty.get("schedule") or {}
    rk = t.get("rankings") or {}

    results = _user_results(dynasty)
    last = results[-1] if results else None
    season_open = not results and int(season.get("week", week) or week) <= 1
    # reaction once the user's game for THIS week is final, else preview
    phase = "reaction" if (last and last.week == week) else "preview"

    w, l = _wl((t.get("record") or {}).get("overall"))
    played = len(results)
    full = sched.get("full") or []
    remaining = max(len(full) - played, 0) if full else max(12 - played, 0)

    if expected_wins_so_far is None:
        expected_wins_so_far = played / 2.0
    delta = float(w) - float(expected_wins_so_far)

    streak = _streak(results)
    seat = int(hc.get("hot_seat") or 0)
    up = sched.get("upcoming") or None
    rivals = {r.get("name") for r in (dynasty.get("rivals") or []) if isinstance(r, dict)}
    rivalry_next = bool(up and up.get("opponent") in rivals)

    return WorldState(
        year=year, week=week, phase=phase, season_open=season_open,
        team_name=t.get("name") or "", school=t.get("school") or t.get("name") or "",
        coach_name=hc.get("name") or "the head coach", coach_tenure=int(hc.get("tenure_years") or 1),
        record=(w, l), conf_record=_wl((t.get("record") or {}).get("conference")),
        streak=streak, ap_rank=rk.get("ap"), cfp_rank=rk.get("cfp"),
        seat_temp=seat, expectation_delta=round(delta, 2),
        mood=_mood(phase, last, streak, delta, seat, season_open),
        last_result=last, next_game=up, rivalry_next=rivalry_next,
        games_played=played, games_remaining=remaining,
    )
