"""Mock dynasty state generator.

Produces a realistic Nebraska Cornhuskers dynasty state so the full app can be
built and exercised before the CFB 27 PC save format exists. Players, coaches,
and recruits are fictional (this is a dynasty universe), while team metadata,
colors, and logos resolve to real schools via the ESPN-backed teams module.

`generate(week=...)` returns a schema-conforming dict. The same week always
produces the same state (deterministic), so caching and week navigation behave
sensibly during development.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from . import config, customization_game as customization, teams

SEASON_YEAR = 2026

# The program name the static polls/standings are seeded with. If the user
# renames their team in the customization store, generate() swaps this one entry
# in the rankings to the new identity.
DEFAULT_TEAM_NAME = "Nebraska Cornhuskers"

# Nebraska's scripted 12-game slate for the mock season. opponent names match
# the teams module so logos/colors resolve.
SCHEDULE = [
    {"week": 1, "opp": "UTEP Miners", "abbr": "UTEP", "espn": 2638, "home": True, "result": "W", "score": "41-10", "rank": None},
    {"week": 2, "opp": "Colorado Buffaloes", "abbr": "COLO", "espn": 38, "home": False, "result": "W", "score": "28-24", "rank": "#22 Colorado"},
    {"week": 3, "opp": "Houston Cougars", "abbr": "HOU", "espn": 248, "home": True, "result": "W", "score": "45-17", "rank": None},
    {"week": 4, "opp": "Michigan Wolverines", "abbr": "MICH", "espn": 130, "home": True, "result": "W", "score": "31-27", "rank": "#9 Michigan"},
    {"week": 5, "opp": "Rutgers Scarlet Knights", "abbr": "RUT", "espn": 164, "home": False, "result": "W", "score": "38-13", "rank": None},
    {"week": 6, "opp": "Maryland Terrapins", "abbr": "MD", "espn": 120, "home": True, "result": "W", "score": "34-20", "rank": None},
    {"week": 7, "opp": "Minnesota Golden Gophers", "abbr": "MINN", "espn": 135, "home": False, "result": "L", "score": "20-23", "rank": None},
    {"week": 8, "opp": "Indiana Hoosiers", "abbr": "IND", "espn": 84, "home": True, "result": "W", "score": "30-13", "rank": "#15 Indiana"},
    {"week": 9, "opp": "Ohio State Buckeyes", "abbr": "OSU", "espn": 194, "home": False, "result": "W", "score": "27-24", "rank": "#3 Ohio State"},
    {"week": 10, "opp": "USC Trojans", "abbr": "USC", "espn": 30, "home": True, "result": None, "score": None, "rank": "#12 USC"},
    {"week": 11, "opp": "Wisconsin Badgers", "abbr": "WIS", "espn": 275, "home": False, "result": None, "score": None, "rank": None},
    {"week": 12, "opp": "Iowa Hawkeyes", "abbr": "IOWA", "espn": 2294, "home": True, "result": None, "score": None, "rank": "#19 Iowa"},
]

# The roster, coaching staff, recruits, transfer portal, rivals, and the NIL /
# Dynasty Points blueprint are all user-editable and live in customization.py
# (the single source of truth). generate() reads them at call time so edits in
# the Customize flow show up immediately. The constants below (schedule, polls,
# standings, Heisman field) remain scaffolding for the real-team rankings.

AP_TOP25 = [
    ("Georgia Bulldogs", "9-0"), ("Texas Longhorns", "9-0"), ("Ohio State Buckeyes", "8-1"),
    ("Oregon Ducks", "9-0"), ("Nebraska Cornhuskers", "8-1"), ("Alabama Crimson Tide", "8-1"),
    ("Penn State Nittany Lions", "8-1"), ("Notre Dame Fighting Irish", "8-1"), ("Michigan Wolverines", "7-2"),
    ("Tennessee Volunteers", "7-2"), ("Clemson Tigers", "8-1"), ("USC Trojans", "7-2"),
    ("LSU Tigers", "7-2"), ("Oklahoma Sooners", "7-2"), ("Indiana Hoosiers", "7-2"),
    ("Miami Hurricanes", "8-1"), ("Florida State Seminoles", "7-2"), ("Wisconsin Badgers", "6-3"),
    ("Iowa Hawkeyes", "7-2"), ("Florida Gators", "6-3"), ("Washington Huskies", "6-3"),
    ("UCLA Bruins", "6-3"), ("Maryland Terrapins", "6-3"), ("Minnesota Golden Gophers", "7-2"),
    ("Michigan State Spartans", "5-4"),
]

# CFP top 12 for the mock week (committee-style seeding).
CFP_TOP12 = [
    "Georgia Bulldogs", "Texas Longhorns", "Ohio State Buckeyes", "Oregon Ducks",
    "Nebraska Cornhuskers", "Alabama Crimson Tide", "Penn State Nittany Lions",
    "Notre Dame Fighting Irish", "Tennessee Volunteers", "Clemson Tigers",
    "Miami Hurricanes", "Indiana Hoosiers",
]

# Coaches poll: same 25 teams as AP, slightly reordered (coaches lean on
# tradition and head-to-head). Records are looked up from AP_TOP25.
COACHES_ORDER = [
    "Georgia Bulldogs", "Texas Longhorns", "Ohio State Buckeyes", "Alabama Crimson Tide", "Oregon Ducks",
    "Nebraska Cornhuskers", "Notre Dame Fighting Irish", "Penn State Nittany Lions", "Tennessee Volunteers",
    "Michigan Wolverines", "Clemson Tigers", "Oklahoma Sooners", "USC Trojans", "Indiana Hoosiers", "LSU Tigers",
    "Miami Hurricanes", "Florida State Seminoles", "Iowa Hawkeyes", "Wisconsin Badgers", "Washington Huskies",
    "Florida Gators", "Minnesota Golden Gophers", "UCLA Bruins", "Maryland Terrapins", "Michigan State Spartans",
]
AP_FIRST = {1: 44, 2: 13, 3: 5, 4: 2}
COACHES_FIRST = {1: 41, 2: 16, 3: 6, 4: 2}
AP_RECEIVING = [
    ("Kansas State Wildcats", 96), ("Texas A&M Aggies", 74), ("Ole Miss Rebels", 61),
    ("Missouri Tigers", 48), ("SMU Mustangs", 39), ("Pittsburgh Panthers", 27),
    ("Memphis Tigers", 18), ("Army Black Knights", 12), ("James Madison Dukes", 7), ("Kansas Jayhawks", 3),
]
COACHES_RECEIVING = [
    ("Texas A&M Aggies", 88), ("Kansas State Wildcats", 70), ("Missouri Tigers", 55),
    ("Ole Miss Rebels", 44), ("Boston College Eagles", 30), ("SMU Mustangs", 22),
    ("Memphis Tigers", 15), ("Illinois Fighting Illini", 9), ("Army Black Knights", 5), ("Kansas Jayhawks", 2),
]

HEISMAN = [
    {"name": "Marcus Whitfield", "team": "Nebraska Cornhuskers", "position": "QB",
     "stat_line": "2,615 yds, 24 TD, 4 INT, 318 rush", "games": 9},
    {"name": "Quinn Holloway", "team": "Texas Longhorns", "position": "QB",
     "stat_line": "2,540 yds, 23 TD, 5 INT, 211 rush", "games": 9},
    {"name": "Jamal Pickens", "team": "Georgia Bulldogs", "position": "RB",
     "stat_line": "1,388 yds, 16 TD", "games": 9},
    {"name": "Eli Sorenson", "team": "Oregon Ducks", "position": "QB",
     "stat_line": "2,402 yds, 21 TD, 3 INT, 140 rush", "games": 9},
]

# National statistical leaders, mirroring the sim's stat_leaders board so the
# offline / cold-start feed can cite the country's leaders by name and line.
STAT_LEADERS = {
    "passing": [
        {"name": "Marcus Whitfield", "team": "Nebraska Cornhuskers", "position": "QB", "stat_line": "2,615 yds, 24 TD, 4 INT"},
        {"name": "Quinn Holloway", "team": "Texas Longhorns", "position": "QB", "stat_line": "2,540 yds, 23 TD, 5 INT"},
        {"name": "Eli Sorenson", "team": "Oregon Ducks", "position": "QB", "stat_line": "2,402 yds, 21 TD, 3 INT"},
    ],
    "rushing": [
        {"name": "Jamal Pickens", "team": "Georgia Bulldogs", "position": "RB", "stat_line": "1,388 yds, 16 TD"},
        {"name": "Tank Boudreaux", "team": "Alabama Crimson Tide", "position": "RB", "stat_line": "1,205 yds, 13 TD"},
        {"name": "Tre Vaughn", "team": "Ohio State Buckeyes", "position": "RB", "stat_line": "1,142 yds, 11 TD"},
    ],
    "receiving": [
        {"name": "Xavier Mercer", "team": "Oregon Ducks", "position": "WR", "stat_line": "61 rec, 1,020 yds, 11 TD"},
        {"name": "Donovan Banks", "team": "Texas Longhorns", "position": "WR", "stat_line": "58 rec, 944 yds, 9 TD"},
        {"name": "Cam Ross", "team": "Penn State Nittany Lions", "position": "WR", "stat_line": "55 rec, 901 yds, 8 TD"},
    ],
    "sacks": [
        {"name": "Malik Calhoun", "team": "Clemson Tigers", "position": "EDGE", "stat_line": "11 sacks, 41 tackles"},
        {"name": "Roman Okafor", "team": "Georgia Bulldogs", "position": "EDGE", "stat_line": "10 sacks, 38 tackles"},
        {"name": "Knox Tillman", "team": "Michigan Wolverines", "position": "EDGE", "stat_line": "9.5 sacks, 44 tackles"},
    ],
}

# The national slate behind the mock week's scoreboard: (home, away, conference
# game, line). Records and AP ranks are looked up from AP_TOP25 at build time.
MOCK_SLATE = [
    ("Nebraska Cornhuskers", "USC Trojans", True, "NEB -6.5"),
    ("Texas Longhorns", "Georgia Bulldogs", True, "TEX -1.5"),
    ("Penn State Nittany Lions", "Ohio State Buckeyes", True, "OSU -2.5"),
    ("LSU Tigers", "Alabama Crimson Tide", True, "ALA -4"),
    ("Michigan Wolverines", "Oregon Ducks", True, "ORE -3"),
    ("Notre Dame Fighting Irish", "Tennessee Volunteers", False, "ND -5.5"),
    ("Florida State Seminoles", "Clemson Tigers", True, "CLEM -3.5"),
    ("Wisconsin Badgers", "Indiana Hoosiers", True, "IND -2.5"),
    ("Northwestern Wildcats", "Iowa Hawkeyes", True, "IOWA -7"),
    ("Kansas Jayhawks", "Kansas State Wildcats", True, "KSU -3"),
]
MOCK_SLATE_RECORDS = {"Northwestern Wildcats": "4-5", "Kansas Jayhawks": "5-4", "Kansas State Wildcats": "7-2"}


def _abbr(name: str) -> str:
    return teams.get_team(name).get("abbreviation") or name[:3].upper()


def _espn(name: str) -> Any:
    return teams.get_team(name).get("espn_id")


def _record_through(week: int) -> tuple[str, str, str]:
    """Compute Nebraska's overall/conference record and streak through a week."""
    wins = losses = cw = cl = 0
    streak_char = ""
    streak_len = 0
    non_conf = {"UTEP Miners", "Colorado Buffaloes", "Houston Cougars"}
    for g in SCHEDULE:
        if g["week"] >= week or g["result"] is None:
            continue
        is_conf = g["opp"] not in non_conf
        if g["result"] == "W":
            wins += 1
            cw += 1 if is_conf else 0
            if streak_char == "W":
                streak_len += 1
            else:
                streak_char, streak_len = "W", 1
        else:
            losses += 1
            cl += 1 if is_conf else 0
            if streak_char == "L":
                streak_len += 1
            else:
                streak_char, streak_len = "L", 1
    streak = f"{streak_char}{streak_len}" if streak_char else "-"
    return f"{wins}-{losses}", f"{cw}-{cl}", streak


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


