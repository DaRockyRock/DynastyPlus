"""Sim universe -> schema-conforming dynasty dict.

This is the bridge that lets the simulation stand in for mock_data.generate
behind pipeline.load_dynasty. It reads the persisted season (state.py) plus the
customization store and emits the exact same dynasty shape the generation modules
already consume, field for field, including the extras beyond schema.py that the
modules and UI rely on (national.coaches_top25, receiving votes, schedule.full,
team.stats.ranks, poll-row points/first, team color/logo).

Ownership: the sim fills everything that flows from played games (records, polls,
standings, team + player stats, opponent records/ranks, the Heisman board). The
customization store still owns identity, staff, roster, recruiting, portal, NIL,
and rival names; rival records are looked up from the sim.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .. import budget, config, customization_game as customization, teams
from . import coaches as sim_coaches
from . import engine, playbyplay, polls, portal, recruiting, satisfaction, standings, state, stats


def _phase(week: int) -> str:
    if week <= 0:
        return "preseason"
    if week <= 13:
        return "regular"
    if week == 14:
        return "conf_championship"
    if week <= 16:
        return "playoff"
    return "offseason"


def _opp(universe: dict[str, Any], name: str) -> dict[str, Any]:
    """Opponent identity, resolving logo/abbr through the teams module."""
    info = universe.get(name)
    if info:
        return {"name": name, "abbr": info.get("abbr"), "espn_id": info.get("espn_id")}
    t = teams.get_team(name)
    return {"name": name, "abbr": t.get("abbreviation"), "espn_id": t.get("espn_id")}


def _national_ranks(agg: dict[str, dict[str, Any]], universe: dict[str, Any],
                    user: str) -> dict[str, Any]:
    """National + conference rank of the user team for each headline stat."""
    played = {n: a for n, a in agg.items() if a["games"] > 0}
    if user not in played:
        return {}
    user_conf = universe[user].get("conference")

    def metric(name: str, getter, *, asc: bool = False) -> dict[str, int]:
        order = sorted(played, key=lambda n: getter(played[n]), reverse=not asc)
        nat = order.index(user) + 1
        conf_order = [n for n in order if universe[n].get("conference") == user_conf]
        conf = conf_order.index(user) + 1
        return {"national": nat, "conference": conf}

    return {
        "points_per_game": metric("ppg", lambda a: a["pf"] / a["games"]),
        "points_allowed": metric("pa", lambda a: a["pa"] / a["games"], asc=True),
        "yards_per_game": metric("ypg", lambda a: a["total_yds"] / a["games"]),
        "turnover_margin": metric("tom", lambda a: a["margin"]),
    }


def _spread(home_rating: float, away_rating: float, user_is_home: bool, abbr: str) -> str:
    diff = (home_rating - away_rating) * engine.MARGIN_PER_RATING + engine.HOME_FIELD
    user_diff = diff if user_is_home else -diff
    pts = round(user_diff * 2) / 2
    if pts >= 0:
        return f"{abbr} -{pts:g}"
    return f"{abbr} +{-pts:g}"


def build_dynasty(year: int, week: int) -> dict[str, Any]:
    st = state.get(year)
    universe = st["teams"]
    sched = st["schedule"]
    results = st["results"]
    user = st["user_team"]

    # `week` is the season clock (the week the user is on). The games that count
    # as PLAYED run through sim_through, which is week-1 normally but equals the
    # current week once it has been simulated-but-not-advanced. Records, polls,
    # stats, and the schedule's played/upcoming split all key off that, decoupled
    # from the displayed week, so a simulated-not-advanced week shows its result.
    played_through = st.get("sim_through", week - 1)
    cutoff = played_through + 1  # games strictly before this are final

    records = standings.compute_records(universe, sched, results, cutoff)
    poll = polls.compute(universe, records)
    user_players = customization.section("players")
    stat = stats.compute(universe, sched, results, cutoff, seed=st["seed"], year=year,
                         user_players=user_players)
    agg = stat["teams"]

    urec = records.get(user, {"overall": "0-0", "conf": "0-0", "streak": "-"})
    ua = agg.get(user, {"games": 0, "pf": 0, "pa": 0, "total_yds": 0, "margin": 0})
    g = max(1, ua["games"])

    tm = customization.team()
    hc = customization.head_coach()
    prog = customization.program()

    # Live player satisfaction -> risk_of_leaving, computed from the real season
    # context (depth role, results vs prestige, class/draft, program profile, the
    # coach's seat). Replaces the random retention seed; budget.snapshot still
    # layers the NIL gap on top. Players who have actually entered the portal in
    # the offseason window are flagged here so the roster reflects the departure.
    key_players = satisfaction.compute(
        _roster(user_players, stat["players"], user), record=urec,
        prestige=universe.get(user, {}).get("prestige", 5),
        ap_rank=polls.rank_of(poll["_ap_order"], user), week=week,
        weeks_total=st["weeks_total"], seed=st["seed"], coach_hot_seat=hc.get("hot_seat"))
    if portal.has_opened(week, st["weeks_total"]):
        _gone = portal.user_outgoing_names(year)
        for _p in key_players:
            if _p["name"] in _gone:
                _p["in_portal"] = True
                _p["risk_of_leaving"] = 100
                _p["risk_reason"] = "Has entered the transfer portal."

    dynasty = {
        "meta": {"generated_at": _now(), "source": "sim", "app_version": config.APP_VERSION,
                 "dynasty_id": state.dynasty_id_for(st)},
        "season": {"year": year, "week": week, "week_label": f"Week {week}", "phase": _phase(week)},
        "team": {
            "name": tm.get("name"), "school": tm.get("school"), "nickname": tm.get("nickname"),
            "abbreviation": tm.get("abbreviation"), "espn_id": tm.get("espn_id"),
            "color": tm.get("color"), "alt_color": tm.get("alt_color"), "logo": tm.get("logo") or None,
            "conference": tm.get("conference"), "division": universe.get(user, {}).get("division"),
            "record": {"overall": urec["overall"], "conference": urec["conf"], "streak": urec["streak"]},
            "head_coach": {
                "name": hc.get("name"), "title": hc.get("title"), "tenure_years": hc.get("tenure_years"),
                "alma_mater": hc.get("alma_mater"), "contract_through": hc.get("contract_through"),
                "hot_seat": hc.get("hot_seat"), "image": hc.get("image") or None,
            },
            "rankings": {
                "cfp": polls.rank_of(poll["_cfp_order"], user) if _in(poll["_cfp_order"], user, 12) else None,
                "ap": polls.rank_of(poll["_ap_order"], user) if _in(poll["_ap_order"], user, 25) else None,
                "coaches": polls.rank_of(poll["_coaches_order"], user) if _in(poll["_coaches_order"], user, 25) else None,
            },
            "stats": {
                "points_per_game": round(ua["pf"] / g, 1),
                "points_allowed": round(ua["pa"] / g, 1),
                "yards_per_game": round(ua["total_yds"] / g, 1),
                "turnover_margin": ua["margin"],
                "ranks": _national_ranks(agg, universe, user),
            },
        },
        "coaching_staff": customization.section("coaching_staff"),
        "roster": {"key_players": key_players},
        "nil": {
            "dynasty_points": {
                "total": prog.get("dynasty_points_total"),
                "allocations": {
                    "coaching_staff": prog.get("alloc_coaching_staff"),
                    "facilities": prog.get("alloc_facilities"),
                    "nil": prog.get("alloc_nil"),
                },
            },
            "recruiting_pool": prog.get("recruiting_pool"),
            "roster_pool": prog.get("roster_pool"),
            "weekly_recruiting_hours": prog.get("weekly_recruiting_hours"),
            "dp_per_dollar": config.DP_PER_DOLLAR,
        },
        "recruiting": _recruiting_block(year),
        "transfer_portal": _portal_block(year, week, st, universe),
        "schedule": _schedule_block(st, week, played_through, records, poll, universe),
        "rivals": _rivals(records, poll, universe),
        "conference_standings": standings.conference_table(records, universe, tm.get("conference")),
        "national": {
            "ap_top25": poll["ap_top25"],
            "coaches_top25": poll["coaches_top25"],
            "cfp_top12": poll["cfp_top12"],
            "ap_receiving_votes": poll["ap_receiving_votes"],
            "coaches_receiving_votes": poll["coaches_receiving_votes"],
            "heisman_frontrunners": stat["heisman"],
            "stat_leaders": _stat_leaders(stat["leaders"]),
            "scoreboard": _scoreboard_block(st, week, played_through, records, poll, universe),
        },
    }

    # The program's prior-season history (records, ranks, postseason, coaches),
    # so the companion can open on the real landscape (last year, the coaching
    # change) rather than a blank slate.
    dynasty["history"] = st.get("history") or []

    # Every FBS program gets a fictional head coach (CFB27 owns a coach for every
    # team; this stands in until the real save is readable). dynasty["coaches"] is
    # the full directory (team -> coach entity with name, tenure, record, hot-seat
    # heat) that the hot-seat board, the phone, and national coverage all read, so
    # the companion names a real person for other programs instead of inventing a
    # real-life coach. The user's own program keeps its identity coach.
    cdir = sim_coaches.build_directory(
        universe, records, st["seed"], user=user,
        user_coach=hc.get("name"), user_tenure=hc.get("tenure_years"), user_hot_seat=hc.get("hot_seat"))
    dynasty["coaches"] = cdir

    def _coach_name(team_name: str):
        return (cdir.get(team_name) or {}).get("name")

    # Stamp the coach name inline where consumers want it cheaply: national poll
    # rows, rivals, the upcoming opponent, and recent results.
    for _key in ("ap_top25", "coaches_top25", "cfp_top12", "ap_receiving_votes", "coaches_receiving_votes"):
        for _row in dynasty["national"].get(_key) or []:
            if isinstance(_row, dict) and _row.get("team"):
                _row["coach"] = _coach_name(_row["team"])
    for _r in dynasty.get("rivals") or []:
        if isinstance(_r, dict) and _r.get("name"):
            _r.setdefault("coach", _coach_name(_r["name"]))
    _sched = dynasty.get("schedule") or {}
    if isinstance(_sched.get("upcoming"), dict) and _sched["upcoming"].get("opponent"):
        _sched["upcoming"]["opponent_coach"] = _coach_name(_sched["upcoming"]["opponent"])
    for _g in _sched.get("recent_results") or []:
        if isinstance(_g, dict) and _g.get("opponent"):
            _g["opponent_coach"] = _coach_name(_g["opponent"])

    # The user's most recently completed game, reconstructed in full (drives,
    # plays, both box scores, scoring summary) from the canonical final score.
    # Deterministic and timestamp-free so it does not churn meta.hash. Drives the
    # Game Center and gives the post-game press conference the whole game. Absent
    # on a bye / before the first game.
    last_game = playbyplay.build_for_user(st, played_through, user_players)
    if last_game:
        dynasty["last_game"] = last_game

    # Embed the authoritative NIL/budget snapshot so Dynasty+ reads it straight
    # from the save (it no longer owns the budget store). Then stamp the explicit
    # pointer and a content hash the watcher uses to detect same-week edits.
    dynasty["budget"] = budget.snapshot(year, week, dynasty)
    dynasty["meta"]["pointer"] = {"year": year, "week": week}
    dynasty["meta"]["hash"] = _content_hash(dynasty)
    return dynasty


def _content_hash(dynasty: dict[str, Any]) -> str:
    """Stable sha1 over the MEDIA-AFFECTING content, so the companion can tell a
    real edit from a no-op rewrite. Excludes two volatile blobs:

      * meta   - carries the volatile generated_at timestamp.
      * budget - the live NIL/Dynasty Points snapshot. It churns on every coach
                 NIL offer or recruiting action (the Simulator drains the inbox and
                 rewrites the save), but spending NIL does NOT change the news,
                 recruiting board, rankings, or any generated media. Folding it into
                 the hash made every offer look like a same-week edit and forced the
                 companion to regenerate the whole week. The companion still reads
                 the fresh budget straight from the save; only a real content change
                 (roster, results, week, identity) should regenerate media.
    """
    content = {k: v for k, v in dynasty.items() if k not in ("meta", "budget")}
    blob = json.dumps(content, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _portal_block(year: int, week: int, st: dict[str, Any], universe: dict[str, Any]) -> dict[str, Any]:
    """The transfer-portal block: a window descriptor plus the user's board, all
    sim-derived. Closed and empty during the regular season (the bug fix); the
    market only fills once the offseason window has opened."""
    weeks_total = st["weeks_total"]
    win = portal.window(year, week, weeks_total)
    if not portal.has_opened(week, weeks_total) or portal.get(year) is None:
        return {"window": win, "incoming": [], "outgoing": [], "targets": [],
                "class_grade": {"grade": "NR", "gpa": 0.0,
                                "summary": "The transfer portal is closed during the season."}}
    return {"window": win, **portal.user_board(year, universe),
            "class_grade": portal.class_grade(year)}


def _recruiting_block(year: int) -> dict[str, Any]:
    """The user's recruiting board, from the national class when one exists."""
    if recruiting.get(year) is None:
        return {
            "class_rank_national": 14, "class_rank_conference": 4,
            "commits": customization.section("commits"),
            "targets": customization.section("targets"),
        }
    board = recruiting.user_board(year)
    ranks = recruiting.class_rankings(year)
    return {
        "class_rank_national": ranks.get("national"),
        "class_rank_conference": ranks.get("conference"),
        "commits": board["commits"],
        "targets": board["targets"],
    }


