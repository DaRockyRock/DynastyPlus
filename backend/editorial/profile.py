"""Model capability profiles: scale the engine's ambitions to the user's model.

The editorial engine must produce the same true universe on any model (or none).
What scales is how much of the rundown gets LLM prose, how big the briefs are,
and how large the social cascades run. The tier is derived from the connected
model's name (parameter count for local models) and refined by the measured
rolling latency in data/llm_stats.json (written by the llm module's timing hook).
"""
from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from typing import Any

from .. import config, llm_settings

_lock = threading.Lock()
_STATS_PATH = config.DATA_DIR / "llm_stats.json"


@dataclass
class ModelProfile:
    tier: str              # none | nano | small | mid | frontier
    model: str
    latency_s: float       # rolling average per call (0 = unmeasured)
    max_brief_facts: int
    max_llm_beats: int     # how many articles get a model call (rest are templated)
    workers: int           # concurrent realization calls
    cascade_scale: float   # social posts per story tier multiplier
    review_pass: bool      # the editorial-review call (mid+)
    budget_s: float        # wall-clock envelope for a week's realization


_TIERS = {
    "none":     dict(max_brief_facts=0,  max_llm_beats=0,  workers=1, cascade_scale=0.0, review_pass=False, budget_s=0),
    "nano":     dict(max_brief_facts=6,  max_llm_beats=5,  workers=2, cascade_scale=0.6, review_pass=False, budget_s=120),
    "small":    dict(max_brief_facts=9,  max_llm_beats=8,  workers=3, cascade_scale=1.0, review_pass=False, budget_s=200),
    "mid":      dict(max_brief_facts=12, max_llm_beats=14, workers=4, cascade_scale=1.4, review_pass=True,  budget_s=360),
    "frontier": dict(max_brief_facts=16, max_llm_beats=24, workers=6, cascade_scale=2.0, review_pass=True,  budget_s=150),
}

_PARAMS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*b\b", re.IGNORECASE)


def _local_tier(model: str) -> str:
    m = _PARAMS_RE.search(model or "")
    if not m:
        return "small"
    params = float(m.group(1))
    if params < 4:
        return "nano"
    if params < 16:
        return "small"
    return "mid"


def record_latency(model: str, seconds: float) -> None:
    """Rolling per-model latency, updated by llm.py after each successful call.
    Exponentially weighted so a model swap re-converges within a few calls."""
    with _lock:
        try:
            data = json.loads(_STATS_PATH.read_text(encoding="utf-8")) if _STATS_PATH.exists() else {}
        except (OSError, ValueError):
            data = {}
        row = data.get(model) or {"avg_s": seconds, "n": 0}
        row["avg_s"] = round(0.8 * float(row["avg_s"]) + 0.2 * seconds, 2)
        row["n"] = int(row["n"]) + 1
        data[model] = row
        try:
            _STATS_PATH.write_text(json.dumps(data, indent=1), encoding="utf-8")
        except OSError:
            pass


def _latency(model: str) -> float:
    try:
        data = json.loads(_STATS_PATH.read_text(encoding="utf-8"))
        return float((data.get(model) or {}).get("avg_s", 0.0))
    except (OSError, ValueError):
        return 0.0


def current() -> ModelProfile:
    """The active profile. Facts and the rundown never depend on this; only how
    much of the week gets model prose (vs the template renderer) does."""
    if not llm_settings.use_llm():
        return ModelProfile(tier="none", model="", latency_s=0.0, **_TIERS["none"])
    model = llm_settings.model() or ""
    tier = "frontier" if llm_settings.provider() == "anthropic" else _local_tier(model)
    return ModelProfile(tier=tier, model=model, latency_s=_latency(model), **_TIERS[tier])