def generate(week: int = 10, year: int = SEASON_YEAR) -> dict[str, Any]:
    """Return a schema-conforming Nebraska dynasty state for the given week."""
    overall, conf, streak = _record_through(week)

    # User-editable identity (from the customization store). The national
    # polls/standings below are seeded with the default program name; if the
    # user renamed their team, swap that one entry to the new identity so the
    # rankings still light up the user's row and resolve its logo.
    tm = customization.team()
    hc = customization.head_coach()
    prog = customization.program()
    _user_name = tm.get("name")

    def _remap(row: dict[str, Any]) -> dict[str, Any]:
        if _user_name and _user_name != DEFAULT_TEAM_NAME and row.get("team") == DEFAULT_TEAM_NAME:
            row = dict(row)
            row["team"] = _user_name
            if tm.get("abbreviation"):
                row["abbr"] = tm["abbreviation"]
            if tm.get("espn_id") is not None:
                row["espn_id"] = tm["espn_id"]
        return row

    recent = []
    for g in SCHEDULE:
        if g["result"] is None or g["week"] >= week:
            continue
        recent.append({
            "week": g["week"],
            "opponent": g["opp"],
            "opponent_abbr": g["abbr"],
            "opponent_espn_id": g["espn"],
            "home": g["home"],
            "result": g["result"],
            "score": g["score"],
            "rank_matchup": g["rank"],
        })
    recent = list(reversed(recent))[:5]

    upcoming_game = next((g for g in SCHEDULE if g["week"] == week), SCHEDULE[-1])
    upcoming = {
        "week": upcoming_game["week"],
        "opponent": upcoming_game["opp"],
        "opponent_abbr": upcoming_game["abbr"],
        "opponent_espn_id": upcoming_game["espn"],
        "opponent_record": "7-2",
        "opponent_rank": 12 if "USC" in upcoming_game["opp"] else None,
        "home": upcoming_game["home"],
        "kickoff": "Saturday 7:30 PM ET",
        "tv": "NBC / Peacock",
        "spread": "NEB -6.5",
    }

    rec_by_name = dict(AP_TOP25)

    def _poll(pairs, firsts):
        out = []
        for i, (name, rec) in enumerate(pairs):
            rank = i + 1
            out.append({
                "rank": rank, "team": name, "abbr": _abbr(name), "espn_id": _espn(name),
                "record": rec, "points": max(40, 1550 - (rank - 1) * 56),
                "first": firsts.get(rank),
            })
        return out

    def _receiving(items):
        return [{"team": n, "abbr": _abbr(n), "espn_id": _espn(n), "votes": v} for n, v in items]

    ap_rank = {name: i + 1 for i, (name, _r) in enumerate(AP_TOP25)}

    def _sb_side(name: str) -> dict[str, Any]:
        side = {
            "name": name, "abbr": _abbr(name), "espn_id": _espn(name),
            "record": rec_by_name.get(name) or MOCK_SLATE_RECORDS.get(name, "5-4"),
            "rank": ap_rank.get(name),
        }
        if _user_name and _user_name != DEFAULT_TEAM_NAME and name == DEFAULT_TEAM_NAME:
            side["name"] = _user_name
            if tm.get("abbreviation"):
                side["abbr"] = tm["abbreviation"]
            if tm.get("espn_id") is not None:
                side["espn_id"] = tm["espn_id"]
        return side

    scoreboard = []
    for home, away, conf_game, line in MOCK_SLATE:
        if DEFAULT_TEAM_NAME in (home, away) and _user_name != DEFAULT_TEAM_NAME and tm.get("abbreviation"):
            line = line.replace("NEB", tm["abbreviation"])  # follow a renamed user team
        scoreboard.append({
            "week": week, "home": _sb_side(home), "away": _sb_side(away),
            "conference_game": conf_game, "neutral": False,
            "user": DEFAULT_TEAM_NAME in (home, away),
            "status": "scheduled", "home_score": None, "away_score": None,
            "line": line,
        })

    ap_top25 = [_remap(r) for r in _poll(AP_TOP25, AP_FIRST)]
    coaches_top25 = [_remap(r) for r in _poll([(n, rec_by_name.get(n, "")) for n in COACHES_ORDER], COACHES_FIRST)]
    cfp_top12 = [
        _remap({"rank": i + 1, "team": t, "abbr": _abbr(t), "espn_id": _espn(t),
                "record": rec_by_name.get(t, "")})
        for i, t in enumerate(CFP_TOP12)
    ]

    return {
        "meta": {
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "source": "mock",
            "app_version": config.APP_VERSION,
        },
        "season": {
            "year": year,
            "week": week,
            "week_label": f"Week {week}",
            "phase": _phase(week),
        },
        "team": {
            "name": tm.get("name"),
            "school": tm.get("school"),
            "nickname": tm.get("nickname"),
            "abbreviation": tm.get("abbreviation"),
            "espn_id": tm.get("espn_id"),
            "color": tm.get("color"),
            "alt_color": tm.get("alt_color"),
            "logo": tm.get("logo") or None,
            "conference": tm.get("conference"),
            "division": None,
            "record": {"overall": overall, "conference": conf, "streak": streak},
            "head_coach": {
                "name": hc.get("name"),
                "title": hc.get("title"),
                "tenure_years": hc.get("tenure_years"),
                "alma_mater": hc.get("alma_mater"),
                "contract_through": hc.get("contract_through"),
                "hot_seat": hc.get("hot_seat"),
                "image": hc.get("image") or None,
            },
            "rankings": {"cfp": 5, "ap": 5, "coaches": 6},
            "stats": {
                "points_per_game": 33.4,
                "points_allowed": 18.9,
                "yards_per_game": 441.2,
                "turnover_margin": 9,
                "ranks": {
                    "points_per_game": {"national": 12, "conference": 3},
                    "points_allowed": {"national": 9, "conference": 2},
                    "yards_per_game": {"national": 15, "conference": 4},
                    "turnover_margin": {"national": 5, "conference": 1},
                },
            },
        },
        "coaching_staff": customization.section("coaching_staff"),
        "roster": {"key_players": customization.section("players")},
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
        "recruiting": {
            "class_rank_national": 14,
            "class_rank_conference": 4,
            "commits": customization.section("commits"),
            "targets": customization.section("targets"),
        },
        # The portal is sim-owned and opens only in the offseason window. The
        # no-sim mock fallback presents it closed and empty (matching the regular
        # season), so pure-mock dev never shows phantom week-1 portal moves.
        "transfer_portal": {
            "window": {"open": False, "label": "Closed", "opened_week": None},
            "incoming": [], "outgoing": [], "targets": [],
            "class_grade": {"grade": "NR", "gpa": 0.0,
                            "summary": "The transfer portal is closed during the season."},
        },
        "schedule": {"recent_results": recent, "upcoming": upcoming, "full": _full_schedule(week)},
        "rivals": [
            {"name": r["name"], "abbreviation": _abbr(r["name"]), "espn_id": _espn(r["name"]),
             "record": r.get("record"), "rank": r.get("rank"), "note": r.get("note")}
            for r in customization.section("rivals")
        ],
        "conference_standings": [_remap(r) for r in _standings()],
        "national": {
            "ap_top25": ap_top25,
            "coaches_top25": coaches_top25,
            "cfp_top12": cfp_top12,
            "ap_receiving_votes": _receiving(AP_RECEIVING),
            "coaches_receiving_votes": _receiving(COACHES_RECEIVING),
            "heisman_frontrunners": [_remap(h) for h in HEISMAN],
            "stat_leaders": STAT_LEADERS,
            "scoreboard": scoreboard,
        },
    }


