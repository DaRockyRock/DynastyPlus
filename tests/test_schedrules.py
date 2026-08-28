"""Tests for the custom schedule generator (backend.schedrules).

Solver primitives are tested on synthetic inputs; the end-to-end path
(state -> rules -> validate -> generate -> apply) runs against a copy of a
real preseason save when one is present in the local CFB 27 saves folder,
and is skipped otherwise (same convention as the other live-save tests).
"""
from __future__ import annotations

import json
import os
import random
import shutil
import struct
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from backend import schedrules

_PRESEASON_ENV = os.environ.get("CFB27_PRESEASON_SAVE")
PRESEASON = Path(_PRESEASON_ENV) if _PRESEASON_ENV else None


# ---------------------------------------------------------------------------
# _pair_up: degree-sequence realization
# ---------------------------------------------------------------------------

def _check_edges(edges, degrees, forbidden=frozenset()):
    deg = Counter()
    seen = set()
    for a, b in edges:
        assert a != b
        fs = frozenset((a, b))
        assert fs not in seen, "duplicate pair"
        assert fs not in forbidden, "forbidden pair used"
        seen.add(fs)
        deg[a] += 1
        deg[b] += 1
    assert dict(deg) == {t: d for t, d in degrees.items() if d}


def test_pair_up_round_robin_is_exact():
    # 8 teams, 7 games each: the complete graph is the only realization
    rng = random.Random(1)
    degrees = {t: 7 for t in range(8)}
    edges = schedrules._pair_up(rng, degrees, lambda a, b: True, set(), "test")
    _check_edges(edges, degrees)
    assert len(edges) == 28


def test_pair_up_respects_forbidden_and_allowed():
    rng = random.Random(2)
    degrees = {t: 2 for t in range(6)}
    forbidden = {frozenset((0, 1))}
    # teams 0..2 may not play each other beyond what's needed: allowed blocks (1,2)
    edges = schedrules._pair_up(
        rng, degrees, lambda a, b: {a, b} != {1, 2}, forbidden, "test")
    _check_edges(edges, degrees, forbidden)
    assert frozenset((1, 2)) not in {frozenset(e) for e in edges}


def test_pair_up_reports_impossible():
    rng = random.Random(3)
    # 3 teams, 2 games each, but one pair forbidden AND one pair disallowed:
    # team 0 can only reach team 1, so degree 2 is unreachable
    with pytest.raises(schedrules._Infeasible):
        schedrules._pair_up(
            rng, {0: 2, 1: 2, 2: 2}, lambda a, b: {a, b} != {0, 2},
            {frozenset((0, 1))}, "test")


def test_pair_up_parity():
    rng = random.Random(4)
    with pytest.raises(schedrules._Infeasible):
        schedrules._pair_up(rng, {0: 1, 1: 1, 2: 1}, lambda a, b: True, set(), "test")


# ---------------------------------------------------------------------------
# _assign_weeks: exact-capacity week assignment
# ---------------------------------------------------------------------------

def _mini_model(n_teams=8, weeks=(0, 1, 2, 3), cap=4, user=None, user_weeks=None):
    return {
        "fcs": set(),
        "user_row": user,
        "user_weeks": list(user_weeks or []),
        "capacity": {w: cap for w in weeks},
        "pinned_games": [],
        "roster": [type("T", (), {"school": f"Team {i}"})() for i in range(n_teams)],
    }


def test_assign_weeks_exact_fill_and_uniqueness():
    rng = random.Random(5)
    # 8 teams, every pair impossible; use a 4-regular slate: 16 games over 4
    # weeks of 4 slots, every team playing every week
    degrees = {t: 4 for t in range(8)}
    edges = schedrules._pair_up(rng, degrees, lambda a, b: True, set(), "t")
    games = [{"a": a, "b": b, "week": None, "tag": "x"} for a, b in edges]
    model = _mini_model()
    schedrules._assign_weeks(rng, model, games)
    per_week = Counter(g["week"] for g in games)
    assert dict(per_week) == {0: 4, 1: 4, 2: 4, 3: 4}
    busy = set()
    for g in games:
        for t in (g["a"], g["b"]):
            assert (t, g["week"]) not in busy
            busy.add((t, g["week"]))


