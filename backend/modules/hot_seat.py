"""Coaching hot seat tracker.

A heat index per coach across the dynasty universe, articles about firings and
hirings, and smarter hiring logic than the game uses. When a coaching change is
detected in the save file, the pipeline calls `coaching_search()` to generate a
full national-search narrative with a ranked candidate pool.

Scaffold: rich mock content now; LLM prompts wired for later.
"""
from __future__ import annotations

from typing import Any

from .. import customization, progress, teams
from . import base

MODULE = "hot_seat"


# The hot-seat board and candidate pool are user-editable (see customization.py).
# The user's own coach reads from the live dynasty data. Team logos resolve from
# the team name via the teams module so the editor only needs a team picker.
def _universe_coaches() -> list[dict[str, Any]]:
    out = []
    for c in customization.section("hot_seat_coaches"):
        tm = teams.get_team(c.get("team", ""))
        out.append({
            "coach": c.get("coach"), "team": c.get("team"),
            "abbr": tm.get("abbreviation"), "espn_id": tm.get("espn_id"),
            "record": c.get("record"), "heat": c.get("heat", 0),
            "trend": c.get("trend", "flat"), "note": c.get("note"),
            "image": c.get("image") or None,
        })
    return out


def _candidate_pool() -> list[dict[str, Any]]:
    return customization.section("candidates")


# How many coaches the board shows (the hottest), plus the user's own program.
_BOARD_SIZE = 24


def _coach_note(c: dict[str, Any]) -> str:
    """A factual one-liner for a board entry (never an invented buyout/donor detail)."""
    tenure = c.get("tenure_years")
    yr = f"year {tenure}" if tenure else "this season"
    rec = (c.get("record") or "").strip()
    heat = c.get("hot_seat", c.get("heat", 0)) or 0
    # Before any games the record is 0-0 and the heat is carryover from last season, so
    # "under some pressure at 0-0" reads as a contradiction. Frame it as how he ENTERS
    # the year (no in-season record), and only attach the live record once games exist.
    preseason = rec in ("", "0-0")
    if preseason:
        if heat >= 75:
            return f"Enters {yr} squarely on the hot seat."
        if heat >= 55:
            return f"Enters {yr} under real pressure."
        if heat >= 35:
            return f"Enters {yr} with something to prove."
        return f"On solid ground entering {yr}."
    where = f" at {rec}"
    if heat >= 75:
        return f"Squarely on the hot seat in {yr}{where}."
    if heat >= 55:
        return f"Feeling real heat in {yr}{where}."
    if heat >= 35:
        return f"Under some pressure in {yr}{where}."
    return f"On solid ground in {yr}{where}."


def _board_from_directory(dynasty: dict) -> list[dict[str, Any]] | None:
    """The hot-seat board built from the league coaching directory the Simulator
    wrote into the save (dynasty['coaches']). Returns None when the save has no
    directory yet (a pre-coaches save), so the caller falls back to the customization
    board. The user's own coach carries his identity image; generated coaches have
    none. Capped to the hottest seats, with the user always included."""
    cdir = dynasty.get("coaches")
    if not isinstance(cdir, dict) or not cdir:
        return None
    hc_img = ((dynasty.get("team") or {}).get("head_coach") or {}).get("image") or None
    rows: list[dict[str, Any]] = []
    for team, c in cdir.items():
        if not isinstance(c, dict) or not c.get("name"):
            continue
        is_user = bool(c.get("is_user"))
        rows.append({
            "coach": c.get("name"), "team": team, "abbr": c.get("abbr"), "espn_id": c.get("espn_id"),
            "record": c.get("record"), "heat": c.get("hot_seat", 0), "trend": c.get("trend", "flat"),
            "tenure_years": c.get("tenure_years"), "note": _coach_note(c),
            "image": hc_img if is_user else None, "is_user": is_user,
        })
    rows.sort(key=lambda x: x.get("heat", 0), reverse=True)
    board = rows[:_BOARD_SIZE]
    if not any(r["is_user"] for r in board):  # always keep the user's program on the board
        user_row = next((r for r in rows if r["is_user"]), None)
        if user_row:
            board = board[:_BOARD_SIZE - 1] + [user_row]
    return board

