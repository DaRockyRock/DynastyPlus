"""Deterministic full-game reconstruction for the user's game.

The season model in engine.py decides only a final score per game, and stats.py
distributes season totals across four star players. The exported snapshot also
needs a complete game record: every drive, every play, both box scores, and the
scoring summary. This module reconstructs that game from the canonical final
score, so records, polls, season stats, and user overrides do not need to change.

It is "score-first": the final score stays the source of truth, and we back-fill
a play sequence whose scoring sums to it exactly and whose per-player yards sum to
the team totals by construction (every play's yards are attributed to a player).
Everything runs through one RNG seeded off the stable game key, so re-running an
advance reproduces the identical game, the same way engine.simulate_game and
stats.compute are idempotent. The star QB/RB/WR/EDGE names come straight from
stats.py so the box score and the Heisman board name the same fictional players,
and the user's real key_players fill those slots for his team.

Pure output (no timestamps): the game lands in dynasty["last_game"], which is
part of meta.hash, so every field must remain deterministic.
"""
from __future__ import annotations

from typing import Any

from .engine import make_rng
from . import stats


# --- identity + names ------------------------------------------------------
def _team_meta(universe: dict[str, Any], name: str) -> dict[str, Any]:
    info = universe.get(name, {})
    return {"name": name, "abbr": info.get("abbr") or name[:3].upper(),
            "espn_id": info.get("espn_id")}


def _name(seed: int, team: str, slot: str) -> str:
    """A deterministic fictional name for a non-star (secondary) player. Keyed off
    a distinct prefix so it never collides with stats.py's star names."""
    r = make_rng(seed, "pbp_name", team, slot)
    return f"{r.choice(stats.FIRST_NAMES)} {r.choice(stats.LAST_NAMES)}"


