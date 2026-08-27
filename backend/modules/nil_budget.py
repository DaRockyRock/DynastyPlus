"""NIL / Dynasty Blueprint narrative module.

The hard numbers (Dynasty Points, NIL pools, recruiting hours, per-prospect
offers) come live + uncached from budget.py via the /api/budget routes. This
module supplies only the *prose* layer for the NIL hub: a blueprint overview
and recruiting/roster analysis. Numbers are read from the budget snapshot so
the writing is grounded, but the LLM never invents the money.
"""
from __future__ import annotations

from typing import Any

from .. import budget, llm, progress
from . import base

MODULE = "nil_budget"

SYSTEM = (
    "You are the general manager's desk for a college football program, writing "
    "a short, grounded NIL and budget briefing (a 'Dynasty Blueprint'). Use the "
    "exact figures provided. Plain, confident front-office voice. No hype, no "
    "dashes as punctuation, no emojis."
)


def _money(n: int) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"${round(n / 1_000)}K"
    return f"${n}"


def _mock(dynasty: dict, snap: dict) -> dict[str, Any]:
    dp = snap["dynasty_points"]
    rec = snap["nil"]["recruiting"]
    ros = snap["nil"]["roster"]
    team = dynasty["team"]["name"]

    top_target = max(snap["recruiting_nil"], key=lambda r: (not r["committed"], r["stars"] or 0, r["interest"]), default=None)
    top_risk = max(snap["roster_nil"], key=lambda r: r["risk_of_leaving"], default=None)

    summary = (
        f"{team} carries {dp['total']} Dynasty Points this season with "
        f"{dp['available']} available after coaching staff, facilities, and "
        f"locked-in NIL. The recruiting war chest sits at {_money(rec['available'])} "
        f"of {_money(rec['pool'])}, with {_money(ros['available'])} of "
        f"{_money(ros['pool'])} left to keep the current room together."
    )
    blueprint_strategy = (
        "Blueprint leans win-now: protect the core, spend into the trenches and "
        "skill on the trail, and hold a reserve for a closing push at signing day."
    )
    recruiting_analysis = (
        f"The board still has room to make a statement offer. "
        + (f"{top_target['name']} ({top_target['stars']}-star {top_target['position']}) is the swing piece, "
           f"expecting around {_money(top_target['expected_nil'])}." if top_target else "")
    )
    roster_analysis = (
        (f"{top_risk['name']} is the retention flag at {top_risk['risk_of_leaving']}/100 risk; "
         f"a bump toward {_money(top_risk['expected_nil'])} settles it." if top_risk else "")
    )
    return {
        "summary": summary,
        "blueprint_strategy": blueprint_strategy,
        "recruiting_analysis": recruiting_analysis,
        "roster_analysis": roster_analysis,
    }


def _prompt(dynasty: dict, snap: dict) -> str:
    import json
    return (
        "Write a Dynasty Blueprint briefing as STRICT JSON with keys "
        '"summary", "blueprint_strategy", "recruiting_analysis", "roster_analysis" '
        "(each 1-3 sentences). Use these exact figures and do not invent others.\n\n"
        f"BUDGET SNAPSHOT:\n{json.dumps(snap, indent=2)}\n\nJSON only."
    )


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    progress.set_sub_step("NIL budget analysis")
    snap = dynasty.get("budget") or budget.snapshot(year, week, dynasty)
    # The NIL/budget panel is a deterministic numbers view built straight from the
    # snapshot. The LLM only ever contributed a flavor "summary" line, and on a small
    # local model it reliably failed to return valid JSON, burning ~40s per retry
    # (160s+ total) before falling back to this same mock. So build it directly, no
    # model call: it is the same output, far faster.
    data = _mock(dynasty, snap)
    return base.sanitize(dict(data, module=MODULE, source="mock"))
