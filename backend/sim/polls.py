"""Emergent national rankings.

AP top 25, Coaches top 25, CFP top 12, and receiving votes, all computed from
the season's stored results rather than scripted. A team's poll score blends its
season rating, its record (wins reward, losses punish harder), and a resume term
(the average rating of the teams it has actually beaten) so strength of schedule
separates contenders. Before any games are played the polls fall back to rating
plus prestige, which gives a sensible preseason top 25.

Row shapes mirror the static mock exactly so the rankings UI is unchanged:
poll rows are {rank, team, abbr, espn_id, record, points, first}; CFP rows drop
points/first; receiving rows are {team, abbr, espn_id, votes}.
"""
from __future__ import annotations

from typing import Any

FIRST_VOTES = {1: 45, 2: 12, 3: 5, 4: 2}


def _quality(beaten: list[str], universe: dict[str, dict[str, Any]]) -> float:
    if not beaten:
        return 0.0
    return sum(universe[b]["rating"] for b in beaten if b in universe) / len(beaten)


def _score(info: dict[str, Any], rec: dict[str, Any], universe, *, cfp: bool) -> float:
    rating = info["rating"]
    w, l = rec["w"], rec["l"]
    if w + l == 0:  # preseason
        return rating * 10 + info.get("prestige", 5) * 4
    q = _quality(rec["beaten"], universe)
    if cfp:
        return w * 45 - l * 75 + q * 5 + rating * 6
    return rating * 8 + w * 40 - l * 70 + q * 4


def _ranked(universe, records, *, cfp: bool, prestige_bias: float = 0.0) -> list[str]:
    names = list(universe.keys())
    names.sort(
        key=lambda n: _score(universe[n], records[n], universe, cfp=cfp)
        + prestige_bias * universe[n].get("prestige", 5),
        reverse=True,
    )
    return names


def _poll_rows(order: list[str], universe, records, count: int, *, with_points: bool) -> list[dict[str, Any]]:
    rows = []
    for i, name in enumerate(order[:count]):
        info = universe[name]
        row = {
            "rank": i + 1, "team": name, "abbr": info.get("abbr"),
            "espn_id": info.get("espn_id"), "record": records[name]["overall"],
        }
        if with_points:
            row["points"] = max(40, 1550 - i * 56)
            row["first"] = FIRST_VOTES.get(i + 1)
        rows.append(row)
    return rows


def _receiving_rows(order: list[str], universe, start: int, end: int) -> list[dict[str, Any]]:
    rows = []
    for i, name in enumerate(order[start:end]):
        info = universe[name]
        rows.append({"team": name, "abbr": info.get("abbr"), "espn_id": info.get("espn_id"),
                     "votes": max(2, 110 - i * 12)})
    return rows


def compute(universe: dict[str, dict[str, Any]], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ap_order = _ranked(universe, records, cfp=False)
    coaches_order = _ranked(universe, records, cfp=False, prestige_bias=6.0)
    cfp_order = _ranked(universe, records, cfp=True)
    return {
        "ap_top25": _poll_rows(ap_order, universe, records, 25, with_points=True),
        "coaches_top25": _poll_rows(coaches_order, universe, records, 25, with_points=True),
        "cfp_top12": _poll_rows(cfp_order, universe, records, 12, with_points=False),
        "ap_receiving_votes": _receiving_rows(ap_order, universe, 25, 35),
        "coaches_receiving_votes": _receiving_rows(coaches_order, universe, 25, 35),
        "_ap_order": ap_order, "_coaches_order": coaches_order, "_cfp_order": cfp_order,
    }


def rank_of(order: list[str], name: str) -> int | None:
    try:
        return order.index(name) + 1
    except ValueError:
        return None
