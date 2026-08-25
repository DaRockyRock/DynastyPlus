"""Player season-stat accrual and the Heisman / stat-leader board.

Hybrid model (per the design): we do not generate a full box score for every
player. Instead each team carries a small star set (QB, RB, WR, EDGE) and each
played game's team output is distributed into those stars' lines, accumulated
into season totals. The user's stars are their customization key_players (mapped
by position); every other team gets deterministic fictional stars.

Everything is recomputed from the stored game results up to a given week, so the
Heisman race and stat leaders move week to week and stay deterministic. Team
aggregates (points for/against, yards, turnover margin) come out of the same
pass so the adapter can rank the user nationally.
"""
from __future__ import annotations

from typing import Any

from .engine import make_rng

FIRST_NAMES = [
    "Marcus", "DeShawn", "Tyrell", "Cole", "Jalen", "Brock", "Eli", "Quinn", "Jamal",
    "Trey", "Xavier", "Cam", "Devin", "Isaiah", "Malik", "Drew", "Hunter", "Carter",
    "Jaylen", "Tre", "Bo", "Kade", "Rashad", "Donovan", "Micah", "Silas", "Gavin",
    "Roman", "Dante", "Knox", "Beau", "Zion", "Amari", "Cooper", "Maddox", "Tank",
]
LAST_NAMES = [
    "Whitfield", "Carter", "Banks", "Vermeer", "Ross", "Hentges", "Sorenson", "Holloway",
    "Pickens", "Mercer", "Vaughn", "Okafor", "Delgado", "Brooks", "Salazar", "Pruitt",
    "Ashby", "Calhoun", "Reyes", "Mceachern", "Tillman", "Fontaine", "Boudreaux", "Hargrove",
    "Stallworth", "Kowalski", "Adeyemi", "Lindqvist", "Vance", "Driskell", "Cromartie", "Yarbrough",
]

STAR_POSITIONS = ["QB", "RB", "WR", "EDGE"]


