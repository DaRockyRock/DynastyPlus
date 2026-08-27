"""Dynasty state schema.

This is the contract between the save-file layer and the generation layer.
Until the CFB 27 PC save format is reverse engineered (game expected July
2026 on Steam), the app accepts a structured JSON object shaped like this.
The mock data generator produces a conforming object for development.

The schema is intentionally permissive: generation modules pull what they
need and tolerate missing fields. `validate()` checks the handful of fields
the pipeline depends on rather than enforcing every key.
"""
from __future__ import annotations

from typing import Any

# A human-readable description of the schema, surfaced via the API so the
# frontend / future save parser knows the target shape.
SCHEMA_DESCRIPTION: dict[str, Any] = {
    "meta": {
        "generated_at": "ISO-8601 timestamp",
        "source": "mock | save",
        "app_version": "string",
        "dynasty_id": "string, stable unique id for this dynasty/world (the companion scopes all per-dynasty data to it)",
    },
    "season": {
        "year": "int, e.g. 2026",
        "week": "int, 0 = preseason",
        "week_label": "string, e.g. 'Week 10'",
        "phase": "preseason | regular | conf_championship | bowls | playoff | offseason",
    },
    "team": {
        "name": "Full team name, e.g. 'Nebraska Cornhuskers'",
        "school": "School name, e.g. 'Nebraska'",
        "nickname": "Mascot, e.g. 'Cornhuskers'",
        "abbreviation": "3-letter, e.g. 'NEB'",
        "espn_id": "ESPN team id for logo lookup",
        "conference": "string",
        "division": "string or null",
        "record": {"overall": "W-L", "conference": "W-L", "streak": "string"},
        "head_coach": {
            "name": "string",
            "title": "Head Coach",
            "tenure_years": "int",
            "alma_mater": "string",
            "contract_through": "int year",
            "hot_seat": "0-100 heat index",
        },
        "rankings": {"cfp": "int or null", "ap": "int or null", "coaches": "int or null"},
        "stats": {
            "points_per_game": "float",
            "points_allowed": "float",
            "yards_per_game": "float",
            "turnover_margin": "int",
        },
    },
    "coaching_staff": [
        {"name": "string", "role": "OC | DC | etc", "notable": "string"},
    ],
    "roster": {
        "key_players": [
            {
                "name": "string",
                "position": "string",
                "year": "FR | SO | JR | SR",
                "jersey": "int",
                "rating": "int 0-99",
                "stat_line": "string",
                "note": "string",
                "draft_stock": "string or null",
                # Roster NIL (retention). Dollars per season.
                "expected_nil": "int dollars the player expects",
                "current_nil": "int dollars currently paid",
                "risk_of_leaving": "0-100 (higher = more likely to leave)",
                "dealbreaker": "string, what they weigh most (e.g. 'Brand Exposure')",
            }
        ]
    },
    # Program budget. Dynasty Points are the annual currency allocated across
    # coaching staff / facilities / NIL; the NIL allocation funds the dollar war
    # chest split into recruiting_pool + roster_pool. dp_per_dollar converts a
    # dollar NIL offer into the Dynasty Points it draws from your balance.
    "nil": {
        "dynasty_points": {
            "total": "int",
            "allocations": {"coaching_staff": "int", "facilities": "int", "nil": "int"},
        },
        "recruiting_pool": "int dollars",
        "roster_pool": "int dollars",
        "weekly_recruiting_hours": "int",
        "dp_per_dollar": "float",
    },
    "recruiting": {
        "class_rank_national": "int",
        "class_rank_conference": "int",
        "commits": [
            {
                "name": "string",
                "position": "string",
                "stars": "int 2-5",
                "rating": "float 0-1",
                "hometown": "string",
                "status": "Committed | Enrolled",
                # Recruiting NIL. expected_nil in dollars/season.
                "expected_nil": "int",
                "dealbreaker": "string",
                "stage": "Open | Top 5 | Top 3 | Verbal | Hard Commit",
                "interest": "0-100 momentum toward this program",
            }
        ],
        "targets": [
            {
                "name": "string",
                "position": "string",
                "stars": "int 2-5",
                "leader": "school name",
                "predicted": "school name",
                "visit": "string or null",
                "expected_nil": "int",
                "dealbreaker": "string",
                "stage": "Open | Top 5 | Top 3 | Verbal | Hard Commit",
                "interest": "0-100 momentum toward this program",
            }
        ],
    },
    # Sim-derived transfer portal. Closed and empty during the regular season; the
    # market opens in the offseason window. `window.open` says whether it is live.
    "transfer_portal": {
        "window": {"open": "bool", "label": "string", "opened_week": "int or null"},
        "incoming": [{"name": "string", "position": "string", "from": "school", "ovr": "int", "stars": "int", "expected_nil": "int", "status": "Committed | Enrolled"}],
        "outgoing": [{"name": "string", "position": "string", "to": "school or 'Undecided'", "ovr": "int", "reason": "string"}],
        "targets": [{"name": "string", "position": "string", "from": "school", "ovr": "int", "stars": "int", "expected_nil": "int", "interest": "0-100", "stage": "string", "leader": "school"}],
        "class_grade": {"grade": "string", "gpa": "float", "summary": "string"},
    },
    "schedule": {
        "recent_results": [
            {
                "week": "int",
                "opponent": "string",
                "opponent_abbr": "string",
                "opponent_espn_id": "int",
                "home": "bool",
                "result": "W | L",
                "score": "e.g. '34-17'",
                "rank_matchup": "string or null",
            }
        ],
        "upcoming": {
            "week": "int",
            "opponent": "string",
            "opponent_abbr": "string",
            "opponent_espn_id": "int",
            "opponent_record": "W-L",
            "opponent_rank": "int or null",
            "home": "bool",
            "kickoff": "string",
            "tv": "string",
            "spread": "string",
        },
    },
    "rivals": [
        {
            "name": "string",
            "abbreviation": "string",
            "espn_id": "int",
            "record": "W-L",
            "rank": "int or null",
            "note": "string",
        }
    ],
    "conference_standings": [
        {"team": "string", "abbr": "string", "espn_id": "int", "conf_record": "W-L", "overall": "W-L"}
    ],
    "national": {
        "ap_top25": [{"rank": "int", "team": "string", "abbr": "string", "espn_id": "int", "record": "W-L"}],
        "cfp_top12": [{"rank": "int", "team": "string", "abbr": "string", "espn_id": "int", "record": "W-L"}],
        "heisman_frontrunners": [{"name": "string", "team": "string", "position": "string"}],
        # The full FBS slate for the current week. The companion ranks these
        # client-side into the home page's marquee matchups.
        "scoreboard": [
            {
                "week": "int",
                "home": {"name": "string", "abbr": "string", "espn_id": "int", "record": "W-L", "rank": "AP rank int or null"},
                "away": {"name": "string", "abbr": "string", "espn_id": "int", "record": "W-L", "rank": "AP rank int or null"},
                "conference_game": "bool",
                "neutral": "bool",
                "user": "bool, true when the user's team is in this game",
                "status": "final | scheduled",
                "home_score": "int or null",
                "away_score": "int or null",
                "line": "betting line string, e.g. 'OSU -3.5' or 'EVEN'",
            }
        ],
    },
    # The program's prior seasons (most recent first), so the companion opens on
    # the real landscape: last year's results and the coaching change. user_coached
    # marks the seasons the current head coach was in charge.
    "history": [
        {
            "year": "int",
            "coach": "string",
            "user_coached": "bool",
            "overall": "W-L",
            "final_rank": "int or null",
            "conference_finish": "string",
            "postseason": "string",
            "result": "string (e.g. 'Played in a bowl game')",
        }
    ],
}

# Fields the pipeline genuinely relies on.
REQUIRED_PATHS = [
    ("season", "year"),
    ("season", "week"),
    ("team", "name"),
]


def validate(dynasty: dict) -> list[str]:
    """Return a list of human-readable problems. Empty list == valid enough."""
    problems: list[str] = []
    if not isinstance(dynasty, dict):
        return ["dynasty payload is not an object"]
    for path in REQUIRED_PATHS:
        node: Any = dynasty
        ok = True
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                ok = False
                break
        if not ok:
            problems.append("missing required field: " + ".".join(path))
    return problems
