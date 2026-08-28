"""Minimal state contract shared by the CFB 27 save reader and Tools UI.

Every value comes from a real dynasty save or its matching game profile. The
editors tolerate optional blocks when a save does not expose that data yet.
"""
from __future__ import annotations

from typing import Any


SCHEMA_DESCRIPTION: dict[str, Any] = {
    "meta": {
        "source": "save",
        "generated_at": "save timestamp",
        "dynasty_id": "stable id for this save file",
        "hash": "change marker for this save file",
    },
    "season": {
        "year": "season year",
        "week": "current week number",
        "week_label": "display label",
        "phase": "preseason, regular, conference championship, bowls, playoff, or offseason",
    },
    "team": {
        "name": "full team name",
        "school": "school name",
        "nickname": "team nickname",
        "abbreviation": "team abbreviation",
        "espn_id": "team art id",
        "conference": "conference name",
        "record": "current record",
        "rankings": "current CFP and AP ranks",
    },
    "all_teams": "teams available to the editors",
    "schedule": "recent results, upcoming game, and rivalry-week results",
    "conference_standings": "current conference records",
    "conference_champions": "completed conference championship winners",
    "national": "current polls and scoreboard",
}


REQUIRED_PATHS = [
    ("season", "year"),
    ("season", "week"),
    ("team", "name"),
]


def validate(dynasty: dict) -> list[str]:
    """Return validation problems; an empty list means the save is usable."""
    if not isinstance(dynasty, dict):
        return ["dynasty payload is not an object"]
    problems: list[str] = []
    for path in REQUIRED_PATHS:
        node: Any = dynasty
        for key in path:
            if not isinstance(node, dict) or key not in node:
                problems.append("missing required field: " + ".".join(path))
                break
            node = node[key]
    return problems
