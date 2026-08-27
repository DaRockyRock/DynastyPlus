"""Game-data customization store (owned by the Simulator).

Team identity, the head coach, the program/NIL blueprint, the coaching staff,
the roster, recruits, the transfer portal, and rivals. This is the editable
identity layer the Simulator projects into the dynasty save file (see
sim/adapter.build_dynasty); the Dynasty+ companion reads it from the save, not
from here. Edited only by the Simulator app, persisted to
data/customization_game.json.

Shares all machinery with the media store via customization_base.Store.
"""
from __future__ import annotations

import json
from typing import Any

from . import config, roster_gen
from .customization_base import (
    DEALBREAKER_OPTS, STAGE_OPTS, YEAR_OPTS, Store, field as _f,
)

_STORE_FILE = config.DATA_DIR / "customization_game.json"

# =========================================================================
# DEFAULTS - canonical seed for the user's program.
# =========================================================================
DEFAULTS: dict[str, Any] = {
    # ---- Program identity ----
    "team": {
        "name": "Nebraska Cornhuskers",
        "school": "Nebraska",
        "nickname": "Cornhuskers",
        "abbreviation": "NEB",
        "espn_id": 158,
        "conference": "Big Ten",
        "color": "e41c38",
        "alt_color": "f5f5f5",
        "logo": "",
    },
    "head_coach": {
        "name": "Garrett Mason",
        "title": "Head Coach",
        "tenure_years": 3,
        "alma_mater": "Nebraska",
        "contract_through": 2030,
        "hot_seat": 8,
        "image": "",
    },
    "program": {
        "dynasty_points_total": 12000,
        "alloc_coaching_staff": 3800,
        "alloc_facilities": 4000,
        "alloc_nil": 4200,
        "recruiting_pool": 5500000,
        "roster_pool": 5000000,
        "weekly_recruiting_hours": config.WEEKLY_RECRUITING_HOURS,
        # Who the head coach replaced (optional). The Simulator generates the
        # program's prior-season history at dynasty start; if this is set, the
        # seasons before the user's tenure are attributed to this coach. The head
        # coach's tenure_years drives the "new coach's first season" angle (set it
        # to 1 for a first-year coach).
        "previous_coach": "",
    },

    # ---- People ----
    "coaching_staff": [
        {"name": "Garrett Mason", "role": "Head Coach", "notable": "3rd year, rebuilt the program culture", "image": ""},
        {"name": "Ricky Salomone", "role": "Offensive Coordinator", "notable": "Up-tempo spread, top-15 scoring offense", "image": ""},
        {"name": "Theo Brantley", "role": "Defensive Coordinator", "notable": "Aggressive 3-3-5, leads Big Ten in TFL", "image": ""},
        {"name": "Marcus Dell", "role": "Recruiting Coordinator", "notable": "Closer on the trail, Texas pipeline", "image": ""},
        {"name": "Pete Janowski", "role": "Special Teams Coordinator", "notable": "Top-10 net punting", "image": ""},
    ],
    # A full 85-man scholarship roster, generated deterministically by the
    # Simulator (roster_gen) the way CFB 27 ships every program a complete depth
    # chart. The coach's edits overlay this seed; the adapter writes it into the
    # save, and the NIL board / phone / archive read it straight from there.
    "players": roster_gen.build_roster(),

    # ---- Recruiting ----
    "commits": [
        {"name": "Jordan Eaves", "position": "QB", "stars": 4, "rating": 0.9412, "hometown": "Frisco, TX", "status": "Committed",
         "national_rank": 22, "expected_nil": 320000, "dealbreaker": "Playing Time", "stage": "Hard Commit", "interest": 96, "image": ""},
        {"name": "Travis McCallister", "position": "WR", "stars": 4, "rating": 0.9388, "hometown": "Bellevue, NE", "status": "Committed",
         "national_rank": 37, "expected_nil": 240000, "dealbreaker": "Proximity to Home", "stage": "Hard Commit", "interest": 95, "image": ""},
        {"name": "Demarcus Pope", "position": "EDGE", "stars": 4, "rating": 0.9201, "hometown": "Kansas City, MO", "status": "Committed",
         "national_rank": 65, "expected_nil": 210000, "dealbreaker": "Development", "stage": "Verbal", "interest": 84, "image": ""},
        {"name": "Owen Schaefer", "position": "OT", "stars": 4, "rating": 0.9105, "hometown": "Lincoln, NE", "status": "Committed",
         "national_rank": 88, "expected_nil": 160000, "dealbreaker": "Proximity to Home", "stage": "Hard Commit", "interest": 97, "image": ""},
        {"name": "Kj Mathis", "position": "CB", "stars": 3, "rating": 0.8899, "hometown": "Omaha, NE", "status": "Committed",
         "national_rank": 142, "expected_nil": 110000, "dealbreaker": "Playing Time", "stage": "Verbal", "interest": 82, "image": ""},
        {"name": "Tanner Ruhl", "position": "LB", "stars": 3, "rating": 0.8821, "hometown": "Grand Island, NE", "status": "Committed",
         "national_rank": 188, "expected_nil": 90000, "dealbreaker": "Proximity to Home", "stage": "Hard Commit", "interest": 94, "image": ""},
        {"name": "Isaiah Greer", "position": "RB", "stars": 3, "rating": 0.8654, "hometown": "Denver, CO", "status": "Committed",
         "national_rank": 174, "expected_nil": 95000, "dealbreaker": "Brand Exposure", "stage": "Verbal", "interest": 80, "image": ""},
    ],
    "targets": [
        {"name": "Cam Brooks-Lee", "position": "WR", "stars": 5, "national_rank": 8,
         "our_board_rank": 1,
         "leader": "Nebraska Cornhuskers", "predicted": "Nebraska Cornhuskers",
         "visit": "Official visit Week 10 (USC game)", "expected_nil": 450000, "dealbreaker": "Brand Exposure", "stage": "Top 3", "interest": 72, "image": ""},
        {"name": "Antoine Devereaux", "position": "S", "stars": 4, "national_rank": 44,
         "our_board_rank": 2,
         "leader": "Oregon Ducks", "predicted": "Oregon Ducks",
         "visit": "Took official to Oregon last weekend", "expected_nil": 180000, "dealbreaker": "Proximity to Home", "stage": "Top 5", "interest": 41, "image": ""},
        {"name": "Marquel Henderson", "position": "DT", "stars": 4, "national_rank": 76,
         "our_board_rank": 1,
         "leader": "Nebraska Cornhuskers", "predicted": "Undecided",
         "visit": "Game-day visit planned", "expected_nil": 220000, "dealbreaker": "Playing Time", "stage": "Top 3", "interest": 58, "image": ""},
        {"name": "Brody Vance", "position": "QB", "stars": 4, "national_rank": 31,
         "our_board_rank": 3,
         "leader": "Texas Longhorns", "predicted": "Texas Longhorns",
         "visit": "", "expected_nil": 300000, "dealbreaker": "Development", "stage": "Top 5", "interest": 33, "image": ""},
    ],

    # The transfer portal is no longer seeded here: it is fully simulated and owned
    # by the Simulator (backend/sim/portal.py), opens only in the offseason window,
    # and flows to Dynasty+ through the save (dynasty["transfer_portal"]). It is not
    # hand-editable, the same way the national recruiting board is not.

    # ---- Rivals ----
    "rivals": [
        {"name": "Iowa Hawkeyes", "record": "7-2", "rank": 19, "note": "Heroes Trophy on the line in the regular-season finale"},
        {"name": "Colorado Buffaloes", "record": "6-3", "rank": None, "note": "Nebraska survived 28-24 in Boulder back in Week 2"},
        {"name": "Wisconsin Badgers", "record": "6-3", "rank": None, "note": "Physical Week 11 road test in Madison"},
        {"name": "Minnesota Golden Gophers", "record": "7-2", "rank": None, "note": "Handed Nebraska its only loss, 23-20"},
    ],
}

