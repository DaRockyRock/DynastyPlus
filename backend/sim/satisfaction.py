"""Player satisfaction / retention model (Simulator-owned).

CFB27 ships every player with wants and a satisfaction that drives whether he
stays or hits the transfer portal. The Simulator stands in for that here: this
module turns the real season context (a player's depth-chart role, the team's
results against its prestige expectation, his class/draft outlook, the national
profile of the program, and how hot the head coach's seat is) into a live
0-100 ``risk_of_leaving`` plus a short human reason.

It REPLACES the random retention seed roster_gen.py stamps. The NIL factor stays
where it already lives (budget.adjusted_risk layers the pay-vs-expectation gap on
top in budget.snapshot), so this computes the pre-NIL baseline and there is no
double counting.

Each player's ``dealbreaker`` (one of customization_base.DEALBREAKERS) is the
"want" the game programs into him: it reweights the factors so a Playing Time guy
runs hot when buried while a Championship Culture guy runs hot when the team is
losing. The result is a pure, deterministic function of the inputs (seeded via
engine.make_rng), so it never churns the save's meta.hash.

Leaf module: standard library + engine.make_rng only (no customization / sim
state imports), so both the adapter and the portal engine can call it freely.
"""
from __future__ import annotations

from typing import Any

from .engine import make_rng

# Weight (in games) of a player's preseason expectation, so a tiny sample does
# not swing the team-performance factor. Mirrors coaches.hot_seat_heat.
_PRIOR_GAMES = 6

# Factor weights per "want". Keys: pt (playing time / depth), tp (team
# performance), cd (class / draft pull), br (program national profile), coach
# (head-coach job security). Each row sums to ~1.0; the default applies when a
# player has no recognized dealbreaker.
_DEFAULT_WEIGHTS = {"pt": 0.40, "tp": 0.25, "cd": 0.20, "br": 0.15, "coach": 0.00}
_WANT_WEIGHTS: dict[str, dict[str, float]] = {
    "Playing Time":         {"pt": 0.62, "tp": 0.14, "cd": 0.14, "br": 0.10, "coach": 0.00},
    "Championship Culture": {"pt": 0.22, "tp": 0.52, "cd": 0.14, "br": 0.12, "coach": 0.00},
    "NFL Readiness":        {"pt": 0.20, "tp": 0.22, "cd": 0.46, "br": 0.12, "coach": 0.00},
    "Development":          {"pt": 0.40, "tp": 0.16, "cd": 0.30, "br": 0.14, "coach": 0.00},
    "Brand Exposure":       {"pt": 0.20, "tp": 0.24, "cd": 0.10, "br": 0.46, "coach": 0.00},
    "Proximity to Home":    {"pt": 0.34, "tp": 0.24, "cd": 0.22, "br": 0.20, "coach": 0.00},
    "Coaching Stability":   {"pt": 0.18, "tp": 0.25, "cd": 0.12, "br": 0.00, "coach": 0.45},
}
# A location-driven want makes a player less reactive to on-field swings overall.
_WANT_DAMPEN = {"Proximity to Home": 0.85}

_YEAR_BASE = {"FR": 0.10, "SO": 0.12, "JR": 0.16, "SR": 0.30, "GR": 0.30}


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _wl(record: Any) -> tuple[int, int]:
    try:
        w, l = str((record or {}).get("overall", "0-0")).split("-")[:2]
        return int(w), int(l)
    except (ValueError, AttributeError):
        return 0, 0


def _expected_win_rate(prestige: int) -> float:
    """A program's expected win rate from its prestige (1 cupcake .. 10 blue blood),
    matching the hot-seat model so a roster and its coach read the season the same
    way."""
    p = max(1, min(10, prestige or 5))
    return 0.30 + (p - 1) / 9 * 0.55  # 0.30 .. 0.85


def _team_pressure(record: Any, prestige: int) -> float:
    """0-1 pressure from the team underperforming its prestige expectation. Shrunk
    toward the expectation by a few prior games so an early loss does not spike the
    whole roster; a sustained slide does. Winning pushes it below baseline."""
    expected = _expected_win_rate(prestige)
    w, l = _wl(record)
    games = w + l
    blended = (w + expected * _PRIOR_GAMES) / (games + _PRIOR_GAMES)
    gap = expected - blended  # positive => underperforming
    return _clamp(0.35 + gap * 1.3, 0.02, 0.95)