def _gen_name(seed: int, team: str, position: str) -> str:
    rng = make_rng(seed, "name", team, position)
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _user_stars(user_players: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Pick the user's best player at each star position from customization."""
    pos_map = {"QB": "QB", "RB": "RB", "WR": "WR", "EDGE": "EDGE", "DE": "EDGE", "OLB": "EDGE"}
    best: dict[str, dict[str, Any]] = {}
    for p in user_players or []:
        slot = pos_map.get((p.get("position") or "").upper())
        if not slot:
            continue
        if slot not in best or (p.get("rating", 0) > best[slot].get("rating", 0)):
            best[slot] = p
    return best


def _stars_for(team: str, info: dict[str, Any], seed: int,
               user_players: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    stars: dict[str, dict[str, Any]] = {}
    user_best = _user_stars(user_players) if info.get("is_user") else {}
    for pos in STAR_POSITIONS:
        up = user_best.get(pos)
        name = up.get("name") if up else _gen_name(seed, team, pos)
        stars[pos] = {"name": name, "position": pos, "team": team,
                      "pass_yds": 0, "pass_td": 0, "int": 0, "rush_yds": 0, "rush_td": 0,
                      "rec": 0, "rec_yds": 0, "rec_td": 0, "sacks": 0.0, "tackles": 0, "games": 0}
    return stars


def _accrue_offense(stars: dict[str, dict[str, Any]], points: int, rng) -> None:
    total_yds = max(120, min(720, rng.gauss(330 + (points - 24) * 6, 55)))
    pass_share = rng.uniform(0.45, 0.72)
    pass_yds = total_yds * pass_share
    rush_yds = total_yds * (1 - pass_share)
    tds = max(0, round(points / 7 * rng.uniform(0.7, 1.0)))
    pass_td = round(tds * pass_share)
    rush_td = max(0, tds - pass_td)
    ints = rng.choices([0, 1, 2, 3], weights=[50, 32, 14, 4])[0]

    qb, rb, wr = stars["QB"], stars["RB"], stars["WR"]
    qb["pass_yds"] += round(pass_yds); qb["pass_td"] += pass_td; qb["int"] += ints
    qb["rush_yds"] += round(rush_yds * rng.uniform(0.08, 0.2))
    rb["rush_yds"] += round(rush_yds * rng.uniform(0.55, 0.75)); rb["rush_td"] += rush_td
    rec_yds = round(pass_yds * rng.uniform(0.28, 0.4))
    wr["rec_yds"] += rec_yds; wr["rec"] += max(1, round(rec_yds / 14)); wr["rec_td"] += round(pass_td * 0.4)
    for s in (qb, rb, wr):
        s["games"] += 1


def _accrue_defense(stars: dict[str, dict[str, Any]], opp_points: int, rng) -> None:
    edge = stars["EDGE"]
    # Stingier defenses (fewer points allowed) generate more pressure.
    edge["sacks"] += round(rng.gauss(2.4 - opp_points * 0.02, 0.8), 1)
    edge["sacks"] = max(0.0, edge["sacks"])
    edge["tackles"] += rng.randint(3, 9)
    edge["games"] += 1


def _stat_line(p: dict[str, Any]) -> str:
    pos = p["position"]
    if pos == "QB":
        return f"{p['pass_yds']:,} yds, {p['pass_td']} TD, {p['int']} INT, {p['rush_yds']} rush"
    if pos == "RB":
        return f"{p['rush_yds']:,} yds, {p['rush_td']} TD"
    if pos == "WR":
        return f"{p['rec']} rec, {p['rec_yds']:,} yds, {p['rec_td']} TD"
    return f"{p['sacks']:g} sacks, {p['tackles']} tackles"


def _heisman_score(p: dict[str, Any], team_wins: int) -> float:
    # QB/RB carry the race the way the real award does; a defender almost never
    # cracks the front of it, so EDGE is heavily discounted.
    pos = p["position"]
    if pos == "QB":
        base = p["pass_yds"] * 0.05 + p["pass_td"] * 5 - p["int"] * 3 + p["rush_yds"] * 0.07 + p["rush_td"] * 5
    elif pos == "RB":
        base = (p["rush_yds"] * 0.08 + p["rush_td"] * 6 + p["rec_yds"] * 0.05) * 0.95
    elif pos == "WR":
        base = (p["rec_yds"] * 0.08 + p["rec_td"] * 6) * 0.92
    else:
        base = (p["sacks"] * 7 + p["tackles"] * 0.3) * 0.45
    return base + team_wins * 8


def compute(universe: dict[str, dict[str, Any]], schedule: list[dict[str, Any]],
            results: dict[str, dict[str, Any]], up_to_week: int, *, seed: int, year: int,
            user_players: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Season stats reflecting all games before up_to_week."""
    stars: dict[str, dict[str, dict[str, Any]]] = {
        name: _stars_for(name, info, seed, user_players) for name, info in universe.items()
    }
    agg: dict[str, dict[str, Any]] = {
        name: {"games": 0, "wins": 0, "losses": 0, "pf": 0, "pa": 0,
               "pass_yds": 0, "rush_yds": 0, "giveaways": 0, "takeaways": 0}
        for name in universe
    }

    for g in schedule:
        if g["week"] >= up_to_week:
            continue
        res = results.get(_key(g))
        if not res:
            continue
        home, away = g["home"], g["away"]
        hs, as_ = res["home_score"], res["away_score"]
        for team, pts, opp_pts in ((home, hs, as_), (away, as_, hs)):
            if team not in stars:
                continue
            rng = make_rng(seed, year, g["week"], "stat", team)
            before_int = stars[team]["QB"]["int"]
            _accrue_offense(stars[team], pts, rng)
            _accrue_defense(stars[team], opp_pts, rng)
            a = agg[team]
            a["games"] += 1
            a["pf"] += pts
            a["pa"] += opp_pts
            a["wins"] += 1 if pts > opp_pts else 0
            a["losses"] += 1 if pts < opp_pts else 0
            a["giveaways"] += stars[team]["QB"]["int"] - before_int
            a["takeaways"] += rng.choices([0, 1, 2, 3], weights=[44, 34, 17, 5])[0]

    # Roll team passing/rushing yard totals straight off the QB/RB lines.
    for name, a in agg.items():
        a["pass_yds"] = stars[name]["QB"]["pass_yds"]
        a["rush_yds"] = stars[name]["RB"]["rush_yds"] + stars[name]["QB"]["rush_yds"]
        a["total_yds"] = a["pass_yds"] + a["rush_yds"]
        a["margin"] = a["takeaways"] - a["giveaways"]

    # Flatten players, attach stat line + heisman score.
    players: list[dict[str, Any]] = []
    for name, group in stars.items():
        wins = agg[name]["wins"]
        for p in group.values():
            if p["games"] == 0:
                continue
            p = dict(p)
            p["stat_line"] = _stat_line(p)
            p["heisman"] = _heisman_score(p, wins)
            players.append(p)

    players.sort(key=lambda p: p["heisman"], reverse=True)
    # Carry the stat line (and games played) on each frontrunner so national
    # coverage can cite the numbers behind the race, not just the name.
    heisman = [{"name": p["name"], "team": p["team"], "position": p["position"],
                "stat_line": p["stat_line"], "games": p["games"]}
               for p in players[:5]]

    return {"teams": agg, "players": players, "heisman": heisman,
            "leaders": _leaders(players)}


def _leaders(players: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    def top(pos: str, key) -> list[dict[str, Any]]:
        pool = [p for p in players if p["position"] == pos]
        pool.sort(key=key, reverse=True)
        return pool[:5]
    return {
        "passing": top("QB", lambda p: p["pass_yds"]),
        "rushing": top("RB", lambda p: p["rush_yds"]),
        "receiving": top("WR", lambda p: p["rec_yds"]),
        "sacks": top("EDGE", lambda p: p["sacks"]),
    }


def _key(g: dict[str, Any]) -> str:
    return f"{g['week']}|{g['home']}|{g['away']}"