# =========================================================================
# SCHEMA - the editor description for the game-data sections.
# =========================================================================
SCHEMA: list[dict[str, Any]] = [
    # ---------------- Program ----------------
    {
        "key": "team", "label": "Team Identity", "group": "Program", "icon": "shield",
        "blurb": "Your program's name, colors, and mark - shown everywhere in the app.",
        "kind": "object",
        "fields": [
            _f("name", "Full name", "text", width="full", placeholder="Nebraska Cornhuskers"),
            _f("school", "School", "text", width="half"),
            _f("nickname", "Nickname", "text", width="half"),
            _f("abbreviation", "Abbreviation", "text", width="half", maxLength=5),
            _f("conference", "Conference", "team_conference", width="half"),
            _f("espn_id", "ESPN team id", "number", width="half", help="Drives the default logo. Leave as-is to keep the real mark."),
            _f("color", "Primary color", "color", width="half"),
            _f("alt_color", "Secondary color", "color", width="half"),
            _f("logo", "Custom logo", "image", width="full", help="Optional. Overrides the ESPN logo across the app."),
        ],
    },
    {
        "key": "head_coach", "label": "Head Coach", "group": "Program", "icon": "whistle",
        "blurb": "The face of your program.",
        "kind": "object", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("title", "Title", "text", width="half"),
            _f("tenure_years", "Tenure (years)", "number", width="half"),
            _f("contract_through", "Contract through", "number", width="half"),
            _f("alma_mater", "Alma mater", "text", width="half"),
            _f("hot_seat", "Hot seat", "percent", width="half", help="0 = ice cold, 100 = on the chopping block."),
        ],
    },
    {
        "key": "program", "label": "Program Blueprint", "group": "Program", "icon": "chart",
        "blurb": "Dynasty Points budget, NIL war chest, and weekly recruiting hours.",
        "kind": "object",
        "fields": [
            _f("dynasty_points_total", "Dynasty Points (total)", "number", width="half"),
            _f("weekly_recruiting_hours", "Weekly recruiting hours", "number", width="half"),
            _f("alloc_coaching_staff", "DP: Coaching Staff", "number", width="third"),
            _f("alloc_facilities", "DP: Facilities", "number", width="third"),
            _f("alloc_nil", "DP: NIL", "number", width="third"),
            _f("recruiting_pool", "Recruiting NIL pool", "money", width="half"),
            _f("roster_pool", "Roster NIL pool", "money", width="half"),
            _f("previous_coach", "Previous head coach", "text", width="half",
               help="Who your coach replaced (optional). The Simulator generates the program's prior-season history; a first-year coach has Tenure = 1."),
        ],
    },
    {
        "key": "rivals", "label": "Rivals", "group": "Program", "icon": "swords",
        "blurb": "The programs that get your fans out of their seats.",
        "kind": "list", "item_kind": "Rival", "title_field": "name", "subtitle_field": "record", "team_field": "name",
        "fields": [
            _f("name", "Team", "team", width="full"),
            _f("record", "Record", "text", width="half", placeholder="7-2"),
            _f("rank", "Rank", "number", width="half", help="Leave blank if unranked."),
            _f("note", "Storyline", "textarea", width="full"),
        ],
    },

    # ---------------- People ----------------
    {
        "key": "coaching_staff", "label": "Coaching Staff", "group": "People", "icon": "clipboard",
        "blurb": "Your coordinators and position coaches.",
        "kind": "list", "item_kind": "Coach", "title_field": "name", "subtitle_field": "role", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("role", "Role", "text", width="half"),
            _f("notable", "Notable", "textarea", width="full"),
        ],
    },
    {
        "key": "players", "label": "Roster", "group": "People", "icon": "jersey",
        "blurb": "Your key players, their ratings, NIL, and retention risk.",
        "kind": "list", "item_kind": "Player", "title_field": "name", "subtitle_field": "position", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("position", "Position", "text", width="quarter"),
            _f("jersey", "Jersey", "number", width="quarter"),
            _f("year", "Class", "select", width="quarter", options=YEAR_OPTS),
            _f("rating", "Overall", "number", width="quarter", min=40, max=99),
            _f("depth_chart_slot", "Depth chart slot", "text", width="full", help='e.g. "Starting Quarterback", "Backup Running Back". Shown on the phone contact list.'),
            _f("stat_line", "Stat line", "text", width="full"),
            _f("note", "Scouting note", "textarea", width="full"),
            _f("draft_stock", "Draft stock", "text", width="full", help="Leave blank for non-prospects."),
            _f("expected_nil", "Expected NIL", "money", width="half"),
            _f("current_nil", "Current NIL", "money", width="half"),
            _f("risk_of_leaving", "Risk of leaving", "percent", width="half"),
            _f("dealbreaker", "Dealbreaker", "select", width="half", options=DEALBREAKER_OPTS),
        ],
    },

    # ---------------- Recruiting ----------------
    {
        "key": "commits", "label": "Commits", "group": "Recruiting", "icon": "star",
        "blurb": "Prospects in your incoming class.",
        "kind": "list", "item_kind": "Commit", "title_field": "name", "subtitle_field": "position", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("position", "Position", "text", width="quarter"),
            _f("stars", "Stars", "stars", width="quarter"),
            _f("national_rank", "National rank", "number", width="quarter", help="Overall prospect ranking. Shown on the phone contact list."),
            _f("rating", "Rating", "rating", width="half", min=0, max=1, step=0.0001, help="247-style composite, 0 to 1."),
            _f("hometown", "Hometown", "text", width="half"),
            _f("stage", "Stage", "select", width="half", options=STAGE_OPTS),
            _f("interest", "Interest", "percent", width="half"),
            _f("expected_nil", "Expected NIL", "money", width="half"),
            _f("dealbreaker", "Dealbreaker", "select", width="half", options=DEALBREAKER_OPTS),
            _f("status", "Status", "text", width="full"),
        ],
    },
    {
        "key": "targets", "label": "Targets", "group": "Recruiting", "icon": "target",
        "blurb": "Uncommitted prospects you are chasing.",
        "kind": "list", "item_kind": "Target", "title_field": "name", "subtitle_field": "position", "image_field": "image",
        "fields": [
            _f("image", "Photo", "image", width="full"),
            _f("name", "Name", "text", width="half"),
            _f("position", "Position", "text", width="quarter"),
            _f("stars", "Stars", "stars", width="quarter"),
            _f("national_rank", "National rank", "number", width="quarter", help="Overall prospect ranking. Shown on the phone contact list."),
            _f("our_board_rank", "Our board rank", "number", width="quarter", help="Where Nebraska ranks on this recruit's board (1 = top choice). Shown on the phone contact list."),
            _f("leader", "Leader", "team", width="half"),
            _f("predicted", "Predicted to", "team", width="half"),
            _f("stage", "Stage", "select", width="half", options=STAGE_OPTS),
            _f("interest", "Interest", "percent", width="half"),
            _f("expected_nil", "Expected NIL", "money", width="half"),
            _f("dealbreaker", "Dealbreaker", "select", width="half", options=DEALBREAKER_OPTS),
            _f("visit", "Visit notes", "textarea", width="full"),
        ],
    },

]