def _roster(seed: int, team: str, info: dict[str, Any], is_user: bool,
            user_players: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Skill players + a defensive front for one team. The QB/RB/WR/EDGE names
    reuse stats._stars_for so they match the season-stat board (and the user's
    real key_players for his team); secondary players are deterministic fiction."""
    stars = stats._stars_for(team, {**info, "is_user": is_user}, seed,
                             user_players if is_user else None)
    return {
        "qb": stars["QB"]["name"],
        "rbs": [stars["RB"]["name"], _name(seed, team, "RB2")],
        "wrs": [stars["WR"]["name"], _name(seed, team, "WR2"),
                _name(seed, team, "WR3"), _name(seed, team, "TE1")],
        "k": _name(seed, team, "K"),
        "defense": [stars["EDGE"]["name"], _name(seed, team, "LB1"),
                    _name(seed, team, "S1"), _name(seed, team, "DL1"),
                    _name(seed, team, "CB1"), _name(seed, team, "LB2")],
        "edge": stars["EDGE"]["name"],
    }


# --- scoring decomposition (exact) -----------------------------------------
def _distribute_converts(td: int, extra: int, rng) -> list[int]:
    """Spread `extra` convert points across `td` touchdowns, each in {0,1,2}
    (missed PAT / kick / two-point), summing exactly to extra."""
    converts = [0] * td
    if td == 0:
        return converts
    order = list(range(td))
    rng.shuffle(order)
    remaining = extra
    # First pass: a PAT (1) on as many TDs as the budget allows.
    for i in order:
        if remaining <= 0:
            break
        converts[i] = 1
        remaining -= 1
    # Second pass: upgrade some PATs to two-point (1 -> 2) to spend the rest.
    for i in order:
        if remaining <= 0:
            break
        if converts[i] == 1:
            converts[i] = 2
            remaining -= 1
    return converts


def _decompose(points: int, rng) -> list[dict[str, Any]]:
    """Break a team's point total into an exact list of scoring events. Prefers
    touchdowns, then field goals; safeties and the rare one-point safety absorb
    football-impossible remainders (the score model can emit any integer)."""
    if points <= 0:
        return []
    best = None  # (preference_key, (td, fg, saf, one, extra))
    for one in (0, 1):              # one-point safety (rare, only to fix a lone 1)
        for saf in range(0, 3):     # safeties
            for fg in range(0, points // 3 + 1):
                rem = points - 3 * fg - 2 * saf - one
                if rem < 0:
                    break
                for td in range(0, rem // 6 + 1):
                    extra = rem - 6 * td
                    if 0 <= extra <= 2 * td:
                        # Prefer the most natural decomposition: as few oddities as
                        # possible (missed PATs / two-pointers / safeties), then more
                        # touchdowns, then fewer field goals. abs(extra-td) is the
                        # count of TDs that are not a plain TD+PAT.
                        anomalies = abs(extra - td) + saf + one
                        key = (anomalies, -td, fg)
                        if best is None or key < best[0]:
                            best = (key, (td, fg, saf, one, extra))
    td, fg, saf, one, extra = best[1]
    events: list[dict[str, Any]] = []
    for c in _distribute_converts(td, extra, rng):
        events.append({"type": "TD", "points": 6 + c, "convert": c})
    events += [{"type": "FG", "points": 3}] * fg
    events += [{"type": "Safety", "points": 2}] * saf
    events += [{"type": "Safety", "points": 1}] * one  # one-point safety
    return events


# --- yardline helpers ------------------------------------------------------
def _yardline(yard: int) -> str:
    """A field position (0..100 from a team's own goal) as broadcast text."""
    yard = max(1, min(99, yard))
    if yard == 50:
        return "50"
    if yard < 50:
        return f"OWN {yard}"
    return f"OPP {100 - yard}"


def _clock(elapsed: int, overtime: bool) -> tuple[str, int]:
    """(quarter_label, remaining_seconds_in_quarter) from seconds elapsed."""
    if elapsed >= 3600:
        return ("OT" if overtime else "4", 0)
    q = elapsed // 900 + 1
    rem = 900 - (elapsed % 900)
    return (str(q), rem)


def _mmss(seconds: int) -> str:
    seconds = max(0, seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


# --- play generation -------------------------------------------------------
def _gain(rng, kind: str) -> int:
    # Occasional chunk play keeps scoring drives from grinding 12 plays downfield.
    if rng.random() < 0.10:
        return rng.randint(16, 44)
    if kind == "run":
        return max(-4, round(rng.gauss(5.2, 6.0)))
    return max(-3, round(rng.gauss(11.5, 9.0)))  # completed pass


def _play_secs(rng, kind: str, complete: bool) -> int:
    if kind == "pass" and not complete:
        return rng.randint(5, 10)
    return rng.randint(22, 42)


def _expand_drive(drive: dict[str, Any], roster: dict[str, Any], opp_def: dict[str, Any],
                  rng, box: dict[str, Any], opp_box: dict[str, Any], start_yard: int,
                  fg_target: int) -> dict[str, Any]:
    """Build the play list for one drive, mutating both teams' box accumulators.
    Returns drive yards/plays/seconds and the made-it field position. The drive's
    predetermined `result` steers the loop (a TD drive always reaches the end zone,
    a turnover drive ends on a giveaway, a punt drive stalls)."""
    result = drive["result"]
    yard = start_yard
    down, to_go = 1, 10
    plays: list[dict[str, Any]] = []
    drive_yards = 0
    secs = 0
    fd = 0

    def record(kind: str, gain: int, complete: bool, desc: str, end: str | None = None):
        nonlocal yard, down, to_go, drive_yards, secs, fd
        plays.append({"down": down, "distance": to_go, "yardline": _yardline(yard),
                      "type": kind, "yards": gain, "description": desc, "result": end})
        secs += _play_secs(rng, kind, complete)
        if complete or kind == "run":
            yard += gain
            drive_yards += gain
            if gain >= to_go:
                fd += 1
                down, to_go = 1, 10
            else:
                down += 1
                to_go -= gain
        else:
            down += 1  # incompletion: clock-ish, down advances

    # A safety is scored by the defense; model it as a quick, self-contained
    # possession rather than a normal drive (it is rare, only from odd scores).
    if result == "Safety":
        plays.append({"down": down, "distance": to_go, "yardline": _yardline(yard),
                      "type": "safety", "yards": 0,
                      "description": "tackled in the end zone, safety", "result": "Safety"})
        secs += rng.randint(10, 20)
        return _drive_summary(plays, 0, secs, yard)

    def kick_fg(good: bool) -> None:
        nonlocal secs
        dist = min(56, max(19, (100 - yard) + 17))
        verdict = "GOOD" if good else "NO GOOD"
        plays.append({"down": down, "distance": to_go, "yardline": _yardline(yard),
                      "type": "fg", "yards": 0,
                      "description": f"{roster['k']} {dist} yd field goal is {verdict}",
                      "result": "Field Goal" if good else "Missed FG"})
        secs += rng.randint(6, 12)

    def punt() -> None:
        nonlocal secs
        plays.append({"down": down, "distance": to_go, "yardline": _yardline(yard),
                      "type": "punt", "yards": 0, "description": "punts", "result": "Punt"})
        drive["result"] = "Punt"
        secs += rng.randint(8, 14)

    is_scoring = result in ("Touchdown", "Field Goal")
    last_player: str | None = None
    last_kind: str | None = None
    cap = 12
    for _ in range(cap):
        # Fourth-down decision first, so a punt or a missed kick does not log a
        # phantom offensive snap (which would inflate fourth-down attempts).
        if down >= 4 and not is_scoring and result not in ("Interception", "Fumble"):
            if result == "Missed FG" and yard >= 58:
                kick_fg(False)
                drive["result"] = "Missed FG"
            else:
                punt()
            return _drive_summary(plays, drive_yards, secs, yard, fd)

        # Predetermined giveaway (non-scoring drives only).
        if result == "Interception" and (down >= 3 or len(plays) >= 4):
            db = rng.choice(opp_def["defense"][1:])
            record("pass", 0, False, f"{roster['qb']} pass INTERCEPTED by {db}", "Interception")
            box["pass_int"] += 1
            opp_box["takeaways"] += 1
            _credit_def(opp_box, db, interception=True)
            return _drive_summary(plays, drive_yards, secs, yard, fd)
        if result == "Fumble" and (down >= 2 and len(plays) >= 3):
            carrier = roster["rbs"][0]
            db = rng.choice(opp_def["defense"])
            g2 = _gain(rng, "run")
            record("run", g2, True, f"{carrier} FUMBLES, recovered by {db}", "Fumble")
            _credit_rush(box, carrier, g2, rng)
            box["fumbles_lost"] += 1
            opp_box["takeaways"] += 1
            return _drive_summary(plays, drive_yards, secs, yard, fd)

        # A drive that ultimately scores keeps the chains moving: on third or
        # fourth down it converts rather than stalling, so scoring drives never
        # pile up fourth-down attempts or turn the ball over.
        force = is_scoring and down >= 3
        pass_play = rng.random() < (0.6 if down >= 3 else 0.52)
        if pass_play:
            if not force and rng.random() < 0.05:  # sack
                sacker = rng.choice(opp_def["defense"][:3])
                loss = -rng.randint(4, 9)
                record("sack", loss, True, f"{roster['qb']} sacked by {sacker} for {loss}", None)
                _credit_sack(opp_box, sacker)
                box["sacks_allowed"] += 1
                last_player = last_kind = None
                continue
            if force or rng.random() < 0.63:  # completion
                gain = _gain(rng, "pass")
                if force and gain < to_go:
                    gain = to_go + rng.randint(0, 7)
                rcv = rng.choice(roster["wrs"])
                if result == "Touchdown" and yard + gain >= 100:
                    gain = 100 - yard
                tag = " on fourth down" if down == 4 else ""
                record("pass", gain, True, f"{roster['qb']} pass complete to {rcv} for {gain}{tag}", None)
                _credit_pass(box, gain, rcv, rng)
                last_player, last_kind = rcv, "rec"
            else:
                record("pass", 0, False, f"{roster['qb']} pass incomplete", None)
                _credit_incompletion(box)
                last_player = last_kind = None
        else:
            gain = _gain(rng, "run")
            if force and gain < to_go:
                gain = to_go + rng.randint(0, 7)
            carrier = roster["rbs"][0] if rng.random() < 0.72 else (
                roster["rbs"][1] if rng.random() < 0.6 else roster["qb"])
            if result == "Touchdown" and yard + gain >= 100:
                gain = 100 - yard
            verb = "rush" if carrier != roster["qb"] else "scramble"
            tag = " on fourth down" if down == 4 else ""
            record("run", gain, True, f"{carrier} {verb} for {gain}{tag}", None)
            _credit_rush(box, carrier, gain, rng)
            last_player, last_kind = carrier, "rush"

        # A scoring drive must score: reach the end zone, or kick when in range.
        if result == "Touchdown" and yard >= 100:
            plays[-1]["result"] = "Touchdown"
            plays[-1]["scorer"], plays[-1]["scorer_kind"] = last_player, last_kind
            return _drive_summary(plays, drive_yards, secs, yard, fd)
        if result == "Field Goal" and yard >= fg_target:
            kick_fg(True)
            return _drive_summary(plays, drive_yards, secs, yard, fd)

    # Hit the play cap: force the predetermined outcome cleanly.
    if result == "Touchdown":
        down, to_go = 1, 10
        gain = max(1, 100 - yard)
        scorer = roster["rbs"][0]
        record("run", gain, True, f"{scorer} rush for {gain}, TOUCHDOWN", "Touchdown")
        _credit_rush(box, scorer, gain, rng)
        plays[-1]["scorer"], plays[-1]["scorer_kind"] = scorer, "rush"
    elif result == "Field Goal":
        kick_fg(True)
    elif result not in ("Interception", "Fumble"):
        punt()
    return _drive_summary(plays, drive_yards, secs, yard, fd)


def _drive_summary(plays, yards, secs, yard, fd=0) -> dict[str, Any]:
    return {"plays_list": plays, "yards": yards, "secs": secs, "end_yard": yard, "first_downs": fd}


# --- box-score crediting ---------------------------------------------------
def _credit_pass(box, gain, rcv, rng) -> None:
    box["pass_yards"] += gain
    box["completions"] += 1
    box["attempts"] += 1
    box["rec"].setdefault(rcv, {"rec": 0, "yds": 0, "td": 0, "long": 0})
    r = box["rec"][rcv]
    r["rec"] += 1
    r["yds"] += gain
    r["long"] = max(r["long"], gain)


def _credit_incompletion(box) -> None:
    box["attempts"] += 1


def _credit_rush(box, carrier, gain, rng) -> None:
    box["rush_yards"] += gain
    box["rush"].setdefault(carrier, {"car": 0, "yds": 0, "td": 0, "long": 0})
    r = box["rush"][carrier]
    r["car"] += 1
    r["yds"] += gain
    r["long"] = max(r["long"], gain)


def _credit_def(box, name, *, interception=False, pd=False) -> None:
    d = box["def"].setdefault(name, {"tackles": 0, "sacks": 0.0, "tfl": 0, "int": 0, "pd": 0})
    if interception:
        d["int"] += 1
    if pd:
        d["pd"] += 1


def _credit_sack(box, name) -> None:
    d = box["def"].setdefault(name, {"tackles": 0, "sacks": 0.0, "tfl": 0, "int": 0, "pd": 0})
    d["sacks"] += 1
    d["tfl"] += 1
    box["sacks"] += 1


def _empty_box() -> dict[str, Any]:
    return {"pass_yards": 0, "rush_yards": 0, "completions": 0, "attempts": 0,
            "pass_int": 0, "fumbles_lost": 0, "sacks_allowed": 0, "sacks": 0,
            "takeaways": 0, "first_downs": 0, "plays": 0, "secs": 0,
            "third_made": 0, "third_att": 0, "fourth_made": 0, "fourth_att": 0,
            "rz_made": 0, "rz_att": 0, "pen": 0, "pen_yds": 0,
            "rush": {}, "rec": {}, "def": {}, "pass_td": 0, "rush_td": 0}


# --- assembling the game ---------------------------------------------------
def build_for_user(st: dict[str, Any], played_through: int,
                   user_players: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """The user's most recent COMPLETED game (week <= played_through) as a full
    game object, or None on a bye / before any game is played. played_through is
    the last finalized week, which can be the current week once it has been
    simulated but not yet advanced."""
    user = st.get("user_team")
    if not user:
        return None
    played = [g for g in st["schedule"]
              if user in (g["home"], g["away"]) and g["week"] <= played_through
              and f"{g['week']}|{g['home']}|{g['away']}" in st["results"]]
    if not played:
        return None
    g = max(played, key=lambda x: x["week"])
    res = st["results"][f"{g['week']}|{g['home']}|{g['away']}"]
    return _build_game(st, g, res, user, user_players)


def _build_game(st, g, res, user, user_players) -> dict[str, Any]:
    seed, year = st["seed"], st["year"]
    universe = st["teams"]
    home, away = g["home"], g["away"]
    hs, as_ = res["home_score"], res["away_score"]
    overtime = bool(res.get("overtime"))
    gweek = g["week"]
    rng = make_rng(seed, year, gweek, home, away, "pbp")

    rosters = {
        home: _roster(seed, home, universe.get(home, {}), home == user, user_players),
        away: _roster(seed, away, universe.get(away, {}), away == user, user_players),
    }
    boxes = {home: _empty_box(), away: _empty_box()}
    events = {home: _decompose(hs, rng), away: _decompose(as_, rng)}

    # Build each team's drive list: one drive per scoring event, plus stalls and
    # giveaways, then interleave the two teams chronologically.
    drives_by_team = {t: _team_drives(events[t], rng) for t in (home, away)}
    sequence = _interleave(drives_by_team, home, away, rng)

    # Pass 1: expand every drive (mutating the box accumulators) and total the
    # raw time, so pass 2 can scale the timeline to fit a regulation game.
    expanded: list[tuple[dict[str, Any], dict[str, Any], str, int]] = []
    for d in sequence:
        team = d["team"]
        opp = away if team == home else home
        box, opp_box = boxes[team], boxes[opp]
        start_yard = rng.randint(20, 34)
        fg_target = rng.randint(60, 78)
        summary = _expand_drive(d, rosters[team], rosters[opp], rng, box, opp_box, start_yard, fg_target)

        box["plays"] += len(summary["plays_list"])
        box["first_downs"] += summary["first_downs"]
        box["secs"] += summary["secs"]
        for p in summary["plays_list"]:
            if p["down"] == 3 and p["type"] in ("run", "pass"):
                box["third_att"] += 1
                if p["yards"] >= p["distance"]:
                    box["third_made"] += 1
            if p["down"] == 4 and p["type"] in ("run", "pass"):
                box["fourth_att"] += 1
                if p["yards"] >= p["distance"]:
                    box["fourth_made"] += 1
        if summary["end_yard"] >= 80 or d["result"] == "Touchdown":
            box["rz_att"] += 1
            if d["result"] in ("Touchdown", "Field Goal"):
                box["rz_made"] += 1
        expanded.append((d, summary, team, start_yard))

    total_raw = sum(s["secs"] for _, s, _, _ in expanded) or 1
    scale = 3540 / total_raw  # fit regulation; the last drive may spill into OT

    drive_rows: list[dict[str, Any]] = []
    scoring: list[dict[str, Any]] = []
    pbp: list[dict[str, Any]] = []
    score = {home: 0, away: 0}
    elapsed = 0.0

    for idx, (d, summary, team, start_yard) in enumerate(expanded):
        box = boxes[team]
        abbr = _team_meta(universe, team)["abbr"]
        drive_secs = summary["secs"] * scale
        is_last = idx == len(expanded) - 1
        ot = overtime and is_last
        q_label, q_rem = ("OT", 0) if ot else _clock(int(elapsed), False)

        n = max(1, len(summary["plays_list"]))
        for j, p in enumerate(summary["plays_list"]):
            if ot:
                pq, prem = "OT", 0
            else:
                pq, prem = _clock(int(elapsed + drive_secs * j / n), False)
            pbp.append({"quarter": pq, "clock": _mmss(prem), "team_abbr": abbr,
                        "down": p["down"], "distance": p["distance"], "yardline": p["yardline"],
                        "type": p["type"], "yards": p["yards"], "description": p["description"],
                        "result": p["result"]})

        if d.get("event"):
            ev = d["event"]
            score[team] += ev["points"]
            last = summary["plays_list"][-1] if summary["plays_list"] else {}
            if ev["type"] == "TD":
                scorer = last.get("scorer")
                if last.get("scorer_kind") == "rec" and scorer in box["rec"]:
                    box["pass_td"] += 1
                    box["rec"][scorer]["td"] += 1
                else:
                    box["rush_td"] += 1
                    if scorer in box["rush"]:
                        box["rush"][scorer]["td"] += 1
                conv = {0: " (PAT failed)", 1: "", 2: " (two-point conversion)"}.get(ev.get("convert", 1), "")
                detail = (last.get("description") or f"{rosters[team]['rbs'][0]} rush, TOUCHDOWN") + conv
            elif ev["type"] == "FG":
                detail = last.get("description") or f"{rosters[team]['k']} field goal is GOOD"
            else:
                detail = "Safety" if ev["points"] == 2 else "One-point safety"
            scoring.append({"quarter": q_label, "clock": _mmss(q_rem), "team_abbr": abbr,
                            "team_name": team, "type": ev["type"], "detail": detail,
                            "home_score": score[home], "away_score": score[away]})

        drive_rows.append({
            "team_abbr": abbr, "team_name": team, "quarter": q_label,
            "start": _yardline(start_yard), "plays": len(summary["plays_list"]),
            "yards": summary["yards"], "time": _mmss(int(drive_secs)), "result": d["result"],
        })
        elapsed += drive_secs

    # The decomposition guarantees the running score sums to the canonical final;
    # clamp defensively against any drift.
    score[home], score[away] = hs, as_

    return _finalize(st, g, res, user, universe, rosters, boxes, drive_rows,
                     scoring, pbp, overtime)


def _team_drives(events: list[dict[str, Any]], rng) -> list[dict[str, Any]]:
    """One drive per scoring event plus a handful of empty possessions (punts and
    a few giveaways), in rough chronological order."""
    drives: list[dict[str, Any]] = []
    for ev in events:
        result = "Touchdown" if ev["type"] == "TD" else (
            "Field Goal" if ev["type"] == "FG" else "Safety")
        drives.append({"result": result, "event": ev})
    punts = rng.randint(3, 5)
    giveaways = rng.choices([0, 1, 2, 3], weights=[34, 38, 20, 8])[0]
    for _ in range(punts):
        drives.append({"result": "Punt", "event": None})
    for _ in range(giveaways):
        drives.append({"result": rng.choice(["Interception", "Fumble"]), "event": None})
    if rng.random() < 0.4:
        drives.append({"result": "Missed FG", "event": None})
    rng.shuffle(drives)
    return drives


def _interleave(drives_by_team, home, away, rng) -> list[dict[str, Any]]:
    """Alternate possessions between the two teams, starting with a coin-flip
    receiver, tagging each drive with its team."""
    h = [{**d, "team": home} for d in drives_by_team[home]]
    a = [{**d, "team": away} for d in drives_by_team[away]]
    seq: list[dict[str, Any]] = []
    turn_home = rng.random() < 0.5
    while h or a:
        if turn_home and h:
            seq.append(h.pop(0))
        elif not turn_home and a:
            seq.append(a.pop(0))
        elif h:
            seq.append(h.pop(0))
        elif a:
            seq.append(a.pop(0))
        turn_home = not turn_home
    return seq


def _finalize(st, g, res, user, universe, rosters, boxes, drive_rows, scoring, pbp,
              overtime) -> dict[str, Any]:
    home, away = g["home"], g["away"]
    hs, as_ = res["home_score"], res["away_score"]

    # Normalize time of possession so the two teams sum to a full game.
    tsec = {t: max(1, boxes[t]["secs"]) for t in (home, away)}
    total = tsec[home] + tsec[away]
    top = {t: round(tsec[t] / total * 3600) for t in (home, away)}

    def team_stats(team: str) -> dict[str, Any]:
        b = boxes[team]
        pen = team_penalties(team)
        return {
            "points": hs if team == home else as_,
            "total_yards": b["pass_yards"] + b["rush_yards"],
            "pass_yards": b["pass_yards"], "rush_yards": b["rush_yards"],
            "first_downs": b["first_downs"],
            "third_down": f"{b['third_made']}-{b['third_att']}",
            "fourth_down": f"{b['fourth_made']}-{b['fourth_att']}",
            "red_zone": f"{b['rz_made']}-{b['rz_att']}",
            "turnovers": b["pass_int"] + b["fumbles_lost"],
            "sacks": b["sacks"],
            "penalties": f"{pen[0]}-{pen[1]}",
            "time_of_possession": _mmss(top[team]),
            "plays": b["plays"],
            "completions": b["completions"], "attempts": b["attempts"],
        }

    def team_penalties(team: str) -> tuple[int, int]:
        r = make_rng(st["seed"], st["year"], g["week"], team, "pen")
        n = r.choices([3, 4, 5, 6, 7, 8], weights=[14, 22, 24, 20, 12, 8])[0]
        return n, n * r.randint(7, 11)

    def player_box(team: str) -> dict[str, Any]:
        b, roster = boxes[team], rosters[team]
        passing = [{"name": roster["qb"], "c_att": f"{b['completions']}/{b['attempts']}",
                    "yards": b["pass_yards"], "td": b["pass_td"], "int": b["pass_int"]}]
        rushing = [{"name": n, "car": v["car"], "yards": v["yds"], "td": v["td"], "long": v["long"]}
                   for n, v in sorted(b["rush"].items(), key=lambda kv: -kv[1]["yds"])]
        receiving = [{"name": n, "rec": v["rec"], "yards": v["yds"], "td": v["td"], "long": v["long"]}
                     for n, v in sorted(b["rec"].items(), key=lambda kv: -kv[1]["yds"])]
        dr = make_rng(st["seed"], st["year"], g["week"], team, "defbox")
        defense = _defense_box(dr, roster, b)
        return {"passing": passing, "rushing": rushing, "receiving": receiving, "defense": defense}

    winner = home if hs > as_ else away
    return {
        "game_key": f"{g['week']}|{home}|{away}",
        "week": g["week"],
        "neutral": bool(g.get("neutral")),
        "overtime": overtime,
        "user_is_home": home == user,
        "home": {**_team_meta(universe, home), "score": hs},
        "away": {**_team_meta(universe, away), "score": as_},
        "final": {"home_score": hs, "away_score": as_, "overtime": overtime, "winner": winner},
        "team_stats": {"home": team_stats(home), "away": team_stats(away)},
        "box": {"home": player_box(home), "away": player_box(away)},
        "scoring_summary": scoring,
        "drives": drive_rows,
        "key_plays": _key_plays(scoring, pbp),
        "play_by_play": pbp,
    }


def _defense_box(r, roster: dict[str, Any], b: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic tackle/sack/INT line for the front, seeded so it is stable.
    Sacks and interceptions already accrued during play generation are folded in."""
    out: list[dict[str, Any]] = []
    names = roster["defense"]
    tackle_budget = r.randint(48, 66)
    weights = [r.uniform(0.5, 1.0) for _ in names]
    wsum = sum(weights) or 1
    for name, w in zip(names, weights):
        d = b["def"].get(name, {"tackles": 0, "sacks": 0.0, "tfl": 0, "int": 0, "pd": 0})
        out.append({
            "name": name,
            "tackles": d["tackles"] + round(tackle_budget * w / wsum),
            "sacks": round(d["sacks"], 1) if d["sacks"] % 1 else int(d["sacks"]),
            "tfl": d["tfl"] + (1 if r.random() < 0.4 else 0),
            "int": d["int"], "pd": d["pd"] + (1 if r.random() < 0.3 else 0),
        })
    out.sort(key=lambda x: -x["tackles"])
    return out


def _key_plays(scoring: list[dict[str, Any]], pbp: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turning points: every score, every turnover, and the longest gains."""
    keys: list[dict[str, Any]] = []
    for s in scoring:
        keys.append({"quarter": s["quarter"], "clock": s["clock"], "team_abbr": s["team_abbr"],
                     "description": s["detail"], "kind": s["type"]})
    for p in pbp:
        if p["result"] in ("Interception", "Fumble"):
            keys.append({"quarter": p["quarter"], "clock": p["clock"], "team_abbr": p["team_abbr"],
                         "description": p["description"], "kind": "Turnover"})
    big = sorted([p for p in pbp if p["type"] in ("run", "pass")],
                 key=lambda p: -p["yards"])[:3]
    for p in big:
        if p["yards"] >= 25:
            keys.append({"quarter": p["quarter"], "clock": p["clock"], "team_abbr": p["team_abbr"],
                         "description": p["description"], "kind": "Explosive"})
    return keys