def _in(order: list[str], name: str, cap: int) -> bool:
    idx = polls.rank_of(order, name)
    return idx is not None and idx <= cap


def _roster(user_players: list[dict[str, Any]], sim_players: list[dict[str, Any]],
            user: str) -> list[dict[str, Any]]:
    """Customization roster with stat lines overwritten by simulated season totals."""
    sim_by_name = {p["name"]: p for p in sim_players if p["team"] == user}
    out = []
    for p in user_players or []:
        p = dict(p)
        sp = sim_by_name.get(p.get("name"))
        if sp and sp.get("stat_line"):
            p["stat_line"] = sp["stat_line"]
        out.append(p)
    return out


def _stat_leaders(leaders: dict[str, list[dict[str, Any]]] | None) -> dict[str, list[dict[str, Any]]]:
    """Trim the computed stat-leader board (passing/rushing/receiving/sacks) to the
    top few per category, carrying just identity + the formatted line. National
    coverage cites these so a story can name the country's leading passer or sack
    artist instead of inventing one."""
    out: dict[str, list[dict[str, Any]]] = {}
    for cat, lst in (leaders or {}).items():
        out[cat] = [
            {"name": p["name"], "team": p["team"], "position": p["position"],
             "stat_line": p.get("stat_line")}
            for p in (lst or [])[:3]
        ]
    return out


