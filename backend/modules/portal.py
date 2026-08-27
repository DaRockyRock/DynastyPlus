"""Transfer portal feed.

Portal entry rumors throughout the season, destination speculation, portal
class grades, and NIL-driven narratives. Grounded in the dynasty transfer
data. Scaffold with rich mock content; LLM prompt wired for later.
"""
from __future__ import annotations

from typing import Any

from .. import llm, progress
from . import base

MODULE = "portal"

SYSTEM = (
    "You are a transfer-portal desk producing entry rumors, destination "
    "speculation, class grades, and NIL-driven storylines. Ground everything in "
    "the dynasty data. Never use dashes as punctuation; use commas or periods, never dashes."
)


def _prompt(dynasty: dict) -> str:
    return (
        f"Build the transfer-portal feed for {dynasty['team']['name']} in "
        f"{dynasty['season']['week_label']}. Use the transfer_portal data. Return "
        "STRICT JSON with keys: \"rumors\" (array of {player, position, team, "
        "status, detail, confidence}), \"incoming\" (array), \"outgoing\" (array), "
        "\"targets\" (array), \"class_grade\" ({grade, gpa, summary}), "
        "\"nil_narrative\" (string). JSON only."
    )


def _grade_for(ovr: int) -> str:
    if ovr >= 88:
        return "A"
    if ovr >= 84:
        return "B+"
    if ovr >= 80:
        return "B"
    return "C+"


def _mock(dynasty: dict) -> dict[str, Any]:
    tp = dynasty.get("transfer_portal") or {}
    team = dynasty["team"]["name"]
    win = tp.get("window") or {"open": False, "label": "Closed"}

    inc = tp.get("incoming") or []
    out = tp.get("outgoing") or []
    tgt = tp.get("targets") or []

    # The portal is closed during the regular season: nothing moves, so no rumors
    # are invented. Rumors only derive from the real, sim-driven board once the
    # offseason window has opened, grounded in each player's actual interest /
    # stage / departure reason (never a fabricated depth-chart event).
    rumors = []
    if win.get("open"):
        for o in out[:3]:
            dest = o.get("to")
            detail = o.get("reason") or f"A {o['position']} has entered the transfer portal."
            if dest and dest != "Undecided":
                detail += f" Reportedly headed to {dest}."
            rumors.append({"player": o["name"], "position": o["position"], "team": team,
                           "status": "Entered the portal", "confidence": 90, "detail": detail})
        for t in tgt[:3]:
            interest = int(t.get("interest", 0))
            rumors.append({"player": t["name"], "position": t["position"], "team": t.get("from"),
                           "status": t.get("stage") or "On the board",
                           "confidence": interest or 45,
                           "detail": (f"{team} are in the mix for the {t['position']} out of "
                                      f"{t.get('from', 'the portal')}.")})
        for i in inc[:2]:
            rumors.append({"player": i["name"], "position": i["position"], "team": i.get("from"),
                           "status": i.get("status") or "Committed in", "confidence": 96,
                           "detail": (f"An incoming {i['position']}"
                                      + (f" from {i['from']}" if i.get("from") else "")
                                      + " the staff sees competing for early snaps.")})

    incoming = [dict(p, impact="Projected contributor", grade=_grade_for(int(p.get("ovr", 80)))) for p in inc]
    outgoing = [dict(p, reason=p.get("reason") or "Sought a fresh opportunity", grade="") for p in out]
    targets = [dict(p, fit="Fills a need at " + p["position"], lean=p.get("stage") or "On the board") for p in tgt]

    # Trust the Simulator's class grade (it owns the portal); fall back to a closed
    # message if the save predates the field.
    class_grade = tp.get("class_grade") or {
        "grade": "NR", "gpa": 0.0, "summary": "The transfer portal is closed during the season."}

    if win.get("open"):
        nil = ("The window is open. NIL is the lever now: matching a transfer's market keeps the "
               "incoming board live and gives the staff a real shot at the players it has prioritized.")
    else:
        nil = ("The portal is quiet. The window opens after the regular season, so retention of the "
               "current core is the focus until then.")

    return {"rumors": rumors, "incoming": incoming, "outgoing": outgoing, "targets": targets,
            "class_grade": class_grade, "nil_narrative": nil, "window": win}


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    progress.set_sub_step("Portal rumors and transfers")
    win = (dynasty.get("transfer_portal") or {}).get("window") or {}
    # Only spend an LLM pass when the window is actually open and there is movement
    # to write about; otherwise serve the grounded (empty) mock so the closed-season
    # portal never invents moves.
    if use_llm and win.get("open") and base.llm_available():
        try:
            context = base.build_context(dynasty, year, week)
            data = llm.generate_json(SYSTEM, _prompt(dynasty), cached_context=context,
                                     grounding=base.reactive_grounding(dynasty, year, week), max_tokens=3000)
            data.setdefault("window", win)
            source = "llm"
        except Exception:
            data = _mock(dynasty)
            source = "mock"
    else:
        data = _mock(dynasty)
        source = "mock"
    return base.sanitize(dict(data, module=MODULE, source=source))