def test_assign_weeks_honors_fixed_and_user_weeks():
    rng = random.Random(6)
    # user (team 0) may only play weeks 0 and 2; they have 2 games
    games = [
        {"a": 0, "b": 1, "week": 1 - 1, "tag": "x"},   # fixed to week 0
        {"a": 0, "b": 2, "week": None, "tag": "x"},
        {"a": 1, "b": 2, "week": None, "tag": "x"},
        {"a": 3, "b": 4, "week": None, "tag": "x"},
        {"a": 3, "b": 5, "week": None, "tag": "x"},
        {"a": 4, "b": 5, "week": None, "tag": "x"},
    ]
    model = _mini_model(n_teams=6, weeks=(0, 1, 2), cap=2, user=0, user_weeks=[0, 2])
    schedrules._assign_weeks(rng, model, games)
    assert games[0]["week"] == 0
    assert games[1]["week"] == 2   # the only other week the user may play
    per_week = Counter(g["week"] for g in games)
    assert dict(per_week) == {0: 2, 1: 2, 2: 2}


def test_assign_weeks_impossible_reports():
    rng = random.Random(7)
    # 2 teams, 2 games against each other is a duplicate upstream; instead:
    # 3 games for team 0 into 2 weeks cannot fit
    games = [
        {"a": 0, "b": 1, "week": None, "tag": "x"},
        {"a": 0, "b": 2, "week": None, "tag": "x"},
        {"a": 0, "b": 3, "week": None, "tag": "x"},
        {"a": 1, "b": 2, "week": None, "tag": "x"},
    ]
    model = _mini_model(n_teams=4, weeks=(0, 1), cap=2)
    with pytest.raises(schedrules._Infeasible):
        schedrules._assign_weeks(rng, model, games)


# ---------------------------------------------------------------------------
# defaults
# ---------------------------------------------------------------------------

def test_default_conf_games_parity_nudge():
    # 17 teams: an odd count times 9 is odd, nudge to 8
    assert schedrules._default_conf_games(17, Counter({9: 12, 8: 5})) == 8
    # 16 teams: 9 is fine
    assert schedrules._default_conf_games(16, Counter({9: 16})) == 9
    # tiny conference clamps to n - 1
    assert schedrules._default_conf_games(8, Counter({8: 8})) == 7


# ---------------------------------------------------------------------------
# end to end against a real preseason save (skipped without one)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# _gate: phases, the preseason full-reset signal, and the locked-week note
# ---------------------------------------------------------------------------

def _slot(week=1, wins=0, losses=0, label="Week"):
    from backend.saveparse.profile import Slot
    return Slot(save_name="DYNASTY-TEST", dynasty_id="1", school="Nebraska",
                next_game="", coach_first="Test", coach_last="Coach",
                week_label=label, week=week, season=1, team_row=0,
                wins=wins, losses=losses)


def _skel(total=900, official=0, pinned=(), user_row=0):
    return {"slots": [None] * total, "official": official,
            "pinned_weeks": list(pinned), "user_row": user_row,
            "user_weeks": [], "by_week": {}}


def test_gate_fresh_empty_store_is_pregeneration():
    # dynasty creation / early preseason: no schedule in the save yet, and the
    # guidance must send the user to a PRESEASON save, not to Week 1
    gate = schedrules._gate({"slot": _slot(week=1)}, _skel(total=0))
    assert not gate["ok"] and gate["phase"] == "pregeneration"
    assert "preseason" in gate["reason"].lower()
    gate = schedrules._gate({"slot": _slot(week=0)}, _skel(total=0))
    assert gate["phase"] == "pregeneration"


def test_gate_rolled_over_empty_store_is_offseason():
    gate = schedrules._gate({"slot": _slot(week=1, wins=10, losses=3, label="Stage")},
                            _skel(total=0))
    assert not gate["ok"] and gate["phase"] == "offseason"
    # with no profile row the empty store still reads as the offseason
    gate = schedrules._gate({"slot": None}, _skel(total=0))
    assert gate["phase"] == "offseason"