SYSTEM = (
    "You are a national college football desk covering the coaching hot seat and "
    "the carousel. Produce a heat index, firing/hiring articles, and when a job "
    "opens, a full search narrative with a ranked candidate pool reflecting fit, "
    "trajectory, recruiting, and NIL. Never use dashes as punctuation; use commas or periods, never dashes."
)


def _mock(dynasty: dict) -> dict[str, Any]:
    # Prefer the league coaching directory the Simulator wrote into the save (every
    # FBS coach, real fictional people). Fall back to the customization board only
    # for a pre-coaches save.
    board = _board_from_directory(dynasty)
    if board is not None:
        coaches = board
    else:
        hc = dynasty["team"]["head_coach"]
        coaches = [{
            "coach": hc["name"], "team": dynasty["team"]["name"],
            "abbr": dynasty["team"]["abbreviation"], "espn_id": dynasty["team"]["espn_id"],
            "record": dynasty["team"]["record"]["overall"], "heat": hc.get("hot_seat", 10),
            "trend": "down", "note": f"Job security as high as it has been; contract runs through {hc['contract_through']}.",
            "image": hc.get("image") or None,
            "is_user": True,
        }]
        coaches += _universe_coaches()
        coaches.sort(key=lambda c: c["heat"], reverse=True)

    # Articles are framed off the other programs on the board (not the user's seat).
    universe = [c for c in coaches if not c.get("is_user")]
    hottest = max(universe, key=lambda c: c["heat"]) if universe else None
    hot = sorted([c for c in universe if (c.get("heat") or 0) >= 65],
                 key=lambda c: c["heat"], reverse=True)
    # Articles are built from the actual board (the heat, trend, and note the user
    # set for each coach), never from invented buyout or donor specifics.
    articles = []
    if hottest:
        note = (hottest.get("note") or "").strip()
        articles.append(
            {"headline": f"Heat check: {hottest['coach']} tops the hot-seat board",
             "outlet": "Coaching Confidential", "category": "Coaching carousel",
             "accent": base.accent_for("Coaching carousel"),
             "body": (f"At {hottest['heat']} on the heat index, {hottest['coach']} "
                      f"({hottest.get('team', '')}, {hottest.get('record', '')}) is the hottest seat on the board"
                      + (f". {note}" if note else "."))})
    if hot:
        names = ", ".join(f"{c['coach']} ({c['heat']})" for c in hot[:3])
        articles.append(
            {"headline": "Carousel watch: the seats running hottest right now",
             "outlet": "The Press Box", "category": "Coaching carousel",
             "accent": base.accent_for("Coaching carousel"),
             "body": (f"By the heat index, {len(hot)} job{'s' if len(hot) != 1 else ''} sit above 65 on the "
                      f"board: {names}. The read weighs trajectory and the temperature around each program, "
                      "not raw record alone.")})

    return {"coaches": coaches, "articles": articles, "candidate_pool": _candidate_pool(), "active_search": None}


def coaching_search(open_team: str, dynasty: dict, *, use_llm: bool = False) -> dict[str, Any]:
    """Generate a full national-search narrative for a newly-open job."""
    pool = sorted(_candidate_pool(), key=lambda c: c["fit"], reverse=True)
    frontrunner = pool[0]["name"] if pool else None
    narrative_text = (
        f"The {open_team} job is open. The search board weighs scheme fit, recruiting footprint, "
        "portal and NIL acumen, and program trajectory over name recognition alone. "
        + (f"{frontrunner} leads the early board." if frontrunner else "The candidate board is still forming.")
    )
    return base.sanitize({
        "open_team": open_team,
        "narrative": narrative_text,
        "candidate_pool": pool,
        "frontrunner": frontrunner,
        "timeline": ["Search firm engaged", "Initial outreach", "On-campus interviews", "Target identified"],
    })


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    progress.set_sub_step("Coach heat index")
    data = _mock(dynasty)
    return base.sanitize(dict(data, module=MODULE, source="mock"))