def _depth(players: list[dict[str, Any]]) -> dict[int, float]:
    """Playing-time pressure per player (keyed by id()). A starter is content; a
    backup is restless; a reserve more so, and a highly rated player stuck behind
    someone runs hotter (talent that is not playing wants out)."""
    out: dict[int, float] = {}
    for p in players:
        slot = str(p.get("depth_chart_slot") or "")
        rating = int(p.get("rating", 70) or 70)
        if slot.startswith("Starting"):
            base, buried = 0.05, 0.0
        elif slot.startswith("Backup"):
            base = 0.45
            buried = _clamp((rating - 78) / 40, 0.0, 0.30)
        else:  # Reserve / unknown
            base = 0.60
            buried = _clamp((rating - 78) / 40, 0.0, 0.30)
        out[id(p)] = _clamp(base + buried, 0.0, 1.0)
    return out


def _class_draft_pressure(player: dict[str, Any]) -> float:
    """0-1 standing pull from class + draft outlook: veterans weigh a final-year
    move, and high draft stock pulls toward the next level."""
    base = _YEAR_BASE.get(str(player.get("year") or ""), 0.15)
    stock = str(player.get("draft_stock") or "").lower()
    if any(k in stock for k in ("round 1", "top-15", "top 15")):
        base += 0.35
    elif stock:
        base += 0.18
    return _clamp(base, 0.0, 1.0)


def _brand_pressure(ap_rank: int | None) -> float:
    """0-1 pressure from the program's national profile. An unranked program leaves
    a brand-minded player restless; a top-10 program satisfies him."""
    if ap_rank is None:
        return 0.55
    if ap_rank <= 10:
        return 0.15
    if ap_rank <= 25:
        return 0.32
    return 0.40


def _coach_pressure(coach_hot_seat: int | None) -> float:
    """0-1 pressure from the head coach's job security (a hot seat unsettles a
    stability-minded player)."""
    if coach_hot_seat is None:
        return 0.25
    return _clamp((int(coach_hot_seat) - 40) / 80, 0.0, 0.70)


_REASONS = {
    "pt_high": "Buried on the depth chart and itching for snaps.",
    "pt_low": "Locked into his role, no reason to look around.",
    "tp_high": "Frustrated with the way the season is going.",
    "tp_low": "Bought into where the program is headed.",
    "cd_high": "Has one eye on the next level.",
    "cd_vet": "A veteran weighing a final-year move.",
    "br_high": "Wants a brighter national stage than this.",
    "coach_high": "Uneasy about the staff's job security.",
    "content": "Content and comfortable in the program.",
}


def _reason(player: dict[str, Any], comps: dict[str, float], weights: dict[str, float], risk: int) -> str:
    if risk < 18:
        return _REASONS["content"]
    # The factor contributing the most to the score (weight * pressure).
    dominant = max(comps, key=lambda k: weights.get(k, 0.0) * comps[k])
    val = comps[dominant]
    if dominant == "pt":
        return _REASONS["pt_high"] if val >= 0.4 else _REASONS["pt_low"]
    if dominant == "tp":
        return _REASONS["tp_high"] if val >= 0.45 else _REASONS["tp_low"]
    if dominant == "cd":
        return _REASONS["cd_vet"] if str(player.get("year")) in ("SR", "GR") else _REASONS["cd_high"]
    if dominant == "br":
        return _REASONS["br_high"]
    if dominant == "coach":
        return _REASONS["coach_high"]
    return _REASONS["content"]


def compute(players: list[dict[str, Any]], *, record: Any, prestige: int,
            ap_rank: int | None, week: int, weeks_total: int, seed: int | str,
            coach_hot_seat: int | None = None) -> list[dict[str, Any]]:
    """Return NEW player dicts with ``risk_of_leaving`` (0-100) and ``risk_reason``
    recomputed from the live season context. Pure + deterministic for a given
    (players, record, prestige, ap_rank, seed)."""
    players = players or []
    depth = _depth(players)
    tp = _team_pressure(record, prestige)
    br = _brand_pressure(ap_rank)
    coach = _coach_pressure(coach_hot_seat)

    out: list[dict[str, Any]] = []
    for p in players:
        comps = {
            "pt": depth.get(id(p), 0.45),
            "tp": tp,
            "cd": _class_draft_pressure(p),
            "br": br,
            "coach": coach,
        }
        want = str(p.get("dealbreaker") or "")
        weights = _WANT_WEIGHTS.get(want, _DEFAULT_WEIGHTS)
        raw = sum(weights.get(k, 0.0) * v for k, v in comps.items())
        raw *= _WANT_DAMPEN.get(want, 1.0)
        # A small, name-seeded wobble so identical profiles are not pixel-identical.
        jitter = make_rng(seed, "satisfaction", p.get("name", "")).uniform(-4, 4)
        risk = int(_clamp(round(raw * 100 + jitter), 2, 99))
        q = dict(p)
        q["risk_of_leaving"] = risk
        q["risk_reason"] = _reason(p, comps, weights, risk)
        out.append(q)
    return out
