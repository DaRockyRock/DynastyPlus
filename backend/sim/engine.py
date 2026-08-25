"""Single-game score model.

Given two team ratings (0-100 program-strength numbers from the league seed,
jittered per season in league.py), produce a final score. The model is a margin
plus total construction: the expected margin scales with the rating gap and a
home-field edge, actual margin and total are sampled with normal noise so upsets
emerge naturally, and the two scores are recovered and rounded to whole points.

Every random draw runs through make_rng, seeded from the stable game key
(master seed, year, week, home, away). Re-simulating a week therefore yields the
exact same scores, which keeps week navigation and regeneration idempotent the
same way the static mock is deterministic per week.
"""
from __future__ import annotations

import hashlib
import random

# Points of margin per rating point. A 20-point rating edge is ~14 points.
MARGIN_PER_RATING = 0.7
HOME_FIELD = 2.4          # points of home-field advantage
MARGIN_STDEV = 12.5       # spread of actual vs expected margin (drives upsets)
BASE_TOTAL = 52.0         # league-average combined points
TOTAL_STDEV = 9.0
TOTAL_PER_RATING = 0.15   # better teams play higher-scoring games


def make_rng(*parts: object) -> random.Random:
    """A random.Random seeded deterministically from the given parts."""
    key = "|".join(str(p) for p in parts)
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def simulate_game(home_rating: float, away_rating: float, rng: random.Random,
                  *, neutral: bool = False) -> tuple[int, int]:
    """Return (home_points, away_points). Never a tie (overtime is resolved)."""
    hfa = 0.0 if neutral else HOME_FIELD
    exp_margin = (home_rating - away_rating) * MARGIN_PER_RATING + hfa
    margin = rng.gauss(exp_margin, MARGIN_STDEV)

    avg_rating = (home_rating + away_rating) / 2
    total = rng.gauss(BASE_TOTAL + (avg_rating - 65) * TOTAL_PER_RATING, TOTAL_STDEV)
    total = max(20.0, total)

    home = max(0, round((total + margin) / 2))
    away = max(0, round((total - margin) / 2))

    if home == away:
        # Overtime: the favored side (by sampled margin) gets a field goal or TD.
        bump = 3 if rng.random() < 0.5 else 7
        if margin >= 0:
            home += bump
        else:
            away += bump
    return home, away