def test_gate_partial_store_is_pregeneration():
    gate = schedrules._gate({"slot": _slot()}, _skel(total=43))
    assert not gate["ok"] and gate["phase"] == "pregeneration"


def test_gate_preseason_full_reset():
    gate = schedrules._gate({"slot": _slot()}, _skel())
    assert gate["ok"] and gate["full_reset"] is True
    assert "note" not in gate


def test_gate_week1_locked_notes_preseason_remedy():
    gate = schedrules._gate({"slot": _slot()}, _skel(pinned=[0]))
    assert gate["ok"] and gate["full_reset"] is False
    assert "Week 1" in gate["note"] and "preseason" in gate["note"]


def test_gate_played_season_stays_closed():
    gate = schedrules._gate({"slot": _slot(wins=2)}, _skel(official=20))
    assert not gate["ok"] and gate["phase"] == "regular"


@pytest.mark.slow
@pytest.mark.skipif(PRESEASON is None or not PRESEASON.exists(),
                    reason="set CFB27_PRESEASON_SAVE to run the live-save test")
def test_end_to_end_on_real_save(tmp_path, monkeypatch):
    from backend.saveparse import container, schedule as savesched, teams

    save = tmp_path / "TESTSAVE"
    shutil.copyfile(PRESEASON, save)
    monkeypatch.setattr(schedrules.config, "SAVE_PATH", str(save))
    schedrules.confsetup._table_cache.clear()
    schedrules.reset()   # a clean rules store whatever ran before

    payload0 = container.decode(save.read_bytes()).payload
    roster = teams.parse_teams(payload0)
    neb = next(i for i, t in enumerate(roster) if t.school == "Nebraska")
    monkeypatch.setattr(schedrules, "_user_row", lambda ctx: neb)

    state = schedrules.get_state()
    assert state["available"] and state["apply_gate"]["ok"]
    assert state["feasibility"]["ok"]
    # a true preseason save has no locked weeks: the whole season regenerates
    assert state["apply_gate"]["full_reset"] is True
    assert not any(w["locked"] for w in state["weeks"])

    # protect a non-conference rival for the user; expect rivalry week
    other = next(c for c in state["conferences"]
                 if c["name"] != state["user_team"]["conference"])
    rival = other["teams"][0]["name"]
    rules = {
        "conferences": {c["name"]: {"games": c["games"],
                                    "round_robin_divisions": False,
                                    "rivalries": c["rivalries"]}
                        for c in state["conferences"]},
        "nonconference": [{"a": state["user_team"]["name"], "b": rival,
                           "rank": 1, "week": None, "location": "rotate"}],
    }
    state = schedrules.set_rules(rules)
    assert state["feasibility"]["ok"], state["feasibility"]["errors"]

    res = schedrules.generate()
    assert res["ok"], res.get("errors")
    # Week 1 is part of the plan (nothing pinned on a preseason save)
    week1 = next(w for w in res["plan"]["weeks"] if w["week"] == 1)
    assert week1["games"] and not week1["locked"]
    week14 = next(w for w in res["plan"]["weeks"] if w["week"] == 14)
    pair = {state["user_team"]["row"],
            next(t["row"] for t in other["teams"] if t["name"] == rival)}
    assert any({g["home"]["row"], g["away"]["row"]} == pair for g in week14["games"])

    out = schedrules.apply_plan()
    assert out["ok"] and out["changed"] > 0

    # the user's records did not move, and only team-ref bytes changed
    payload1 = container.decode(save.read_bytes()).payload
    s0, s1 = savesched.parse(payload0), savesched.parse(payload1)
    u0 = {g.index for g in s0.games if g.scheduled and g.bowl_row is None
          and neb in (g.away_row, g.home_row)}
    u1 = {g.index for g in s1.games if g.scheduled and g.bowl_row is None
          and neb in (g.away_row, g.home_row)}
    assert u0 == u1
    changed_offsets = set()
    for g0 in s0.games:
        r0 = payload0[g0.offset:g0.offset + 100]
        r1 = payload1[g0.offset:g0.offset + 100]
        changed_offsets |= {i for i in range(100) if r0[i] != r1[i]}
    assert changed_offsets <= {8, 9, 10, 11, 36, 37, 38, 39}
