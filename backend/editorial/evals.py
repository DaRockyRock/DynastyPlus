"""Golden-week evals: assert the editorial brain makes the obviously-right calls.

A small, model-free harness (it exercises steps 1-7: state, ratings, candidates,
scorer, arcs, rundown) over synthetic saves built from the current dynasty, so
scorer weights and selection can be tuned with confidence and regressions are
caught. Run: `python -m backend.editorial.evals`. Each check is deterministic and
runs against an ISOLATED store so it never touches a real dynasty.
"""
from __future__ import annotations

import copy
import tempfile
from pathlib import Path
from typing import Callable

from .. import dynasty_paths, pipeline
from . import arcs, briefs, claims


def _isolate():
    tmp = Path(tempfile.mkdtemp())
    dynasty_paths.sub = lambda name: (tmp / name).mkdir(parents=True, exist_ok=True) or (tmp / name)


def _base() -> dict:
    return pipeline.load_dynasty(2026, 1)


def _check_determinism() -> tuple[bool, str]:
    _isolate()
    d = _base()
    r1, r2 = briefs.build_rundown(d, 2026, 1), briefs.build_rundown(d, 2026, 1)
    ids1 = [c["id"] for c in r1["national"] + r1["program"]]
    ids2 = [c["id"] for c in r2["national"] + r2["program"]]
    return ids1 == ids2, f"slate ids stable across rebuilds ({len(ids1)} stories)"


def _check_upset_leads() -> tuple[bool, str]:
    _isolate()
    d = _base()
    d["season"]["week"] = 2
    # Construct the upset deterministically (saves differ): an unranked nobody beats
    # the AP No. 1 as a 34.5-point underdog. Must outrank everything else that week.
    ap1 = d["national"]["ap_top25"][0]
    g = d["national"]["scoreboard"][0]
    g["home"] = {"name": "Overmatched State Spartans", "abbr": "OMS", "rank": None, "record": "0-0"}
    g["away"] = {"name": ap1["team"], "abbr": ap1.get("abbr"), "rank": 1, "record": "0-0"}
    g.update(line=f"{ap1.get('abbr')} -34.5", neutral=False, user=False,
             status="final", home_score=31, away_score=28, week=2)
    r = briefs.build_rundown(d, 2026, 2)
    top = (r["national"] or [{}])[0]
    return top.get("type") == "upset", f"top national story is '{top.get('type')}' (want upset)"


def _check_bye_evergreens() -> tuple[bool, str]:
    _isolate()
    d = _base()
    d["season"]["week"] = 7
    d["recruiting"]["targets"] = []
    d["team"]["record"]["overall"] = "4-2"
    d["schedule"]["recent_results"] = [{"week": 6, "opponent": "Iowa", "result": "W 21-17",
                                        "score": "21-17", "home": True}]
    d["schedule"]["upcoming"] = {}
    r = briefs.build_rundown(d, 2026, 7)
    types = {c["type"] for c in r["program"]}
    ever = {"player_spotlight", "position_feature", "season_retrospective"}
    return bool(types & ever), f"bye-week program types {sorted(types)} include an evergreen"


def _check_season_open_no_rumors() -> tuple[bool, str]:
    _isolate()
    d = _base()
    cl = claims.for_week(d, 2026, 1, season_open=True)
    ok = not cl["live"] and not cl["resolutions"]
    return ok, "no carousel rumors exist in the preseason"


def _check_arc_continuity() -> tuple[bool, str]:
    _isolate()
    d = _base()
    briefs.build_rundown(d, 2026, 1)                 # opens recruiting arcs
    d2 = copy.deepcopy(d); d2["season"]["week"] = 2
    r2 = briefs.build_rundown(d2, 2026, 2)           # advances them
    notes = [c.get("arc_note") for c in r2["program"] if c.get("arc_note")]
    return bool(notes), f"week-2 program stories carry an arc continuity note ({len(notes)} found)"


CHECKS: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
    ("determinism", _check_determinism),
    ("upset_leads", _check_upset_leads),
    ("bye_evergreens", _check_bye_evergreens),
    ("season_open_no_rumors", _check_season_open_no_rumors),
    ("arc_continuity", _check_arc_continuity),
]


def run() -> bool:
    passed = 0
    for name, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as exc:
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        passed += bool(ok)
    print(f"\n{passed}/{len(CHECKS)} golden checks passed")
    return passed == len(CHECKS)


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
