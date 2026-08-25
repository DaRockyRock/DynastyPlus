"""Records and conference standings, derived from stored game results.

Pure functions over (universe, schedule, results, up_to_week): no state of their
own. compute_records returns each team's overall/conference W-L plus current
streak; conference_table sorts one conference by conference win pct then overall,
matching the row shape the standings UI already consumes from the static mock.
"""
from __future__ import annotations

from typing import Any


def _key(g: dict[str, Any]) -> str:
    return f"{g['week']}|{g['home']}|{g['away']}"


def compute_records(universe: dict[str, dict[str, Any]], schedule: list[dict[str, Any]],
                    results: dict[str, dict[str, Any]], up_to_week: int) -> dict[str, dict[str, Any]]:
    """name -> {w, l, cw, cl, overall, conf, streak, beaten:[names]}."""
    rec: dict[str, dict[str, Any]] = {
        name: {"w": 0, "l": 0, "cw": 0, "cl": 0, "_seq": [], "beaten": []}
        for name in universe
    }
    games = sorted((g for g in schedule if g["week"] < up_to_week and _key(g) in results),
                   key=lambda g: g["week"])
    for g in games:
        res = results[_key(g)]
        home, away = g["home"], g["away"]
        hs, as_ = res["home_score"], res["away_score"]
        winner, loser = (home, away) if hs > as_ else (away, home)
        for t, won in ((winner, True), (loser, False)):
            if t not in rec:
                continue
            r = rec[t]
            r["w" if won else "l"] += 1
            if g["conference"]:
                r["cw" if won else "cl"] += 1
            r["_seq"].append("W" if won else "L")
        rec[winner]["beaten"].append(loser)

    for name, r in rec.items():
        r["overall"] = f"{r['w']}-{r['l']}"
        r["conf"] = f"{r['cw']}-{r['cl']}"
        r["streak"] = _streak(r.pop("_seq"))
    return rec


def _streak(seq: list[str]) -> str:
    if not seq:
        return "-"
    last = seq[-1]
    n = 0
    for s in reversed(seq):
        if s == last:
            n += 1
        else:
            break
    return f"{last}{n}"


def _winpct(w: int, l: int) -> float:
    total = w + l
    return w / total if total else 0.0


def conference_table(records: dict[str, dict[str, Any]], universe: dict[str, dict[str, Any]],
                     conference: str) -> list[dict[str, Any]]:
    members = [n for n, v in universe.items() if v.get("conference") == conference]
    members.sort(key=lambda n: (_winpct(records[n]["cw"], records[n]["cl"]),
                                 _winpct(records[n]["w"], records[n]["l"])), reverse=True)
    rows = []
    for n in members:
        info = universe[n]
        rows.append({
            "team": n, "abbr": info.get("abbr"), "espn_id": info.get("espn_id"),
            "conf_record": records[n]["conf"], "overall": records[n]["overall"],
        })
    return rows
