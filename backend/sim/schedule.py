"""Season schedule generator.

Builds a full, conflict-free slate for every team in the universe: a 12-week
regular season where each team plays at most once per week. Conference games
form the backbone (a round-robin via the circle method, one round per week),
and the remaining open slots each week are filled with non-conference games by
a seeded greedy matcher that prefers fresh, cross-conference pairings.

Layout: weeks 1..LEAD open with non-conference play (like a real September),
then conference round i lands on week LEAD+i. Everything is deterministic from
the season seed, so a given (seed, year) always yields the same schedule.

A game is `{week, home, away, conference: bool, neutral: bool}`.
"""
from __future__ import annotations

import random
from typing import Any

from .engine import make_rng

WEEKS = 12          # regular-season weeks
CONF_WEEKS = 9      # how many conference rounds to schedule per team
LEAD = WEEKS - CONF_WEEKS  # opening non-conference weeks (3)


def _circle_rounds(teams: list[str], rng: random.Random) -> list[list[tuple[str, str]]]:
    """Round-robin rounds via the circle method. Odd team count -> a bye slot."""
    ts = teams[:]
    rng.shuffle(ts)
    if len(ts) % 2:
        ts.append(None)  # the bye marker
    n = len(ts)
    arr = ts[:]
    rounds: list[list[tuple[str, str]]] = []
    for _r in range(n - 1):
        pairs: list[tuple[str, str]] = []
        for i in range(n // 2):
            a, b = arr[i], arr[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((a, b))
        rounds.append(pairs)
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]  # rotate, fixing the first seat
    return rounds


def build_schedule(universe: dict[str, dict[str, Any]], seed: int, year: int) -> list[dict[str, Any]]:
    all_teams = list(universe.keys())
    by_conf: dict[str, list[str]] = {}
    for name, v in universe.items():
        by_conf.setdefault(v.get("conference") or "FBS Independents", []).append(name)

    week_games: dict[int, list[dict[str, Any]]] = {w: [] for w in range(1, WEEKS + 1)}
    matched: dict[int, set[str]] = {w: set() for w in range(1, WEEKS + 1)}
    played: set[frozenset[str]] = set()

    # Conference backbone: round i of every conference shares week LEAD+i+1.
    for conf, teams in sorted(by_conf.items()):
        if len(teams) < 2:
            continue
        rounds = _circle_rounds(teams, make_rng(seed, year, "conf", conf))
        for i in range(min(CONF_WEEKS, len(rounds))):
            w = LEAD + i + 1
            for a, b in rounds[i]:
                home, away = (a, b) if i % 2 == 0 else (b, a)
                week_games[w].append({"week": w, "home": home, "away": away,
                                      "conference": True, "neutral": False})
                matched[w].update((a, b))
                played.add(frozenset((a, b)))

    # Non-conference fill: pair the teams left open each week.
    for w in range(1, WEEKS + 1):
        rng = make_rng(seed, year, "nonconf", w)
        open_teams = [t for t in all_teams if t not in matched[w]]
        rng.shuffle(open_teams)
        used: set[str] = set()
        for idx, a in enumerate(open_teams):
            if a in used:
                continue
            partner = _pick_partner(a, open_teams[idx + 1:], used, played, universe)
            if partner is None:
                continue  # odd team out -> byes this week
            used.update((a, partner))
            played.add(frozenset((a, partner)))
            home, away = (a, partner) if rng.random() < 0.5 else (partner, a)
            week_games[w].append({"week": w, "home": home, "away": away,
                                  "conference": False, "neutral": False})

    schedule: list[dict[str, Any]] = []
    for w in range(1, WEEKS + 1):
        schedule.extend(week_games[w])
    return schedule


def _pick_partner(a: str, candidates: list[str], used: set[str],
                  played: set[frozenset[str]], universe: dict[str, dict[str, Any]]) -> str | None:
    """Best available opponent: fresh + cross-conference, then fresh, then any."""
    a_conf = universe[a].get("conference")
    fresh_cross = fresh_any = any_open = None
    for b in candidates:
        if b in used:
            continue
        if any_open is None:
            any_open = b
        rematch = frozenset((a, b)) in played
        if not rematch and fresh_any is None:
            fresh_any = b
        if not rematch and universe[b].get("conference") != a_conf:
            fresh_cross = b
            break
    return fresh_cross or fresh_any or any_open