def _scoreboard_block(st: dict[str, Any], week: int, played_through: int,
                      records, poll, universe) -> list[dict[str, Any]]:
    """Every FBS game in the displayed week: both sides' identity, record, and
    AP rank, plus the rating-derived betting line. This is the save's national
    slate; the companion ranks it client-side into the marquee matchups rail."""
    ap_order = poll["_ap_order"]
    user = st["user_team"]

    def side(name: str) -> dict[str, Any]:
        meta = _opp(universe, name)
        rank = polls.rank_of(ap_order, name)
        return {
            "name": name, "abbr": meta["abbr"], "espn_id": meta["espn_id"],
            "record": records.get(name, {}).get("overall", "0-0"),
            "rank": rank if (rank and rank <= 25) else None,
        }

    def line(home: str, away: str, home_abbr: str, away_abbr: str) -> str:
        hr = universe.get(home, {}).get("rating", 70)
        ar = universe.get(away, {}).get("rating", 70)
        pts = round(((hr - ar) * engine.MARGIN_PER_RATING + engine.HOME_FIELD) * 2) / 2
        if pts == 0:
            return "EVEN"
        return f"{home_abbr} -{pts:g}" if pts > 0 else f"{away_abbr} -{-pts:g}"

    out = []
    for g in st["schedule"]:
        if g["week"] != week:
            continue
        res = st["results"].get(f"{g['week']}|{g['home']}|{g['away']}")
        final = res is not None and g["week"] <= played_through
        home, away = side(g["home"]), side(g["away"])
        out.append({
            "week": week, "home": home, "away": away,
            "conference_game": bool(g.get("conference")),
            "neutral": bool(g.get("neutral", False)),
            "user": user in (g["home"], g["away"]),
            "status": "final" if final else "scheduled",
            "home_score": res["home_score"] if final else None,
            "away_score": res["away_score"] if final else None,
            "line": line(g["home"], g["away"], home["abbr"], away["abbr"]),
        })
    return out


