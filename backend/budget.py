"""NIL and Dynasty Points budget engine.

This is the source of truth for everything the coach (the user) actively spends:
Dynasty Points allocation, NIL offers to recruits and roster players, and the
weekly recruiting hours poured into prospects. It overlays the deterministic
season state so a $250k offer made in Week 10 persists across reloads.

CFB 27 model (see CLAUDE.md / EA deep dive), built out as documented
assumptions until the save format is readable:

  - Dynasty Points (DP) are the annual program budget, split across coaching
    staff / facilities / NIL. Offering NIL immediately draws DP from your
    available balance (DP_PER_DOLLAR conversion).
  - Recruiting NIL: offer up to 2x a prospect's expected amount for the biggest
    weekly influence bonus; below expected hurts; an offer establishes a floor,
    and cutting back below that floor is part of why a recruit may leave.
  - Roster NIL: per-player pay tied to a risk-of-leaving meter.
  - Weekly recruiting hours are spent on actions ("Send the House", visits, ...).

All money math and simulation lives here so the numbers remain exact. State is
stored as one JSON document per season at data/budget/<year>.json.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from typing import Any

from . import config

# Recruitment funnel, low to high momentum.
STAGES = ["Open", "Top 5", "Top 3", "Verbal", "Hard Commit"]

# Weekly recruiting actions. hours = cost from the weekly pool; influence = the
# momentum bump applied to the prospect's interest. Modeled on the CFB 25 board
# (the deep dive mentions weekly hours but does not quantify them) - tune freely.
RECRUITING_ACTIONS = [
    {"key": "send_the_house", "label": "Send the House", "hours": 600, "influence": 18,
     "blurb": "Full staff blitz - the biggest weekly swing you can make"},
    {"key": "schedule_visit", "label": "Set Up a Visit", "hours": 250, "influence": 11,
     "blurb": "Get the prospect on campus for a gameday"},
    {"key": "hard_sell", "label": "Hard Sell a Pitch", "hours": 250, "influence": 10,
     "blurb": "Pitch a program strength head-on"},
    {"key": "head_coach_visit", "label": "Head Coach Visit", "hours": 200, "influence": 9,
     "blurb": "You make the in-home visit personally"},
    {"key": "coordinator_visit", "label": "Coordinator Visit", "hours": 150, "influence": 7,
     "blurb": "Send a coordinator or position coach"},
    {"key": "send_dm", "label": "Send a DM", "hours": 75, "influence": 3,
     "blurb": "Low-cost touch to keep the relationship warm"},
]
_ACTION_BY_KEY = {a["key"]: a for a in RECRUITING_ACTIONS}


# --- persistence ----------------------------------------------------------
def _path(year: int):
    return config.BUDGET_DIR / f"{year}.json"


def _empty(year: int) -> dict[str, Any]:
    return {
        "year": year,
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        # null = use the dynasty baseline allocation
        "allocations": None,
        # entity_id -> {"amount": int, "floor": int}  (recruiting NIL offers)
        "recruit_offers": {},
        # entity_id -> int dollars  (roster NIL pay overrides)
        "player_pay": {},
        # entity_id -> int  (interest override, otherwise the baseline)
        "interest": {},
        # entity_id -> str  (stage override)
        "stage": {},
        # "<year>_wk<NN>" -> int hours spent that week
        "hours": {},
        # entity_id -> {"<year>_wk<NN>": ["action_key", ...]}
        "actions": {},
    }


def load(year: int) -> dict[str, Any]:
    path = _path(year)
    if not path.exists():
        return _empty(year)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        base = _empty(year)
        base.update(data)
        return base
    except (OSError, ValueError):
        return _empty(year)


def save(state: dict[str, Any]) -> None:
    try:
        with _path(state.get("year")).open("w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
    except OSError:
        pass


# --- helpers --------------------------------------------------------------
def entity_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def _wk(year: int, week: int) -> str:
    return f"{year}_wk{int(week):02d}"


def _clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def _nil_base(dynasty: dict) -> dict[str, Any]:
    nil = dynasty.get("nil") or {}
    dp = nil.get("dynasty_points") or {}
    return {
        "total": int(dp.get("total", 12000)),
        "allocations": dict(dp.get("allocations", {"coaching_staff": 3800, "facilities": 4000, "nil": 4200})),
        "recruiting_pool": int(nil.get("recruiting_pool", 5500000)),
        "roster_pool": int(nil.get("roster_pool", 5000000)),
        "weekly_recruiting_hours": int(nil.get("weekly_recruiting_hours", config.WEEKLY_RECRUITING_HOURS)),
        "dp_per_dollar": float(nil.get("dp_per_dollar", config.DP_PER_DOLLAR)),
    }


def stage_for_interest(interest: int) -> str:
    if interest >= 92:
        return "Hard Commit"
    if interest >= 75:
        return "Verbal"
    if interest >= 55:
        return "Top 3"
    if interest >= 35:
        return "Top 5"
    return "Open"


def influence_from_offer(amount: int, expected: int) -> int:
    """Weekly influence from a recruiting NIL offer relative to expected.

    0x -> -10, 1x -> +4, 2x and up -> +12 (the biggest weekly bonus).
    """
    if expected <= 0:
        return 0
    r = amount / expected
    if r <= 1:
        return round(-10 + 14 * r)
    if r >= 2:
        return 12
    return round(4 + 8 * (r - 1))


def adjusted_risk(baseline_risk: int, current_pay: int, expected: int) -> int:
    """Roster risk-of-leaving adjusted for pay vs expectation.

    Paying at expectation leaves the baseline; +50% over cuts risk ~20, and
    paying under expectation raises it.
    """
    if expected <= 0:
        return int(baseline_risk)
    delta = round((expected - current_pay) / expected * 40)
    return int(_clamp(baseline_risk + delta, 2, 99))


def _recruits(dynasty: dict) -> list[tuple[dict, bool]]:
    """All recruiting entities as (record, committed)."""
    rec = dynasty.get("recruiting", {})
    out = [(c, True) for c in rec.get("commits", [])]
    out += [(t, False) for t in rec.get("targets", [])]
    return out


def _find_recruit(dynasty: dict, eid: str) -> tuple[dict | None, bool]:
    for r, committed in _recruits(dynasty):
        if entity_id(r["name"]) == eid:
            return r, committed
    return None, False


def _find_player(dynasty: dict, eid: str) -> dict | None:
    for p in dynasty.get("roster", {}).get("key_players", []):
        if entity_id(p["name"]) == eid:
            return p
    return None


# --- snapshot -------------------------------------------------------------
def snapshot(year: int, week: int, dynasty: dict) -> dict[str, Any]:
    """Live numeric budget snapshot, merging the mock baseline + stored edits."""
    st = load(year)
    base = _nil_base(dynasty)
    dpd = base["dp_per_dollar"]
    allocations = st.get("allocations") or base["allocations"]

    # Recruiting NIL rows (targets + commits).
    recruiting_rows: list[dict[str, Any]] = []
    for r, committed in _recruits(dynasty):
        eid = entity_id(r["name"])
        offer = st["recruit_offers"].get(eid, {})
        interest = int(st["interest"].get(eid, r.get("interest", 0)))
        stage = st["stage"].get(eid) or r.get("stage") or stage_for_interest(interest)
        recruiting_rows.append({
            "id": eid,
            "name": r["name"],
            "position": r.get("position"),
            "stars": r.get("stars"),
            "expected_nil": int(r.get("expected_nil", 0)),
            "offer": int(offer.get("amount", 0)),
            "floor": int(offer.get("floor", 0)),
            "interest": interest,
            "stage": stage,
            "dealbreaker": r.get("dealbreaker"),
            "leader": r.get("leader"),
            "predicted": r.get("predicted"),
            "committed": committed,
        })
    recruiting_committed = sum(row["offer"] for row in recruiting_rows)

    # Roster NIL rows.
    roster_rows: list[dict[str, Any]] = []
    for p in dynasty.get("roster", {}).get("key_players", []):
        eid = entity_id(p["name"])
        expected = int(p.get("expected_nil", 0))
        current = int(st["player_pay"].get(eid, p.get("current_nil", 0)))
        roster_rows.append({
            "id": eid,
            "name": p["name"],
            "position": p.get("position"),
            "year": p.get("year"),
            "depth_chart_slot": p.get("depth_chart_slot"),
            "expected_nil": expected,
            "current_nil": current,
            "risk_of_leaving": adjusted_risk(int(p.get("risk_of_leaving", 20)), current, expected),
            "dealbreaker": p.get("dealbreaker"),
        })
    roster_committed = sum(row["current_nil"] for row in roster_rows)

    nil_committed_dollars = recruiting_committed + roster_committed
    nil_committed_dp = round(nil_committed_dollars * dpd)
    committed_dp = {
        "coaching_staff": int(allocations.get("coaching_staff", 0)),
        "facilities": int(allocations.get("facilities", 0)),
        "nil": nil_committed_dp,
    }
    total_dp = base["total"]
    available_dp = total_dp - sum(committed_dp.values())

    hours_total = base["weekly_recruiting_hours"]
    hours_spent = int(st["hours"].get(_wk(year, week), 0))

    return {
        "year": year,
        "week": week,
        "dp_per_dollar": dpd,
        "dynasty_points": {
            "total": total_dp,
            "available": available_dp,
            "allocations": allocations,
            "committed": committed_dp,
        },
        "nil": {
            "recruiting": {
                "pool": base["recruiting_pool"],
                "committed": recruiting_committed,
                "available": base["recruiting_pool"] - recruiting_committed,
            },
            "roster": {
                "pool": base["roster_pool"],
                "committed": roster_committed,
                "available": base["roster_pool"] - roster_committed,
            },
        },
        "recruiting_hours": {
            "total": hours_total,
            "spent": hours_spent,
            "remaining": hours_total - hours_spent,
        },
        "recruiting_nil": recruiting_rows,
        "roster_nil": roster_rows,
        "actions": RECRUITING_ACTIONS,
        "stages": STAGES,
    }


# --- mutations ------------------------------------------------------------
def set_allocation(year: int, week: int, allocations: dict, dynasty: dict) -> dict[str, Any]:
    """Set the Dynasty Points allocation across the three categories."""
    base = _nil_base(dynasty)
    cleaned = {
        "coaching_staff": max(0, int(allocations.get("coaching_staff", base["allocations"]["coaching_staff"]))),
        "facilities": max(0, int(allocations.get("facilities", base["allocations"]["facilities"]))),
        "nil": max(0, int(allocations.get("nil", base["allocations"]["nil"]))),
    }
    total = base["total"]
    over = sum(cleaned.values()) > total
    st = load(year)
    st["allocations"] = cleaned
    save(st)
    snap = snapshot(year, week, dynasty)
    return {
        "snapshot": snap,
        "effect": {
            "kind": "allocate",
            "allocations": cleaned,
            "over_budget": over,
            "message": "Allocation updated" + (" (over total budget)" if over else ""),
        },
    }


def set_nil_offer(year: int, week: int, eid: str, kind: str, amount: int, dynasty: dict) -> dict[str, Any]:
    """Make or adjust an NIL offer. kind is 'recruit' or 'player'."""
    st = load(year)
    base = _nil_base(dynasty)
    dpd = base["dp_per_dollar"]
    amount = max(0, int(amount))

    if kind == "player":
        player = _find_player(dynasty, eid)
        if not player:
            return {"error": "unknown player"}
        expected = int(player.get("expected_nil", 0))
        amount = int(_clamp(amount, 0, expected * 2 if expected else amount))
        prev = int(st["player_pay"].get(eid, player.get("current_nil", 0)))
        st["player_pay"][eid] = amount
        save(st)
        snap = snapshot(year, week, dynasty)
        risk = adjusted_risk(int(player.get("risk_of_leaving", 20)), amount, expected)
        effect = {
            "kind": "nil_offer",
            "entity_kind": "player",
            "id": eid,
            "name": player["name"],
            "amount": amount,
            "expected": expected,
            "dp_cost": round((amount - prev) * dpd),
            "risk_of_leaving": risk,
            "message": _player_offer_message(player["name"], amount, expected, risk),
        }
        return {"snapshot": snap, "effect": effect}

    # recruit
    recruit, committed = _find_recruit(dynasty, eid)
    if not recruit:
        return {"error": "unknown recruit"}
    expected = int(recruit.get("expected_nil", 0))
    amount = int(_clamp(amount, 0, expected * 2 if expected else amount))
    prev = st["recruit_offers"].get(eid, {})
    prev_amount = int(prev.get("amount", 0))
    prev_floor = int(prev.get("floor", 0))
    floor = max(prev_floor, amount)  # offering up sets a new floor

    influence = influence_from_offer(amount, expected)
    # cutting below an established floor is part of why a recruit may leave
    if amount < prev_floor and expected:
        influence -= round((prev_floor - amount) / expected * 8)

    base_interest = int(st["interest"].get(eid, recruit.get("interest", 0)))
    new_interest = int(_clamp(base_interest + influence, 0, 100))
    new_stage = stage_for_interest(new_interest)

    st["recruit_offers"][eid] = {"amount": amount, "floor": floor}
    st["interest"][eid] = new_interest
    st["stage"][eid] = new_stage
    save(st)

    snap = snapshot(year, week, dynasty)
    effect = {
        "kind": "nil_offer",
        "entity_kind": "recruit",
        "id": eid,
        "name": recruit["name"],
        "amount": amount,
        "expected": expected,
        "floor": floor,
        "dp_cost": round((amount - prev_amount) * dpd),
        "influence_delta": influence,
        "interest": new_interest,
        "stage": new_stage,
        "over_budget": snap["nil"]["recruiting"]["available"] < 0,
        # Whether this offer crossed the recruit's expected value for the first time.
        "crossed_expected": bool(amount >= expected and amount > prev_amount and expected),
        "message": _recruit_offer_message(recruit["name"], amount, expected, influence, new_stage),
    }
    return {"snapshot": snap, "effect": effect}


def spend_recruiting_action(year: int, week: int, eid: str, action_key: str, dynasty: dict) -> dict[str, Any]:
    """Spend weekly recruiting hours on a prospect via an action."""
    action = _ACTION_BY_KEY.get(action_key)
    if not action:
        return {"error": "unknown action"}
    recruit, committed = _find_recruit(dynasty, eid)
    if not recruit:
        return {"error": "unknown recruit"}

    st = load(year)
    base = _nil_base(dynasty)
    wk = _wk(year, week)
    spent = int(st["hours"].get(wk, 0))
    remaining = base["weekly_recruiting_hours"] - spent

    if remaining < action["hours"]:
        snap = snapshot(year, week, dynasty)
        return {"snapshot": snap, "effect": {
            "kind": "recruiting_action", "ok": False, "id": eid, "name": recruit["name"],
            "action_label": action["label"], "hours": action["hours"], "remaining": remaining,
            "message": f"Not enough recruiting hours left this week ({remaining} of {action['hours']} needed).",
        }}

    st["hours"][wk] = spent + action["hours"]
    st["actions"].setdefault(eid, {}).setdefault(wk, []).append(action_key)

    influence = action["influence"]
    base_interest = int(st["interest"].get(eid, recruit.get("interest", 0)))
    new_interest = int(_clamp(base_interest + influence, 0, 100))
    new_stage = stage_for_interest(new_interest)
    st["interest"][eid] = new_interest
    st["stage"][eid] = new_stage
    save(st)

    snap = snapshot(year, week, dynasty)
    effect = {
        "kind": "recruiting_action",
        "ok": True,
        "id": eid,
        "name": recruit["name"],
        "action_key": action_key,
        "action_label": action["label"],
        "hours": action["hours"],
        "remaining": snap["recruiting_hours"]["remaining"],
        "influence_delta": influence,
        "interest": new_interest,
        "stage": new_stage,
        "message": _action_message(recruit["name"], action["label"], influence, new_stage),
    }
    return {"snapshot": snap, "effect": effect}


# --- user-facing result messages ------------------------------------------
def _short(n: int) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{round(n / 1_000)}K"
    return str(n)


def _recruit_offer_message(name: str, amount: int, expected: int, influence: int, stage: str) -> str:
    tier = "way over" if amount >= expected * 2 and expected else "above" if amount >= expected else "below"
    if amount == 0:
        return f"You pulled your NIL offer to {name}. Influence {influence:+d}."
    return (f"You offered {name} ${_short(amount)}/yr ({tier} their ${_short(expected)} expectation). "
            f"Influence {influence:+d}, now at {stage}.")


def _player_offer_message(name: str, amount: int, expected: int, risk: int) -> str:
    return (f"You set {name}'s NIL at ${_short(amount)}/yr (expects ${_short(expected)}). "
            f"Risk of leaving {risk}/100.")


def _action_message(name: str, label: str, influence: int, stage: str) -> str:
    return f"You spent recruiting hours on {name}: {label}. Influence {influence:+d}, now at {stage}."
