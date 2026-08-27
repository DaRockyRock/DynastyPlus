"""Salience scoring and seeded slate selection.

Signals are z-score normalized ACROSS THE WEEK'S POOL (so no raw scale can
dominate), combined as a weighted sum with one representative per correlated
concept, then selected greedily with Maximal Marginal Relevance so the slate
stays varied (no three near-identical recruit stories). All tie-breaking jitter
draws from a seed of (dynasty-stable inputs), so the same save always produces
the same rundown: beat ids, cascade dedup keys, and re-scans depend on that.
"""
from __future__ import annotations

import math
import random
from typing import Sequence

from .candidates import StoryCandidate

# One weight per signal CONCEPT. surprise/magnitude/stakes overlap is handled by
# the detectors emitting at most the signals that genuinely apply, and by MMR
# downstream; do not add is_upset-style booleans on top of surprise.
WEIGHTS = {
    "surprise": 1.00,
    "magnitude": 0.80,
    "stakes": 0.90,
    "conflict": 0.60,
    "eliteness": 0.60,
    "proximity": 0.70,
    "follow_up": 0.80,
    "goodness": 0.40,
}

MMR_LAMBDA = 0.7   # 1.0 = pure score, lower = more diversity pressure


def _normalize(pool: Sequence[StoryCandidate]) -> None:
    """Z-score each signal across the pool, clip to [-3, 3], map to [0, 1].
    A signal absent from a candidate contributes nothing (not a penalty)."""
    keys = {k for c in pool for k in c.signals}
    for k in keys:
        vals = [c.signals[k] for c in pool if k in c.signals]
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        sd = math.sqrt(var)
        for c in pool:
            if k in c.signals:
                z = (c.signals[k] - mean) / sd if sd > 1e-9 else 0.0
                c.signals[k] = (max(-3.0, min(3.0, z)) + 3.0) / 6.0


def _similarity(a: StoryCandidate, b: StoryCandidate) -> float:
    """Subject/type overlap for the diversity penalty."""
    sa = set(a.subjects) | {a.type}
    sb = set(b.subjects) | {b.type}
    inter = len(sa & sb)
    union = len(sa | sb) or 1
    return inter / union


def score(pool: list[StoryCandidate], *, seed: str) -> list[StoryCandidate]:
    """Score the pool in place and return it sorted best-first (deterministic)."""
    _normalize(pool)
    rng = random.Random(seed)
    for c in pool:
        c.score = sum(WEIGHTS.get(k, 0.3) * v for k, v in c.signals.items())
        c.score += rng.random() * 1e-6        # seeded tie-break only
    pool.sort(key=lambda c: -c.score)
    return pool


def select(pool: list[StoryCandidate], k: int, *, scope: str | None = None) -> list[StoryCandidate]:
    """Greedy MMR over an already-scored pool: pick the best, then penalize
    near-duplicates of what is chosen. Deterministic given the scored order."""
    cands = [c for c in pool if scope is None or c.scope == scope]
    chosen: list[StoryCandidate] = []
    while cands and len(chosen) < k:
        best, best_val = None, -1e9
        for c in cands:
            penalty = max((_similarity(c, p) for p in chosen), default=0.0)
            val = MMR_LAMBDA * c.score - (1.0 - MMR_LAMBDA) * penalty
            if val > best_val:
                best, best_val = c, val
        chosen.append(best)
        cands.remove(best)
    return chosen
