"""The persistent simulated season.

One JSON document per season at data/sim/<year>.json. The document is
intentionally canonical and minimal: it stores the universe
(teams + ratings), the full generated schedule, and the locked game results.
Everything else (records, standings, polls, stats, the Heisman board) is a pure
function of those results, recomputed on demand, so there is nothing to keep in
sync and viewing any past week is consistent.

Public surface (mirrors budget.py's style):
  new_season / status / advance / scoreboard / reset / is_active / get.

advance() plays the current week's games with the deterministic engine, applies
an optional user override, locks the results, and bumps the week. Re-simming a
week is a no-op because results that already exist are never recomputed.
"""
from __future__ import annotations

import datetime as _dt
import json
import random
import re
import threading
from typing import Any

from .. import config, customization_game as customization
from . import engine, history, league, polls, portal, recruiting, schedule, standings

_lock = threading.Lock()
_DIR = config.DATA_DIR / "sim"
_DIR.mkdir(parents=True, exist_ok=True)


def _path(year: int):
    return _DIR / f"{year}.json"


def _slug(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-") or "dynasty"


def dynasty_id_for(st: dict[str, Any]) -> str:
    """The stable unique id for a season's dynasty. Stored at creation; derived
    from team + seed for seasons that predate the field."""
    return st.get("dynasty_id") or f"{_slug(st.get('user_team'))}-{st.get('seed')}"


def get(year: int) -> dict[str, Any] | None:
    path = _path(year)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _save(state: dict[str, Any]) -> None:
    try:
        _path(state["year"]).write_text(json.dumps(state, indent=2))
    except OSError:
        pass


def is_active(year: int) -> bool:
    st = get(year)
    return bool(st and st.get("active"))


def _game_key(g: dict[str, Any]) -> str:
    return f"{g['week']}|{g['home']}|{g['away']}"


# --- lifecycle ------------------------------------------------------------
def new_season(year: int, seed: int | None = None) -> dict[str, Any]:
    """Initialize a fresh simulated season and persist it. Week 1 is upcoming."""
    if not league.has_seed():
        raise RuntimeError("league seed missing: run scripts/build_league_seed.py")
    if seed is None:
        seed = random.randint(1, 2_000_000_000)
    user = customization.team()
    universe = league.build_universe(year, seed, user)
    sched = schedule.build_schedule(universe, seed, year)
    user_team = league.user_team_name(universe)
    state = {
        "year": year,
        "seed": seed,
        "active": True,
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        # Stable unique id for this dynasty and its exported snapshots.
        "dynasty_id": f"{_slug(user_team)}-{seed}",
        "user_team": user_team,
        "weeks_total": schedule.WEEKS,
        "current_week": 1,
        # The highest week whose games are finalized and surfaced as "played"
        # (recent_results / last_game). Normally current_week - 1, but it equals
        # current_week after simulate_week locks this week's games without
        # advancing, so results can be reviewed while the clock stays put.
        "sim_through": 0,
        "teams": universe,
        "schedule": sched,
        "results": {},
        # The program's prior seasons (records, ranks, postseason, and coaches).
        "history": history.build(year, seed, universe, user_team,
                                 customization.head_coach(), customization.program()),
    }
    with _lock:
        _save(state)
    # Generate the national recruiting class for the season alongside the games.
    recruiting.new_class(year, seed, universe, state["user_team"])
    return status(year)


def reset(year: int) -> None:
    st = get(year)
    if st:
        st["active"] = False
        with _lock:
            _save(st)
    recruiting.reset(year)
    portal.reset(year)


# --- simulation -----------------------------------------------------------
def _lock_week(st: dict[str, Any], year: int, week: int,
               override: dict[str, Any] | None, user: str | None) -> None:
    """Play and lock every game in `week` (idempotent: results already present are
    never recomputed), applying the user's score override first if given."""
    universe = st["teams"]
    results = st["results"]
    if override and user:
        ug = _user_game(st, week)
        if ug:
            hs, as_ = _orient_override(ug, user, override)
            results[_game_key(ug)] = {"home_score": hs, "away_score": as_,
                                      "overtime": False, "override": True}
    for g in st["schedule"]:
        if g["week"] != week:
            continue
        k = _game_key(g)
        if k in results:
            continue
        rng = engine.make_rng(st["seed"], year, week, g["home"], g["away"])
        home_pts, away_pts = engine.simulate_game(
            universe[g["home"]]["rating"], universe[g["away"]]["rating"], rng,
            neutral=g.get("neutral", False))
        results[k] = {"home_score": home_pts, "away_score": away_pts,
                      "overtime": False, "override": False}


def simulate_week(year: int, override: dict[str, Any] | None = None) -> dict[str, Any]:
    """Play the current week's games and lock them in WITHOUT advancing the week.

    Call advance() to move to the next week and run the recruiting cycle."""
    with _lock:
        st = get(year)
        if not st or not st.get("active"):
            return {"error": "no active simulated season"}
        week = st["current_week"]
        _lock_week(st, year, week, override, st.get("user_team"))
        st["sim_through"] = week
        _save(st)
    return {"week": week, "scoreboard": scoreboard(year, week),
            "user_game": user_game_summary(year, week), "advanced": False}


def advance(year: int, override: dict[str, Any] | None = None) -> dict[str, Any]:
    """Simulate the current week (if it has not already been simulated), apply any
    user override, lock it, and bump the week. Idempotent over a week already
    locked by simulate_week."""
    with _lock:
        st = get(year)
        if not st or not st.get("active"):
            return {"error": "no active simulated season"}
        week = st["current_week"]
        _lock_week(st, year, week, override, st.get("user_team"))
        st["sim_through"] = week
        st["current_week"] = week + 1
        _save(st)

    # Progress the national recruiting cycle for the week just played. Reads the
    # coach's hours/NIL spend (budget) so his board competes in real time.
    recruiting.advance(year, week, st["teams"], weeks_total=st["weeks_total"])

    # Progress the transfer portal. A no-op during the regular season; in the
    # offseason window it opens the market (the user's unhappy players leave and a
    # national entrant pool appears) and moves it one week.
    portal.advance(year, week, st)

    return {"week": week, "scoreboard": scoreboard(year, week),
            "user_game": user_game_summary(year, week), "advanced": True}


def _user_game(st: dict[str, Any], week: int) -> dict[str, Any] | None:
    user = st.get("user_team")
    return next((g for g in st["schedule"]
                 if g["week"] == week and user in (g["home"], g["away"])), None)


def _orient_override(game: dict[str, Any], user: str, override: dict[str, Any]) -> tuple[int, int]:
    """Map {user_score, opp_score} onto (home_score, away_score)."""
    us = int(override.get("user_score", 0))
    them = int(override.get("opp_score", 0))
    if game["home"] == user:
        return us, them
    return them, us


# --- derived views --------------------------------------------------------
def _team_meta(universe: dict[str, Any], name: str) -> dict[str, Any]:
    info = universe.get(name, {})
    return {"name": name, "abbr": info.get("abbr"), "espn_id": info.get("espn_id"),
            "rating": info.get("rating"), "is_user": info.get("is_user", False)}


def scoreboard(year: int, week: int) -> list[dict[str, Any]]:
    st = get(year)
    if not st:
        return []
    universe = st["teams"]
    results = st["results"]
    user = st.get("user_team")
    # Ranks entering the week (based on games already played before it).
    records = standings.compute_records(universe, st["schedule"], results, week)
    ap_order = polls.compute(universe, records)["_ap_order"]

    out = []
    for g in st["schedule"]:
        if g["week"] != week:
            continue
        res = results.get(_game_key(g))
        home, away = _team_meta(universe, g["home"]), _team_meta(universe, g["away"])
        home["rank"] = _top25_rank(ap_order, g["home"])
        away["rank"] = _top25_rank(ap_order, g["away"])
        row = {
            "week": week, "home": home, "away": away,
            "conference": g.get("conference"), "neutral": g.get("neutral", False),
            "user": user in (g["home"], g["away"]),
            "status": "final" if res else "scheduled",
            "home_score": res["home_score"] if res else None,
            "away_score": res["away_score"] if res else None,
            "override": bool(res and res.get("override")),
        }
        if res:
            row["winner"] = g["home"] if res["home_score"] > res["away_score"] else g["away"]
        out.append(row)
    # User game first, then ranked matchups, then the rest.
    out.sort(key=lambda r: (not r["user"], min(
        r["home"].get("rank") or 99, r["away"].get("rank") or 99)))
    return out


def _top25_rank(order: list[str], name: str) -> int | None:
    idx = polls.rank_of(order, name)
    return idx if (idx is not None and idx <= 25) else None


def user_game_summary(year: int, week: int) -> dict[str, Any] | None:
    st = get(year)
    if not st:
        return None
    ug = _user_game(st, week)
    if not ug:
        return None
    for row in scoreboard(year, week):
        if row["user"]:
            return row
    return None


def status(year: int) -> dict[str, Any]:
    st = get(year)
    if not st:
        return {"active": False, "year": year, "has_seed": league.has_seed()}
    user = st.get("user_team")
    cur = st["current_week"]
    sim_through = st.get("sim_through", cur - 1)
    # Count games through the last finalized week (which is the current week once
    # it has been simulated but not yet advanced), so the record is up to date.
    cutoff = max(cur, sim_through + 1)
    records = standings.compute_records(st["teams"], st["schedule"], st["results"], cutoff)
    urec = records.get(user, {})
    return {
        "active": st.get("active", False),
        "year": year,
        "seed": st.get("seed"),
        "week": cur,
        "weeks_total": st["weeks_total"],
        "user_team": user,
        "user_record": urec.get("overall"),
        "user_conf_record": urec.get("conf"),
        # True when this week's games are locked but the week has not advanced yet
        # (so the UI shows "Advance Week" instead of "Simulate Game").
        "current_week_simmed": sim_through >= cur,
        "teams_count": len(st["teams"]),
        "has_seed": True,
    }