def _full_schedule(week: int) -> list[dict[str, Any]]:
    out = []
    for g in SCHEDULE:
        played = g["result"] is not None and g["week"] < week
        out.append({
            "week": g["week"],
            "opponent": g["opp"],
            "opponent_abbr": g["abbr"],
            "opponent_espn_id": g["espn"],
            "home": g["home"],
            "result": g["result"] if played else None,
            "score": g["score"] if played else None,
            "rank_matchup": g["rank"],
            "status": "final" if played else ("next" if g["week"] == week else "upcoming"),
        })
    return out


def _standings() -> list[dict[str, Any]]:
    rows = [
        ("Ohio State Buckeyes", "6-1", "8-1"), ("Oregon Ducks", "6-0", "9-0"),
        ("Nebraska Cornhuskers", "5-1", "8-1"), ("Penn State Nittany Lions", "5-1", "8-1"),
        ("Indiana Hoosiers", "5-1", "7-2"), ("Michigan Wolverines", "5-2", "7-2"),
        ("USC Trojans", "5-2", "7-2"), ("Minnesota Golden Gophers", "4-2", "7-2"),
        ("Iowa Hawkeyes", "4-2", "7-2"), ("Wisconsin Badgers", "3-3", "6-3"),
    ]
    return [
        {"team": t, "abbr": _abbr(t), "espn_id": _espn(t), "conf_record": c, "overall": o}
        for t, c, o in rows
    ]
