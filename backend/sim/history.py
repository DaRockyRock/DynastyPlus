"""Program history (prior seasons) for a dynasty.

CFB 27 stores a program's full history. We model that here: when a dynasty
starts, the Simulator generates the program's recent seasons (records, conference
finish, final ranking, postseason result, and who coached) so the companion has
real "last year's results" and a grounded coaching-change story on day one. The
most recent `tenure_years - 1` seasons are attributed to the user's coach; the
earlier ones to the predecessor (named in the program blueprint, or generated).

Deterministic from the season seed so the same dynasty always has the same past.
Persisted inside the season state (state.py) and projected into the save by the
adapter, so Dynasty+ reads it from the dynasty dict like everything else.
"""
from __future__ import annotations

import random
from typing import Any

# Fictional coach names for a generated predecessor (never a real person).
_COACH_POOL = [
    "Wade Hollis", "Marcus Trent", "Gil Avery", "Dom Castellano", "Rex Manning",
    "Hal Brennan", "Cliff Dawson", "Vance Okeke", "Sal Petrino", "Brett Calloway",
    "Dane Whitlock", "Russ Oduya", "Lonnie Fairchild", "Chip Merle",
]

_BOWLS = [
    "Sun Bowl", "Music City Bowl", "Las Vegas Bowl", "Gator Bowl", "Liberty Bowl",
    "Holiday Bowl", "Pinstripe Bowl", "Duke's Mayo Bowl", "Texas Bowl", "ReliaQuest Bowl",
]
_NY6 = ["Rose Bowl", "Sugar Bowl", "Orange Bowl", "Cotton Bowl", "Fiesta Bowl", "Peach Bowl"]


def _win_pct(rating: float, rng: random.Random) -> float:
    base = 0.15 + (float(rating) - 60.0) / 45.0  # ~rating 70 -> .37, 85 -> .71, 92 -> .86
    base += rng.uniform(-0.16, 0.16)
    return max(0.05, min(0.95, base))


def _final_rank(wins: int, rng: random.Random) -> int | None:
    if wins >= 12:
        return rng.randint(1, 6)
    if wins >= 11:
        return rng.randint(4, 14)
    if wins >= 10:
        return rng.randint(10, 25)
    return None


def _postseason(wins: int) -> str:
    if wins >= 12:
        return "Reached the College Football Playoff"
    if wins >= 11:
        return f"Won a New Year's Six bowl"
    if wins >= 6:
        return "Played in a bowl game"
    return "Missed a bowl game"


def _conf_finish(wins: int) -> str:
    if wins >= 11:
        return "won the conference"
    if wins >= 9:
        return "contended in the conference"
    if wins >= 6:
        return "finished in the upper half of the conference"
    return "finished near the bottom of the conference"


def build(year: int, seed: int, universe: dict[str, Any], user_team: str,
          hc: dict[str, Any], prog: dict[str, Any], n: int = 5) -> list[dict[str, Any]]:
    """Generate the last `n` seasons of program history (most recent first)."""
    info = universe.get(user_team, {}) or {}
    rating = info.get("rating", 72)
    rng = random.Random(f"{seed}|history|{user_team}")

    tenure = int(hc.get("tenure_years") or 1)
    user_coach = hc.get("name") or "the head coach"
    user_prior_seasons = max(0, tenure - 1)  # completed seasons under the user
    prev_coach = (prog.get("previous_coach") or "").strip() or rng.choice(_COACH_POOL)

    out: list[dict[str, Any]] = []
    for i in range(1, n + 1):
        y = year - i
        srng = random.Random(f"{seed}|history|{y}")
        wins = round(_win_pct(rating, srng) * 12)
        # The predecessor's final year (right before a first-year coach takes over)
        # skews worse: it is usually why the job opened.
        is_user = i <= user_prior_seasons
        if not is_user and i == user_prior_seasons + 1 and tenure <= 1:
            wins = max(2, wins - srng.randint(2, 4))
        wins = max(0, min(12, wins))
        losses = 12 - wins
        rank = _final_rank(wins, srng)
        out.append({
            "year": y,
            "coach": user_coach if is_user else prev_coach,
            "user_coached": is_user,
            "overall": f"{wins}-{losses}",
            "wins": wins,
            "losses": losses,
            "final_rank": rank,
            "conference_finish": _conf_finish(wins),
            "postseason": (_NY6[srng.randrange(len(_NY6))] + " win" if wins >= 11
                           else (f"{_BOWLS[srng.randrange(len(_BOWLS))]}" if wins >= 6 else "")),
            "result": _postseason(wins),
        })
    return out