PERSONA_SECTIONS: dict[str, tuple[str, str]] = {
    "head_coach": ("generated", "head coach"),
    "coaching_staff": ("generated", "coach"),
    "players": ("generated", "player"),
    "commits": ("generated", "recruit"),
    "targets": ("generated", "recruit"),
}


def _migrate_from_combined() -> None:
    """One-time: seed this store from the old combined customization.json, which
    held game + media edits together before the split. Copies any game-section
    edits across so a user's existing team/roster/rival customizations survive.
    Non-destructive: leaves the old file alone (its stale game keys are ignored
    by the trimmed media store)."""
    if _STORE_FILE.exists():
        return
    old = config.DATA_DIR / "customization.json"
    if not old.exists():
        return
    try:
        with old.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return
    if not isinstance(data, dict):
        return
    carried = {k: v for k, v in data.items() if k in DEFAULTS}
    if not carried:
        return
    try:
        with _STORE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(carried, fh, indent=2)
    except OSError:
        pass


_migrate_from_combined()

_store = Store(store_file=_STORE_FILE, defaults=DEFAULTS, schema=SCHEMA,
               persona_sections=PERSONA_SECTIONS)

# Module-level delegating API (kept stable for sim/adapter + the Simulator app).
section = _store.section
load = _store.load
get_state = _store.get_state
generate_person = _store.generate_person
set_section = _store.set_section
reset_section = _store.reset_section
reset_all = _store.reset_all


def team() -> dict[str, Any]:
    return section("team")


def head_coach() -> dict[str, Any]:
    return section("head_coach")


def program() -> dict[str, Any]:
    return section("program")