def _schedule_block(st: dict[str, Any], week: int, played_through: int, records, poll, universe) -> dict[str, Any]:
    user = st["user_team"]
    user_games = sorted((g for g in st["schedule"] if user in (g["home"], g["away"])),
                        key=lambda g: g["week"])
    ap_order = poll["_ap_order"]

    recent, full, upcoming = [], [], None
    for g in user_games:
        home = g["home"] == user
        opp_name = g["away"] if home else g["home"]
        opp = _opp(universe, opp_name)
        res = st["results"].get(f"{g['week']}|{g['home']}|{g['away']}")
        played = res is not None and g["week"] <= played_through
        opp_rank = polls.rank_of(ap_order, opp_name)
        opp_rank = opp_rank if (opp_rank and opp_rank <= 25) else None
        rank_matchup = f"#{opp_rank} {opp_name}" if opp_rank else None

        score = result = None
        if played:
            us = res["home_score"] if home else res["away_score"]
            them = res["away_score"] if home else res["home_score"]
            result = "W" if us > them else "L"
            score = f"{us}-{them}"

        status = "final" if played else ("next" if g["week"] == played_through + 1 else "upcoming")
        full.append({
            "week": g["week"], "opponent": opp_name, "opponent_abbr": opp["abbr"],
            "opponent_espn_id": opp["espn_id"], "home": home,
            "result": result, "score": score, "rank_matchup": rank_matchup, "status": status,
        })
        if played:
            recent.append({
                "week": g["week"], "opponent": opp_name, "opponent_abbr": opp["abbr"],
                "opponent_espn_id": opp["espn_id"], "home": home,
                "result": result, "score": score, "rank_matchup": rank_matchup,
            })
        if g["week"] == played_through + 1 and upcoming is None:
            ur = universe.get(user, {}).get("rating", 70)
            or_ = universe.get(opp_name, {}).get("rating", 70)
            upcoming = {
                "week": g["week"], "opponent": opp_name, "opponent_abbr": opp["abbr"],
                "opponent_espn_id": opp["espn_id"],
                "opponent_record": records.get(opp_name, {}).get("overall", "0-0"),
                "opponent_rank": opp_rank, "home": home,
                "kickoff": "Saturday 7:30 PM ET", "tv": "NBC / Peacock",
                "spread": _spread(ur if home else or_, or_ if home else ur, home,
                                  universe.get(user, {}).get("abbr", "USR")),
            }

    recent = list(reversed(recent))[:5]
    if upcoming is None:  # bye or postseason: fall back to the last game for context
        last = user_games[-1] if user_games else None
        if last:
            opp_name = last["away"] if last["home"] == user else last["home"]
            opp = _opp(universe, opp_name)
            upcoming = {
                "week": week, "opponent": opp_name, "opponent_abbr": opp["abbr"],
                "opponent_espn_id": opp["espn_id"],
                "opponent_record": records.get(opp_name, {}).get("overall", "0-0"),
                "opponent_rank": None, "home": True,
                "kickoff": "TBD", "tv": "TBD", "spread": "EVEN",
            }
    return {"recent_results": recent, "upcoming": upcoming, "full": full}


def _rivals(records, poll, universe) -> list[dict[str, Any]]:
    ap_order = poll["_ap_order"]
    out = []
    for r in customization.section("rivals"):
        name = r.get("name")
        rank = polls.rank_of(ap_order, name)
        rank = rank if (rank and rank <= 25) else None
        meta = _opp(universe, name)
        out.append({
            "name": name, "abbreviation": meta["abbr"], "espn_id": meta["espn_id"],
            "record": records.get(name, {}).get("overall", r.get("record")),
            "rank": rank if rank is not None else r.get("rank"),
            "note": r.get("note"),
        })
    return out


def _now() -> str:
    import datetime as _dt
    return _dt.datetime.now().isoformat(timespec="seconds")
