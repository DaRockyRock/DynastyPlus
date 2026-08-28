"""End-to-end custom-playoff loop tests: drive playoff_live.sync through a
whole bracket against the faithful CFB27 engine emulator, for every bracket
size and every place the user can finish (win it all, lose in any round, or
never make the field). These are the scenarios the live automation kept
breaking on; they run only when a base-save fixture is present
(CFBMOD_TEST_BASE_SAVE), and are marked slow (each wave re-encodes a ~30MB
save).

What each run proves:
  * the bracket always reaches a single champion (no stall, no hang);
  * the user plays exactly as many games as their finish implies, and is the
    champion iff they win them all;
  * once eliminated the user's own record is never overwritten by a CPU game
    and their real last result is pinned (state.user_frozen);
  * every simmed score is distinct wave-to-wave (real per-load simulation, not
    a frozen replay).
"""
import copy
import math
import shutil

import pytest

import cfb27_playoff_engine as eng

BASE = eng.base_save_path()
pytestmark = [
    pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture"),
    pytest.mark.slow,
]

# Hybrid field sizes (bigger than 16, so past both stock and native modes).
# Early rounds cycle at bowl week 1, then the final 16 advance normally.
POW2 = [32, 64, 128]
USER_RANK = 13

# native-mode field sizes (16 or fewer: the balla14-style forward calendar).
# The user is seeded inside the field (rank 3) so every round has a user game
# to play until they are eliminated or win it all.
NATIVE_SIZES = [2, 4, 8, 16]
NATIVE_USER_RANK = 1  # seeded into every field size, including a 2-team final


def _elims(size):
    rounds = int(math.log2(size))
    return sorted({1, (rounds + 1) // 2, rounds})  # early, middle, final-round loss


@pytest.mark.parametrize("size", POW2)
def test_user_wins_it_all(size, monkeypatch):
    h = eng.Harness(BASE, "Oregon Ducks", USER_RANK, eng._fmt(size), monkeypatch)
    r = eng.run_hybrid(h, size, elim_round=0)
    assert r["ok"], r.get("reason")
    assert r["champion"] == "Oregon Ducks"
    assert r["user_played"] == int(math.log2(size))
    scores = h.all_final_scores()
    assert len(set(scores)) == len(scores), "scores repeated across waves"


def test_124_team_cycle_finishes_each_round_before_advancing(monkeypatch):
    """The SMU shape completes every round and keeps neutral field treatment."""
    size = 124
    fmt = eng._fmt(size, byes=[{"teams": 4, "rounds": 1}])
    neutral = {
        "mode": "neutral", "bowls": [], "venue": "Custom Neutral",
        "city": "", "stadium": 0, "games": [],
    }
    fmt["sites"]["rounds"] = [dict(neutral) for _ in range(6)]
    h = eng.Harness(BASE, "Oregon Ducks", 40, fmt, monkeypatch)
    result = eng.run_hybrid(h, size, elim_round=0)
    assert result["ok"], result.get("reason")
    assert result["champion"] == "Oregon Ducks"
    assert result["user_played"] == 7


def test_96_team_field_with_32_byes_completes_after_user_loss(monkeypatch):
    """The Tennessee shape survives elimination and the empty title slate."""
    fmt = eng._fmt(96, byes=[{"teams": 32, "rounds": 1}])
    h = eng.Harness(BASE, "Oregon Ducks", 43, fmt, monkeypatch)
    result = eng.run_hybrid(h, 96, elim_round=2)
    assert result["ok"], result.get("reason")
    assert result["champion"] and result["champion"] != "Oregon Ducks"
    assert result["user_played"] == 2
    assert result["state"].get("status") == "complete"
    assert not h.slate(), "the completion only passed with a stale title queue"


@pytest.mark.parametrize("size", POW2)
def test_user_eliminated_each_round(size, monkeypatch):
    for elim in _elims(size):
        h = eng.Harness(BASE, "Oregon Ducks", USER_RANK, eng._fmt(size), monkeypatch)
        r = eng.run_hybrid(h, size, elim_round=elim)
        assert r["ok"], f"size {size} elim {elim}: {r.get('reason')}"
        assert r["champion"], "no champion crowned"
        assert r["champion"] != "Oregon Ducks", "eliminated user won"
        assert r["user_played"] == elim, f"played {r['user_played']} != {elim}"
        assert (r["state"].get("user_frozen") or {}).get("record"), \
            "user's last game not pinned after elimination"


# --- native mode (<=16 teams, forward calendar) ----------------------------

@pytest.mark.parametrize("size", NATIVE_SIZES)
def test_native_user_wins_it_all(size, monkeypatch):
    h = eng.Harness(BASE, "Oregon Ducks", NATIVE_USER_RANK, eng._fmt(size),
                    monkeypatch)
    r = eng.run_native(h, size, elim_round=0)
    assert r["ok"], r.get("reason")
    assert r["champion"] == "Oregon Ducks"
    assert r["user_played"] == int(math.log2(size))
    assert r["state"].get("mode") == "native"


@pytest.mark.parametrize("size", NATIVE_SIZES)
def test_native_user_eliminated_each_round(size, monkeypatch):
    for elim in _elims(size):
        h = eng.Harness(BASE, "Oregon Ducks", NATIVE_USER_RANK, eng._fmt(size),
                        monkeypatch)
        r = eng.run_native(h, size, elim_round=elim)
        assert r["ok"], f"size {size} elim {elim}: {r.get('reason')}"
        assert r["champion"], "no champion crowned"
        assert r["champion"] != "Oregon Ducks", "eliminated user won"
        assert r["user_played"] == elim, f"played {r['user_played']} != {elim}"


def test_native_spectator_completes(monkeypatch):
    # the user's own team is NOT in the field (they missed the playoff): the
    # exact scenario the request is about, watching the bracket play through
    # without taking over another team. An 8-team field with the user ranked
    # 40th so they are nowhere near it.
    h = eng.Harness(BASE, "Oregon Ducks", 40, eng._fmt(8), monkeypatch)
    r = eng.run_native(h, 8, elim_round=0)
    assert r["ok"], r.get("reason")
    assert r["champion"], "no champion crowned"
    assert r["user_played"] == 0, "spectator should play no playoff games"


def _cfp_user():
    """A team the fixture save has in a CFP FIRST-ROUND record (so it anchors
    at bowl week 1 on the CFP path, not a bowl). None if the save has none."""
    from backend import playoff_live
    from backend.saveparse import container, schedule, teams
    payload = container.decode(BASE.read_bytes()).payload
    store = schedule.parse(payload)
    roster = teams.parse_teams(payload)
    for r in playoff_live._postseason_slots(payload).get("first_round") or []:
        g = store.games[r]
        for row in (g.away_row, g.home_row):
            if row is not None and roster[row].name \
                    and not roster[row].name.upper().startswith("FCS"):
                return roster[row].name
    return None


def _future_bowl_user():
    """A non-FCS team with an engine postseason game outside this week's
    slate, the exact native-wiring shape of USC's later Ole Miss bowl."""
    from backend.saveparse import container, schedule, teams
    payload = container.decode(BASE.read_bytes()).payload
    store = schedule.parse(payload)
    roster = teams.parse_teams(payload)
    slate = set(schedule.week_slate(payload))
    current_rows = {
        row for record in slate if record < len(store.games)
        for row in (store.games[record].away_row, store.games[record].home_row)
        if row is not None
    }
    for game in store.games:
        if game.index in slate or game.bowl_row is None or game.official \
                or not game.scheduled:
            continue
        for row in (game.away_row, game.home_row):
            if row is not None and row not in current_rows and roster[row].name \
                    and not roster[row].name.upper().startswith("FCS"):
                return roster[row].name
    return None


def test_prepare_flips_every_regular_season_loss(monkeypatch):
    """The selection-boundary prepare presents an undefeated user to CFB."""
    from backend import playoff_live
    from backend.saveparse import container, schedule, teams

    user = _future_bowl_user()
    assert user, "fixture has no ordinary-bowl team"
    h = eng.Harness(BASE, user, 21, eng._fmt(32), monkeypatch)
    before_payload = container.decode(h.save.read_bytes()).payload
    before_store = schedule.parse(before_payload)
    losses = [game.index for game in before_store.by_team(h.user_row)
              if game.loser_row == h.user_row and game.bowl_row is None]
    if not losses:
        pytest.skip("fixture user has no regular-season losses")

    written = playoff_live._apply_prepare(
        h.user_row, teams.parse_teams(before_payload))

    assert written.get("written") is True
    assert {flip["game"] for flip in written["flips"]} == set(losses)
    after_payload = container.decode(h.save.read_bytes()).payload
    after_store = schedule.parse(after_payload)
    assert all(after_store.games[record].winner_row == h.user_row
               for record in losses)


def test_later_bowl_user_stays_on_safe_cycle_without_native_path(monkeypatch):
    """An ordinary-bowl user never enters an unsafe native handoff.

    The game may originally place the program in a later bowl, but Dynasty+
    schedules its custom games in the Bowl Week 1 cycle. A native CFP record can
    expose Play Game for this team while silently discarding the postgame result,
    because CFB never created the team's internal CFP route. The safe fallback
    therefore keeps the user on the cycle through the title.
    """
    from backend import playoff_live
    from backend.saveparse import bowls, container, schedule
    import struct

    user = _future_bowl_user()
    assert user, "fixture has no future engine bowl team"
    h = eng.Harness(BASE, user, 21, eng._fmt(32), monkeypatch)

    out = playoff_live.sync(write=True)
    state = h.state()
    game, record = h.user_unfinished(
        out.get("bracket") or {}, state.get("plan") or {})
    assert state.get("user_engine_week") == "later"
    assert state.get("user_cfp_path") is False
    assert not state.get("fallback_cycle")
    assert game is not None and record in h.slate(), \
        "ordinary-bowl user was not staged in Bowl Week 1"

    payload = container.decode(h.save.read_bytes()).payload
    req0, stride, count, _ = bowls._find_store(payload, b"SeasonGameRequest")
    request_rows = []
    for row in range(count):
        base = req0 + row * stride
        words = struct.unpack_from(f">{stride // 4}I", payload, base)
        if any((word >> 16) == schedule.GAME_REF
               and (word & 0xFFFF) == record for word in words):
            request_rows.append(base)
    assert any(
        struct.unpack_from(">I", payload, base + 16)[0] >> 16
        == schedule.USER_REF
        for base in request_rows
    ), "Bowl Week 1 user game lacks the user request mark"

    result = eng.run(h, 32, elim_round=0)
    assert result["ok"], result.get("reason")
    assert result["champion"] == user
    assert not result["state"].get("handoff")


def test_format9_migrates_existing_ordinary_bowl_fallback(monkeypatch):
    """An in-progress format 8 run recovers without restarting the dynasty."""
    import json

    from backend import playoff_live

    user = _future_bowl_user()
    assert user, "fixture has no future engine bowl team"
    fmt = eng._fmt(96, [{"teams": 32, "rounds": 1}])
    h = eng.Harness(BASE, user, 21, fmt, monkeypatch)

    # Finish the prioritized feeder so the bye user's first matchup is known.
    playoff_live.sync(write=True)
    h.engine.load()
    out = playoff_live.sync(write=False)
    state = h.state()
    game, record = h.user_unfinished(
        out.get("bracket") or {}, state.get("plan") or {})
    assert game is not None and record is not None

    # Recreate the legacy compatibility state that left USC waiting for its
    # later ordinary bowl and disabled the native final-16 tail.
    for rnd in state["bracket"]["rounds"]:
        recs = state["plan"].get(str(rnd["round"])) or []
        for gi, candidate in enumerate(rnd["games"]):
            if candidate["id"] == game["id"]:
                recs[gi] = None
                candidate.pop("record_index", None)
                candidate.pop("_disk", None)
    state.update({
        "fallback_cycle": True,
        "route_forward_clean": True,
        "user_engine_week": "later",
        "user_cfp_path": False,
        "wave_format": 8,
    })
    (h.tmp / "live.json").write_text(json.dumps(state), encoding="utf-8")

    migrated = playoff_live.sync(write=True)
    state = h.state()
    game, record = h.user_unfinished(
        migrated.get("bracket") or {}, state.get("plan") or {})
    assert not state.get("fallback_cycle")
    assert not state.get("route_forward_clean")
    assert state.get("wave_format") == playoff_live._WAVE_FORMAT
    assert game is not None and record in h.slate()
    assert playoff_live.native_tail_rounds(migrated["bracket"])
    assert any("upgraded to the native final-16 handoff" in note
               for note in migrated.get("notes") or [])


def test_reactive_tail_pin_reserves_user_live_record():
    # THE TAIL FIX (reactive pin): when the engine has advanced a CFP-path user
    # into a quarterfinal record, the user's tail-round game must map onto THAT
    # record (not a positional slot), and no sibling game may take it. This is
    # what stops "Indiana's QF -> BYU vs Oklahoma". Verified directly on the
    # reactive-pin helper with the user planted in one QF record of the fixture.
    from backend import playoff_live
    from backend.saveparse import container, schedule, teams
    import struct
    if BASE is None:
        pytest.skip("no fixture save")
    payload = bytearray(container.decode(BASE.read_bytes()).payload)
    store0 = schedule.parse(bytes(payload))
    roster = teams.parse_teams(bytes(payload))
    qf_recs = playoff_live._postseason_slots(bytes(payload)).get("quarterfinal") or []
    if len(qf_recs) < 2:
        pytest.skip("fixture has no quarterfinal records")
    user_row = next(i for i, t in enumerate(roster) if t.name and not t.name.upper().startswith("FCS"))
    user = roster[user_row].name
    live = qf_recs[0]
    # plant the user into one QF record, result-less (engine's live placement)
    off = store0.records_off + live * schedule.RECORD_SIZE
    struct.pack_into(">I", payload, off + 36, (schedule.TEAM_REF << 16) | user_row)
    payload[off + 97] &= ~0x11 & 0xFF
    store = schedule.parse(bytes(payload))
    rows_by_name = {t.name: i for i, t in enumerate(roster)}
    opp = roster[next(i for i, t in enumerate(roster) if i != user_row and t.name)].name
    # rounds 3/4/5 so the walk-back kinds are QF / SF / championship; the user
    # is live in round 3 (the QF) with a sibling CPU game.
    bracket = {"rounds": [
        {"round": 3, "games": [
            {"id": "u", "status": "live", "slots": [{"type": "team", "team": user}, {"type": "team", "team": opp}]},
            {"id": "c", "status": "live", "slots": [{"type": "team", "team": roster[10].name}, {"type": "team", "team": roster[11].name}]}]},
        {"round": 4, "games": [{"id": "s", "status": "pending",
                                "slots": [{"type": "winner", "game": "u"}, {"type": "winner", "game": "c"}]}]},
        {"round": 5, "games": [{"id": "f", "status": "pending",
                                "slots": [{"type": "winner", "game": "s"}, {"type": "seed", "seed": 1}]}]},
    ]}
    sub = {"rounds": [bracket["rounds"][0]]}  # only the QF round is being written
    slots_map = playoff_live._postseason_slots(bytes(payload))
    plan = {}
    playoff_live._pin_user_tail(sub, plan, slots_map, store, rows_by_name, {user}, bracket)
    assert plan.get("3", [None])[0] == live, "user's tail game not pinned to their live QF record"
    playoff_live._assign_records(sub, plan, slots_map, store, rows_by_name)
    assert plan["3"][0] == live, "reactive pin was overwritten"
    assert plan["3"][1] != live, "sibling game stole the user's reserved record"


def test_native_pin_follows_actions_request_and_swaps_sibling_record():
    """Actions wiring wins when prior writes moved the user's team elsewhere."""
    from backend import playoff_live
    from backend.saveparse import container, schedule, teams

    payload = bytearray(container.decode(BASE.read_bytes()).payload)
    roster = teams.parse_teams(bytes(payload))
    store = schedule.parse(bytes(payload))
    slate = [record for record in schedule.week_slate(bytes(payload))
             if record < len(store.games) and not store.games[record].official]
    assert len(slate) >= 2
    wrong, actions = slate[:2]
    schedule.set_user_pending(payload, actions)
    assert schedule.user_pending_game(bytes(payload)) == actions

    user_row = next(i for i, team in enumerate(roster)
                    if team.name == "Oregon Ducks")
    names = [team.name for team in roster if team.name
             and team.name != "Oregon Ducks"]
    bracket = {"rounds": [{
        "round": 1,
        "games": [
            {"id": "user", "status": "scheduled", "slots": [
                {"type": "team", "team": "Oregon Ducks"},
                {"type": "team", "team": names[0]},
            ]},
            {"id": "cpu", "status": "scheduled", "slots": [
                {"type": "team", "team": names[1]},
                {"type": "team", "team": names[2]},
            ]},
        ],
    }]}
    plan = {"1": [wrong, actions]}
    slots = {"championship": [wrong, actions]}

    changed = playoff_live._native_pin_user(
        bracket, plan, slots, schedule.parse(bytes(payload)), bytes(payload),
        {"Oregon Ducks"}, {user_row})

    assert changed
    assert plan["1"] == [actions, wrong]


def test_duplicate_user_request_rows_are_collapsed_without_touching_game():
    """Two Actions rows for one native matchup safely become one."""
    import struct

    from backend.saveparse import bowls, container, schedule

    payload = bytearray(container.decode(BASE.read_bytes()).payload)
    record = schedule.week_slate(bytes(payload))[0]
    store0 = schedule.parse(bytes(payload))
    game0 = store0.games[record]
    user_rows = {game0.home_row}
    schedule.set_user_pending(payload, record, user_team_rows=user_rows)
    req0, stride, count, _ = bowls._find_store(
        bytes(payload), b"SeasonGameRequest")
    rows = []
    for row in range(count):
        base = req0 + row * stride
        words = struct.unpack_from(f">{stride // 4}I", payload, base)
        if any((word >> 16) == schedule.GAME_REF
               and (word & 0xFFFF) == record for word in words):
            rows.append(base)
    assert len(rows) == 2
    away_request, home_request = schedule.request_id_pair(bytes(payload), game0)
    assert away_request != home_request
    assert struct.unpack_from(">I", payload, rows[0] + 16)[0] == \
        schedule.USER_REF << 16
    assert struct.unpack_from(">I", payload, rows[0] + 40)[0] == home_request

    # Reproduce the live SMU shape: both participant rows are user variants
    # with allocated request IDs, while the SeasonGame itself is healthy.
    for base, request_id in zip(rows, (away_request, home_request)):
        struct.pack_into(">I", payload, base + 16, schedule.USER_REF << 16)
        struct.pack_into(">I", payload, base + 28, 0)
        struct.pack_into(">I", payload, base + 40, request_id)
        struct.pack_into(">I", payload, base + 48, schedule.NO_RESULT)
        struct.pack_into(">I", payload, base + 56, 0x01000000)
    store = schedule.parse(bytes(payload))
    game_before = schedule.read_record(bytes(payload), store, record)

    report = schedule.repair_duplicate_user_pending(
        payload, record, user_team_rows=user_rows)

    assert report
    assert schedule.user_pending_count(bytes(payload), record) == 1
    assert schedule.read_record(bytes(payload), store, record) == game_before
    keep = next(base for base in rows
                if struct.unpack_from(">I", payload, base + 40)[0] == home_request)
    other = next(base for base in rows if base != keep)
    assert struct.unpack_from(">I", payload, other + 16)[0] == 0
    assert struct.unpack_from(">I", payload, other + 40)[0] == schedule.NO_RESULT
    assert struct.unpack_from(">I", payload, other + 48)[0] == \
        struct.unpack_from(">I", payload, other + 44)[0]
    assert struct.unpack_from(">I", payload, keep + 16)[0] == \
        schedule.USER_REF << 16


def test_native_sync_repairs_duplicate_actions_row(monkeypatch):
    """A loaded native round prompts one update and removes the duplicate."""
    import struct

    from backend import playoff_live
    from backend.saveparse import bowls, container, schedule

    user = _cfp_user()
    if user is None:
        pytest.skip("fixture save has no CFP first-round team")
    h = eng.Harness(BASE, user, 3, eng._fmt(16), monkeypatch)
    written = playoff_live.sync(write=True)
    state = h.state()
    _game, record = h.user_unfinished(written["bracket"], state["plan"])
    assert record is not None

    raw = h.save.read_bytes()
    payload = bytearray(container.decode(raw).payload)
    req0, stride, count, _ = bowls._find_store(
        bytes(payload), b"SeasonGameRequest")
    rows = []
    for row in range(count):
        base = req0 + row * stride
        words = struct.unpack_from(f">{stride // 4}I", payload, base)
        if any((word >> 16) == schedule.GAME_REF
               and (word & 0xFFFF) == record for word in words):
            rows.append(base)
    assert len(rows) == 2
    for index, base in enumerate(rows):
        struct.pack_into(">I", payload, base + 16, schedule.USER_REF << 16)
        struct.pack_into(">I", payload, base + 28, 0)
        struct.pack_into(">I", payload, base + 40, 0x80001000 + index)
        struct.pack_into(">I", payload, base + 48, schedule.NO_RESULT)
        struct.pack_into(">I", payload, base + 56, 0x01000000)
    h.save.write_bytes(container.encode(raw, bytes(payload)))

    polled = playoff_live.sync(write=False)
    assert polled.get("needs_write") is True
    repaired = playoff_live.sync(write=True)
    assert repaired.get("save_written") is True
    repaired_payload = container.decode(h.save.read_bytes()).payload
    assert schedule.user_pending_count(repaired_payload, record) == 1


def test_native_next_round_is_prestaged_before_boundary():
    from backend import playoff_live

    bracket = {"rounds": [
        {"round": 1, "games": [
            {"status": "final", "slots": [
                {"type": "team", "team": "A"},
                {"type": "team", "team": "B"}]}]},
        {"round": 2, "games": [
            {"status": "scheduled", "slots": [
                {"type": "team", "team": "A"},
                {"type": "team", "team": "C"}]}]},
        {"round": 3, "games": [
            {"status": "scheduled", "slots": [
                {"type": "winner", "game": "qf"},
                {"type": "team", "team": "D"}]}]},
    ]}
    slots = {
        "first_round": [10], "quarterfinal": [20],
        "semifinal": [30], "championship": [40],
    }
    # Three custom rounds map to QF, SF, NCG. With the QF current, the fully
    # decided semifinal must be written before advancing into its week.
    assert playoff_live._native_prestage_rounds(
        bracket, slots, {20}) == {"2"}


def test_partial_native_request_ids_are_detected_but_never_transplanted():
    import struct
    from backend.saveparse import container, schedule

    payload = bytearray(container.decode(BASE.read_bytes()).payload)
    store = schedule.parse(bytes(payload))
    qf = [game.index for game in store.games
          if game.bowl_row is not None][:4]
    assert len(qf) == 4

    # Give every target a complete matchup but only one request identity.
    # The schema confirms these numbers are backed by engine request objects,
    # so no repair function is allowed to copy IDs from another game.
    team_rows = [row for row in range(12)]
    for number, index in enumerate(qf):
        game = store.games[index]
        schedule.set_matchup(payload, game,
                             away_row=team_rows[number * 2],
                             home_row=team_rows[number * 2 + 1])
        struct.pack_into(">I", payload, game.offset + 52,
                         0x80002000 + number)
        struct.pack_into(">I", payload, game.offset + 60,
                         schedule.NO_RESULT)
        payload[game.offset + 97] &= ~0x11 & 0xFF

    broken = schedule.parse(bytes(payload))
    assert all(schedule.request_id_pair_partial(
        bytes(payload), broken.games[index]) for index in qf)
    assert not hasattr(schedule, "repair_partial_result_pairs")


def test_partial_native_requests_restore_prior_boundary(monkeypatch):
    """Recovery rewinds one week and lets CFB issue both requests itself."""
    import struct

    from backend import playoff_live
    from backend.saveparse import container, schedule

    user = _cfp_user()
    if user is None:
        pytest.skip("fixture save has no CFP first-round team")
    h = eng.Harness(BASE, user, 1, eng._fmt(16), monkeypatch)

    playoff_live.sync(write=True)
    h.engine.load(user_row=h.user_row, user_result="win", official=True)
    staged = playoff_live.sync(write=True)
    assert staged.get("save_written")
    boundary = h.tmp / "native_boundary_base.sav"
    assert boundary.exists()

    h.engine.advance_week()
    raw = h.save.read_bytes()
    payload = bytearray(container.decode(raw).payload)
    store = schedule.parse(bytes(payload))
    qf = playoff_live._postseason_slots(bytes(payload))["quarterfinal"]
    for record in qf:
        game = store.games[record]
        assert game.scheduled
        struct.pack_into(">I", payload, game.offset + 60,
                         schedule.NO_RESULT)
    h.save.write_bytes(container.encode(raw, bytes(payload)))

    recovered = playoff_live.sync(write=True)
    assert recovered.get("save_written")
    assert h.state().get("boundary_recovery")
    recovered_payload = container.decode(h.save.read_bytes()).payload
    recovered_store = schedule.parse(recovered_payload)
    assert not set(qf) & set(schedule.week_slate(recovered_payload))
    assert all(recovered_store.games[record].scheduled for record in qf)
    assert all(schedule.request_id_pair(recovered_payload,
                                        recovered_store.games[record]) ==
               (schedule.NO_RESULT, schedule.NO_RESULT)
               for record in qf)

    # Crossing the restored boundary creates real two-sided requests and
    # clears recovery mode on the next sync.
    h.engine.week = 1
    h.engine.advance_week()
    arrived_payload = container.decode(h.save.read_bytes()).payload
    arrived_store = schedule.parse(arrived_payload)
    assert all(schedule.request_id_pair_complete(
        arrived_payload, arrived_store.games[record]) for record in qf)
    verified = playoff_live.sync(write=False)
    assert not h.state().get("boundary_recovery")
    assert not verified.get("awaiting_reload")


@pytest.mark.parametrize("elim", [0, 2])
def test_cfp_user_hybrid_completes(elim, monkeypatch):
    # A CFP-path team cycles only the oversized opening phase, then follows
    # the same final-16 handoff as a bowl-path user. It must complete, avoid
    # the retired calendar-tail flag, and crown the right champion.
    user = _cfp_user()
    if user is None:
        pytest.skip("fixture save has no CFP first-round team")
    h = eng.Harness(BASE, user, 9, eng._fmt(32), monkeypatch)
    r = eng.run_hybrid(h, 32, elim_round=elim)
    assert r["ok"], r.get("reason")
    assert r["state"].get("user_cfp_path") is True, "expected a CFP-path anchor"
    assert not r["state"].get("tail"), "tail must stay disabled"
    if elim == 0:
        assert r["champion"] == user
    else:
        assert r["champion"] and r["champion"] != user
        assert r["user_played"] == elim


@pytest.mark.parametrize("size,byes", [(24, [{"teams": 8, "rounds": 1}]),
                                       (80, [{"teams": 48, "rounds": 1}]),
                                       # the reported 2026-07-10 format: tiered
                                       # byes, user a double-bye seed (rank 13)
                                       (128, [{"teams": 24, "rounds": 1},
                                              {"teams": 16, "rounds": 2},
                                              {"teams": 8, "rounds": 3}])])
def test_non_power_of_two_completes(size, byes, monkeypatch):
    for elim in (1, 0):
        h = eng.Harness(BASE, "Oregon Ducks", USER_RANK, eng._fmt(size, byes), monkeypatch)
        r = eng.run_hybrid(h, size, elim_round=elim)
        assert r["ok"], f"size {size} elim {elim}: {r.get('reason')}"
        assert r["champion"], "no champion"
        if elim == 0:
            assert r["champion"] == "Oregon Ducks"


def test_96_team_bye_users_feeder_runs_in_first_wave(monkeypatch):
    """Regression for USC seed 21 waiting on an unplayed R1G16.

    The 32 first-round games exceed the fixture save's 28 host records. The
    direct feeder into the bye user's current game must still be staged in
    wave one and produce a result before distant title-path branches.
    """
    from backend import playoff_live
    from backend.saveparse import container, schedule as savesched

    byes = [{"teams": 32, "rounds": 1}]
    h = eng.Harness(BASE, "Oregon Ducks", 21, eng._fmt(96, byes), monkeypatch)
    out = playoff_live.sync(write=True)
    bracket = out["bracket"]
    state = h.state()
    user_game = next(
        game
        for rnd in bracket["rounds"]
        for game in rnd["games"]
        if any(slot.get("team") == "Oregon Ducks" for slot in game["slots"])
    )
    feeder = next(slot["game"] for slot in user_game["slots"]
                  if slot.get("game"))
    feeder_round = next(rnd for rnd in bracket["rounds"]
                        if any(game["id"] == feeder for game in rnd["games"]))
    feeder_index = next(i for i, game in enumerate(feeder_round["games"])
                        if game["id"] == feeder)
    feeder_record = state["plan"][str(feeder_round["round"])][feeder_index]
    assert feeder_record in h.slate(), "direct feeder was not staged in wave one"

    h.engine.load()
    captured = playoff_live.sync(write=False)["bracket"]
    feeder_game = next(game for rnd in captured["rounds"]
                       for game in rnd["games"] if game["id"] == feeder)
    assert feeder_game["status"] == "final"
    assert feeder_game.get("winner")

    # The next write stages the user's newly decided matchup. Their original
    # engine bowl must no longer contain the user, or CFB 27 keeps that stale
    # bowl as the program's postseason destination and the custom request row
    # appears as a bye on the dynasty hub (USC still showing Ole Miss).
    playoff_live.sync(write=True)
    payload = container.decode(h.save.read_bytes()).payload
    store = savesched.parse(payload)
    user_postseason = [
        game for game in store.games
        if game.bowl_row is not None and not game.official
        and h.user_row in (game.away_row, game.home_row)
    ]
    assert len(user_postseason) == 1, [game.index for game in user_postseason]
    custom = user_postseason[0]
    staged_state = h.state()
    user_record = next(
        record
        for rnd in staged_state["bracket"]["rounds"]
        for game, record in zip(
            rnd["games"], staged_state["plan"].get(str(rnd["round"]), []))
        if record is not None and game.get("status") != "final"
        and any(slot.get("team") == "Oregon Ducks" for slot in game["slots"])
    )
    assert custom.index == user_record
    assert savesched.week_slate(payload).count(user_record) == 1


def test_cfp_user_custom_bye_never_uses_fcs_placeholder(monkeypatch):
    """A native CFP record containing FCS crashes CFB 27 on dynasty load.

    Penn State reproduced this on the first 96-team wave: the custom seed had
    a bye, so its engine-owned CFP record was held with an FCS opponent. Format
    10 must instead choose an unused, non-field FBS program while preserving
    one valid user destination and a double-book-free slate.
    """
    from backend import playoff_live
    from backend.saveparse import container, schedule, teams

    user = _cfp_user()
    assert user, "fixture has no current CFP user"
    fmt = eng._fmt(96, [{"teams": 32, "rounds": 1}])
    h = eng.Harness(BASE, user, 11, fmt, monkeypatch)

    out = playoff_live.sync(write=True)
    state = h.state()
    payload = container.decode(h.save.read_bytes()).payload
    store = schedule.parse(payload)
    roster = teams.parse_teams(payload)
    slate = set(schedule.week_slate(payload))
    field = {seed["team"] for seed in out["bracket"]["seeds"]}
    user_games = [game for game in store.games
                  if game.index in slate and not game.official
                  and h.user_row in (game.away_row, game.home_row)]

    assert state.get("wave_format") == playoff_live._WAVE_FORMAT
    assert len(user_games) == 1
    game = user_games[0]
    opponent_row = (game.home_row if game.away_row == h.user_row
                    else game.away_row)
    opponent = roster[opponent_row].name
    assert opponent not in field
    assert not opponent.upper().startswith("FCS ")
    assert eng.slate_double_books(h.save) == 0


def test_format10_rewrites_staged_fcs_cfp_wave(monkeypatch):
    """The crashed Penn State format 9 state repairs from its clean base."""
    import json

    from backend import playoff_live
    from backend.saveparse import container, schedule, teams

    user = _cfp_user()
    assert user, "fixture has no current CFP user"
    fmt = eng._fmt(96, [{"teams": 32, "rounds": 1}])
    h = eng.Harness(BASE, user, 11, fmt, monkeypatch)
    playoff_live.sync(write=True)

    # Recreate the invalid format 9 placement without touching a real save.
    raw = h.save.read_bytes()
    payload = bytearray(container.decode(raw).payload)
    store = schedule.parse(bytes(payload))
    roster = teams.parse_teams(bytes(payload))
    slate = set(schedule.week_slate(bytes(payload)))
    user_game = next(game for game in store.games
                     if game.index in slate and not game.official
                     and h.user_row in (game.away_row, game.home_row))
    fcs_row = next(i for i, team in enumerate(roster)
                   if team.name.upper().startswith("FCS "))
    side = "home_row" if user_game.away_row == h.user_row else "away_row"
    schedule.set_matchup(payload, user_game, **{side: fcs_row})
    h.save.write_bytes(container.encode(raw, bytes(payload)))
    state = h.state()
    state["wave_format"] = 9
    (h.tmp / "live.json").write_text(json.dumps(state), encoding="utf-8")

    recovered = playoff_live.sync(write=True)
    state = h.state()
    payload = container.decode(h.save.read_bytes()).payload
    store = schedule.parse(payload)
    roster = teams.parse_teams(payload)
    slate = set(schedule.week_slate(payload))
    repaired = next(game for game in store.games
                    if game.index in slate and not game.official
                    and h.user_row in (game.away_row, game.home_row))
    opponent_row = (repaired.home_row if repaired.away_row == h.user_row
                    else repaired.away_row)

    assert state.get("wave_format") == playoff_live._WAVE_FORMAT
    assert not roster[opponent_row].name.upper().startswith("FCS ")
    assert eng.slate_double_books(h.save) == 0
    assert any("format 9 custom-bye placeholder" in note
               for note in recovered.get("notes") or [])


def test_engine_declined_records_are_quarantined(monkeypatch):
    # THE DEAD-RECORD TAR PIT (user report 2026-07-10, 128-team run): the real
    # engine consistently declined to sim two slate records. The app unmapped
    # the skipped games at the advance (official-with-no-result), then remapped
    # the user's PATH-PRIORITY games first onto the first free pool records,
    # which were the same dead ones, so the user's own opponent chain never
    # finished and they sat on the FCS fill forever ("I had a double bye").
    # With the quarantine, a skipped record is retired from the pool on the
    # first strike and the rescheduled games land on records that work: the
    # bracket must complete and the user must play every round.
    from backend.saveparse import container, schedule as savesched
    byes = [{"teams": 8, "rounds": 2}, {"teams": 8, "rounds": 1}]
    h = eng.Harness(BASE, "Oregon Ducks", USER_RANK, eng._fmt(32, byes), monkeypatch)
    payload = container.decode(h.save.read_bytes()).payload
    store = savesched.parse(payload)
    dead = [r for r in savesched.week_slate(payload)
            if store.games[r].bowl_row is not None
            and h.user_row not in (store.games[r].away_row,
                                   store.games[r].home_row)][:2]
    assert len(dead) == 2, "fixture slate too small to kill two records"
    h.engine.dead_records = set(dead)
    r = eng.run_hybrid(h, 32, elim_round=0)
    assert r["ok"], r.get("reason")
    assert r["champion"] == "Oregon Ducks"
    assert set(dead) <= set(r["state"].get("dead_records") or []), \
        "declined records were not quarantined"
    # no finished game may still claim a dead record as where it played
    plan = r["state"].get("plan") or {}
    final_recs = {rec
                  for rnd in (r["state"].get("bracket") or {}).get("rounds") or []
                  for g, rec in zip(rnd["games"],
                                    plan.get(str(rnd["round"])) or [])
                  if g.get("status") == "final" and rec is not None}
    assert not (final_recs & set(dead)), \
        "a game finished on a record the engine never simmed"


def test_hybrid_handoff_is_one_way(monkeypatch):
    # Once 16 teams remain, the loop snapshot is retired permanently. The
    # final four rounds then live on successive game-owned postseason weeks,
    # with no completion restore and no attempt to establish a second anchor.
    user = _cfp_user()
    if user is None:
        pytest.skip("fixture save has no CFP first-round team")
    h = eng.Harness(BASE, user, 9, eng._fmt(32), monkeypatch)
    r = eng.run_hybrid(h, 32, elim_round=0)
    assert r["ok"], r.get("reason")
    state = r["state"]
    assert state.get("handoff") is True
    assert state.get("status") == "complete"
    assert not (h.tmp / "cycle_base.sav").exists()
    assert not state.get("postseason_restored")
    assert not state.get("awaiting_anchor"), \
        "the forward endgame tried to establish another cycle anchor"
    assert eng.slate_double_books(h.save) == 0


def test_empty_slate_after_championship_captures_and_persists(monkeypatch):
    """Advancing straight past the title cannot reset the finished bracket.

    The real Tennessee run reached Bowl Season 3, published the championship,
    and emptied SeasonGameRequest before the watcher next synced. The old
    stale-state gate saw no postseason slate, returned before `_fill_results`,
    then replaced the live bracket with a projection after three polls.
    """
    import json

    from backend import playoff_live

    h = eng.Harness(BASE, "Oregon Ducks", 40, eng._fmt(32), monkeypatch)
    reached_title = False
    for _step in range(80):
        out = playoff_live.sync(write=True)
        state = h.state()
        bracket = out.get("bracket") or {}
        rounds = bracket.get("rounds") or []
        assert rounds, "bracket disappeared before the championship"
        native_phase = eng._pre_tail_final(bracket)
        title = rounds[-1]["games"][0]
        title_arrival = (
            all(game.get("status") == "final"
                for rnd in rounds[:-1] for game in rnd["games"])
            and title.get("status") != "final"
            and all(slot.get("type") == "team" for slot in title["slots"])
            and (state.get("plan") or {}).get(str(rounds[-1]["round"]),
                                              [None])[0] is not None
        )
        simulated = h.engine.load()
        if title_arrival:
            assert simulated, "championship was not simulated"
            h.engine.advance_week()  # no watcher capture before this advance
            assert not h.slate(), "post-championship queue did not empty"
            reached_title = True
            break
        playoff_live.sync(write=False)
        if native_phase:
            h.engine.advance_week()
    assert reached_title, "test never reached the championship"

    completed = playoff_live.sync(write=False)
    assert completed.get("status") == "complete"
    assert (completed.get("bracket") or {}).get("champion")
    assert h.state().get("status") == "complete"
    history = json.loads((h.tmp / "history.json").read_text(encoding="utf-8"))
    assert len(history) == 1 and history[0].get("champion")

    # Background polling after completion must keep serving the archived live
    # bracket even though both the week queue and future postseason are empty.
    for _ in range(4):
        polled = playoff_live.sync(write=False)
        assert polled.get("status") == "complete"
        assert (polled.get("bracket") or {}).get("champion")
    assert len(json.loads((h.tmp / "history.json").read_text(
        encoding="utf-8"))) == 1


def test_native_update_is_followed_by_load_not_a_second_update(monkeypatch):
    """Polling after a successful write must not repeat the Update prompt."""
    from backend import playoff_live

    user = _cfp_user()
    if user is None:
        pytest.skip("fixture save has no CFP first-round team")
    h = eng.Harness(BASE, user, 3, eng._fmt(16), monkeypatch)

    written = playoff_live.sync(write=True)
    assert written.get("awaiting_reload") is True
    polled = playoff_live.sync(write=False)
    assert polled.get("awaiting_reload") is True
    assert polled.get("needs_write") is False
    current = next(phase for phase in polled["guide"]["phases"]
                   if phase.get("state") == "current")
    assert next(step["id"] for step in current["steps"]
                if step.get("state") == "current") == "load"


def test_awaiting_reload_never_hides_changed_actions_record(monkeypatch):
    """A stale reload flag cannot bless a save that no longer matches plan."""
    from backend import playoff_live
    from backend.saveparse import container, schedule

    user = _cfp_user()
    if user is None:
        pytest.skip("fixture save has no CFP first-round team")
    h = eng.Harness(BASE, user, 3, eng._fmt(16), monkeypatch)
    written = playoff_live.sync(write=True)
    state = h.state()
    user_game, user_record = h.user_unfinished(
        written["bracket"], state["plan"])
    assert user_game is not None and user_record is not None
    round_key = str(user_game["round"])
    sibling_record = next(record for record in state["plan"][round_key]
                          if record is not None and record != user_record)

    # Keep the Actions request on user_record but recreate the failed on-disk
    # matchup placement: the user game and a CPU sibling occupy each other's
    # SeasonGame records while awaiting_reload remains true.
    raw = h.save.read_bytes()
    payload = bytearray(container.decode(raw).payload)
    store = schedule.parse(bytes(payload))
    user_disk = store.games[user_record]
    sibling_disk = store.games[sibling_record]
    user_pair = (user_disk.away_row, user_disk.home_row)
    sibling_pair = (sibling_disk.away_row, sibling_disk.home_row)
    schedule.set_matchup(payload, user_disk, away_row=sibling_pair[0],
                         home_row=sibling_pair[1])
    schedule.set_matchup(payload, sibling_disk, away_row=user_pair[0],
                         home_row=user_pair[1])
    h.save.write_bytes(container.encode(raw, bytes(payload)))

    polled = playoff_live.sync(write=False)
    assert polled.get("awaiting_reload") is True
    assert polled.get("needs_write") is True
    current = next(phase for phase in polled["guide"]["phases"]
                   if phase.get("state") == "current")
    assert next(step["id"] for step in current["steps"]
                if step.get("state") == "current") == "update"

    repaired = playoff_live.sync(write=True)
    assert repaired.get("save_written")
    repaired_state = h.state()
    repaired_game, repaired_record = h.user_unfinished(
        repaired["bracket"], repaired_state["plan"])
    repaired_payload = container.decode(h.save.read_bytes()).payload
    repaired_store = schedule.parse(repaired_payload)
    expected = {h.user_row}
    expected.update(
        next(i for i, team in enumerate(h.roster)
             if team.name == slot["team"])
        for slot in repaired_game["slots"]
        if slot.get("team") != h.user_name)
    assert {repaired_store.games[repaired_record].away_row,
            repaired_store.games[repaired_record].home_row} == expected
    assert schedule.user_pending_game(repaired_payload) == repaired_record

    verified = playoff_live.sync(write=False)
    assert verified.get("needs_write") is False
    current = next(phase for phase in verified["guide"]["phases"]
                   if phase.get("state") == "current")
    assert next(step["id"] for step in current["steps"]
                if step.get("state") == "current") == "load"


def test_loaded_native_round_stays_on_play_instead_of_update(monkeypatch):
    """A locked, pre-simmed native week is already staged, not write-due."""
    from backend import playoff_live

    user = _cfp_user()
    if user is None:
        pytest.skip("fixture save has no CFP first-round team")
    h = eng.Harness(BASE, user, 3, eng._fmt(16), monkeypatch)

    playoff_live.sync(write=True)
    # Merely loading the dynasty locks and pre-sims the CPU slate. It does not
    # advance the week, which is the exact state that triggered the loop.
    h.engine.load(user_row=h.user_row, official=False)
    loaded = playoff_live.sync(write=False)

    assert loaded.get("awaiting_reload") is False
    assert loaded.get("needs_write") is False
    current = next(phase for phase in loaded["guide"]["phases"]
                   if phase.get("state") == "current")
    assert next(step["id"] for step in current["steps"]
                if step.get("state") == "current") != "update"
    # Clicking Update manually in this state must also be a no-op. Rewriting
    # the clean bridge world here would discard the current pre-sims and start
    # the same loop again.
    redundant = playoff_live.sync(write=True)
    assert not redundant.get("save_written")


def test_bowl_regeneration_never_blanks_a_queued_matchup():
    """An exhausted substitute pool must leave a valid two-team bowl."""
    from backend import playoff_live
    from backend.saveparse import container, schedule, teams

    payload = bytearray(container.decode(BASE.read_bytes()).payload)
    store = schedule.parse(bytes(payload))
    roster = teams.parse_teams(bytes(payload))
    slate = set(schedule.week_slate(bytes(payload)))
    complete_before = {
        record for record in slate
        if record < len(store.games)
        and store.games[record].away_row is not None
        and store.games[record].home_row is not None
    }
    # Deliberately leave no eligible FBS substitute. This recreates the old
    # failure at maximum pressure without needing to drive an entire bracket.
    all_fbs = {team.name for team in roster
               if team.name and not team.name.upper().startswith("FCS ")}
    playoff_live._regenerate_bowls(
        payload, store, roster, all_fbs, [], keep_records=set())
    repaired = schedule.parse(bytes(payload))

    assert all(repaired.games[record].away_row is not None
               and repaired.games[record].home_row is not None
               for record in complete_before)


def test_native_advancement_recovers_winners_without_scores():
    """The next game-owned round is authoritative when score refs are gone."""
    from types import SimpleNamespace

    from backend import playoff_live

    roster = [SimpleNamespace(name=name) for name in ("A", "B", "C", "D")]
    games = [
        SimpleNamespace(away_row=1, home_row=0),
        SimpleNamespace(away_row=3, home_row=2),
        # The title field proves A and C advanced from the two semifinals.
        SimpleNamespace(away_row=2, home_row=0),
    ]
    store = SimpleNamespace(games=games)
    bracket = {
        "rounds": [
            {"round": 1, "name": "Semifinals", "games": [
                {"id": "S1", "status": "scheduled", "slots": [
                    {"type": "team", "team": "A"},
                    {"type": "team", "team": "B"}]},
                {"id": "S2", "status": "scheduled", "slots": [
                    {"type": "team", "team": "C"},
                    {"type": "team", "team": "D"}]},
            ]},
            {"round": 2, "name": "National Championship", "games": [
                {"id": "F", "status": "scheduled", "slots": [
                    {"type": "winner", "game": "S1"},
                    {"type": "winner", "game": "S2"}]},
            ]},
        ]
    }
    notes = playoff_live._recover_native_advancements(
        bracket, {"1": [0, 1]}, store, roster,
        {"semifinal": [0, 1], "championship": [2]}, {2})

    assert [game.get("winner") for game in bracket["rounds"][0]["games"]] \
        == ["A", "C"]
    assert all(game.get("scores") is None
               for game in bracket["rounds"][0]["games"])
    assert notes and "real advancing teams" in notes[0]


def test_locked_week_reset_matches_reference_home_scheduled_status():
    from backend.saveparse import container, schedule

    payload = bytearray(container.decode(BASE.read_bytes()).payload)
    store = schedule.parse(bytes(payload))
    record = next(game for game in store.games
                  if game.bowl_row is not None and game.scheduled)
    before = bytes(payload[record.offset:record.offset + schedule.RECORD_SIZE])
    schedule.reset_locked_matchup_status(payload, record)
    after = bytes(payload[record.offset:record.offset + schedule.RECORD_SIZE])

    assert payload[record.offset + 84] & 0xF0 == 0x60
    assert payload[record.offset + 97] & 0x11 == 0
    assert [index for index, (old, new) in enumerate(zip(before, after))
            if old != new] == [index for index in (84, 97)
                               if before[index] != after[index]]


def test_hybrid_endgame_keeps_custom_championship_bowl(monkeypatch):
    # The handoff changes who owns week progression, not the configured game
    # sites. A custom bowl selected for any final-16 round must still be
    # written onto the native postseason record at that bowl's stadium.
    from backend import playoff, playoff_live
    from backend.saveparse import container, schedule

    fmt = eng._fmt(32)
    fmt["sites"]["championship"] = {
        "mode": "bowls", "bowl": "rose", "venue": "", "city": "",
    }
    fmt = playoff.normalize_format(fmt)
    user = _cfp_user()
    if user is None:
        pytest.skip("fixture save has no CFP first-round team")
    h = eng.Harness(BASE, user, 9, fmt, monkeypatch)
    r = eng.run_hybrid(h, 32, elim_round=0)
    assert r["ok"], r.get("reason")

    bracket = r["state"]["bracket"]
    title = bracket["rounds"][-1]["games"][0]
    assert title["site"]["bowl"]["key"] == "rose"
    rec = r["state"]["plan"][str(bracket["rounds"][-1]["round"])][0]
    payload = container.decode(h.save.read_bytes()).payload
    game = schedule.parse(payload).games[rec]
    assert game.venue_uid == playoff_live._bowl_stadium_handles(payload)["rose bowl"]


@pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture")
def test_bowl_site_resolves_to_bowl_stadium():
    # a format round set to a specific bowl (e.g. the Alamo Bowl) must resolve
    # to THAT bowl's stadium handle, not None. When it returned None the game
    # kept the record's default venue and played at the home team's campus
    # (observed: Michigan's Alamo Bowl game played at Michigan). The engine
    # honors a venue write, so resolving it fixes the site.
    from backend import playoff_live
    from backend.saveparse import container
    payload = container.decode(BASE.read_bytes()).payload
    bowl_handles = playoff_live._bowl_stadium_handles(payload)
    assert bowl_handles, "no bowl stadium handles resolved from the save"
    for bowl in ("Alamo Bowl", "Orange Bowl", "Rose Bowl"):
        if bowl.lower() not in bowl_handles:
            continue
        h = playoff_live._desired_venue({"site": {"type": "bowl", "bowl": {"name": bowl}}},
                                        [], bowl_handles)
        assert h == bowl_handles[bowl.lower()], f"{bowl} did not resolve to its stadium"
        assert h and h >> 24 == 0x80, f"{bowl} handle is not a stadium uid"
    # without a resolvable bowl it declines rather than forcing campus
    assert playoff_live._desired_venue(
        {"site": {"type": "bowl", "bowl": {"name": "Nonexistent Bowl"}}}, [], bowl_handles) is None


@pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture")
def test_field_branding_uses_home_team_field_at_plain_neutral_site():
    # THE ORANGE FIELD: field art keys off the bowl identity (+16), and a
    # CFP-round identity only has art at its native venues (first round =
    # campus, QF/SF = the New Year's Six stadiums), so a neutral- or
    # bowl-sited custom game left with CFP branding renders a blank orange
    # field in-game. A named bowl gets its own presentation. An ordinary
    # neutral user game keeps the selected physical stadium but enters it via
    # the native zero-venue plus HomeTeam.Stadium playoff relationship.
    from backend import playoff_live
    from backend.saveparse import bowls as savebowls, container
    payload = container.decode(BASE.read_bytes()).payload
    btable = savebowls.parse(payload)
    cfp_rows = playoff_live._cfp_round_rows(btable)
    assert sorted(set(cfp_rows.values())) == \
        ["championship", "first_round", "quarterfinal", "semifinal"]
    # a REAL bowl relabeled with a CFP-looking display name (leftover from an
    # earlier build's relabel) must NOT classify as a CFP row
    for b in btable.bowls:
        if b.internal and "cfp" not in b.internal.lower():
            assert b.row not in cfp_rows, f"{b.internal} misclassified as CFP"
    ny6 = {pb.stadium_handle for pb in btable.playoff_bowls if pb.stadium_handle}
    kind_rows = [r for r, k in cfp_rows.items() if k == "first_round"]
    bowl = next(b for b in btable.bowls
                if b.internal and not b.is_cfp and b.stadium_handle
                and b.stadium_handle not in ny6)
    # a campus game keeps the round's CFP branding (the verified native combo)
    assert playoff_live._brand_rows(btable, kind_rows, "first_round", {}, 0,
                                    ny6) == kind_rows
    # An ordinary neutral site for the user's playable game uses team field
    # art. CPU games do not need this presentation treatment because they are
    # simulated without entering the field.
    neutral = {"site": {"type": "neutral"}}
    assert playoff_live._use_home_team_field(neutral, 10, 11, {11})
    assert not playoff_live._use_home_team_field(neutral, 10, 11, set())
    rows = playoff_live._brand_rows(
        btable, kind_rows, "first_round", neutral["site"], 0x80DEADBE, ny6)
    assert rows == kind_rows
    # a bowls-mode site -> the named bowl's identity
    rows = playoff_live._brand_rows(
        btable, kind_rows, "quarterfinal",
        {"type": "bowl", "bowl": {"name": bowl.name}}, bowl.stadium_handle, ny6)
    assert bowl.row in rows and all(r not in cfp_rows for r in rows)
    # a QF at a New Year's Six stadium keeps the round's CFP identity (the
    # engine's own native combo, e.g. a quarterfinal at the Orange Bowl)
    qf_rows = [r for r, k in cfp_rows.items() if k == "quarterfinal"]
    if ny6:
        rows = playoff_live._brand_rows(btable, qf_rows, "quarterfinal",
                                        {"type": "bowl",
                                         "bowl": {"name": "Orange Bowl"}},
                                        next(iter(ny6)), ny6)
        assert rows[:len(qf_rows)] == qf_rows
    # a custom neutral stadium follows the same team-field treatment for a
    # playable user game, regardless of whether that stadium is recognized.
    assert playoff_live._use_home_team_field(
        {"site": {"type": "neutral", "stadium": 999}}, 10, 11, {11})
    # a named bowl keeps its own field and presentation
    assert not playoff_live._use_home_team_field(
        {"site": {"type": "bowl", "bowl": {"name": bowl.name}}},
        10, 11, {11})
    # ... except a championship, whose art travels with the venue natively
    ncg_rows = [r for r, k in cfp_rows.items() if k == "championship"]
    rows = playoff_live._brand_rows(btable, ncg_rows, "championship",
                                    {"type": "neutral"}, 0x80DEADBE, ny6)
    assert rows[:len(ncg_rows)] == ncg_rows


def test_cycle_user_plain_neutral_keeps_stadium_with_team_field(monkeypatch):
    """A playable neutral uses the selected stadium through native CFP art."""
    from backend import playoff_live
    from backend.saveparse import bowls, container, schedule, stadiums

    user = "Oregon Ducks"
    fmt = eng._fmt(32)
    fmt["sites"]["rounds"] = [{
        "mode": "neutral", "bowls": [], "venue": "Custom Neutral",
        "city": "", "stadium": 0, "games": [],
    }]
    h = eng.Harness(BASE, user, 13, fmt, monkeypatch)
    # Reproduce format 20's metadata-loss bug: the save retains the recipe
    # string, but the bracket no longer remembers that Dynasty+ wrote it.
    legacy_raw = h.save.read_bytes()
    legacy_payload = bytearray(container.decode(legacy_raw).payload)
    assert stadiums.set_field_recipe(legacy_payload, 0, "ore_recipe")
    h.save.write_bytes(container.encode(legacy_raw, bytes(legacy_payload)))
    out = playoff_live.sync(write=True)
    state = h.state()
    user_game = next(
        (game, state["plan"][str(rnd["round"])][index])
        for rnd in out["bracket"]["rounds"]
        for index, game in enumerate(rnd["games"])
        if game.get("status") != "final"
        and any(slot.get("team") == user for slot in game["slots"])
    )
    game, record = user_game
    assert game["site"]["type"] == "neutral"
    assert record is not None

    payload = container.decode(h.save.read_bytes()).payload
    staged = schedule.parse(payload).games[record]
    selected_stadium = stadiums.stadium_table(payload)[0]
    btable = bowls.parse(payload)
    cfp_rows = playoff_live._cfp_round_rows(btable)
    assert staged.home_row == h.user_row
    assert staged.venue_uid is None, \
        "native home-playoff field must not carry a SeasonGame venue override"
    assert stadiums.team_home_handle(payload, staged.home_row) == selected_stadium
    assert cfp_rows.get(staged.bowl_row) == "first_round"
    assert btable.by_row(staged.bowl_row).stadium_handle == 0
    assert staged.bowl_row != bowls.GENERIC_ROW
    assert stadiums.field_recipe_name(payload, 0) == ""
    assert game["_disk"]["team_stadium"] == {
        "team": staged.home_row,
        "selected": selected_stadium,
        "original": stadiums.team_home_handle(
            container.decode(BASE.read_bytes()).payload, staged.home_row),
    }
    assert game["_disk"]["bowl_stadium"] == {
        "row": staged.bowl_row, "selected": 0, "original": 0,
    }
    assert game["_disk"]["bowl_row"] == staged.bowl_row
    disk_before_probe = copy.deepcopy(game["_disk"])
    playoff_live._apply_to_save(
        out["bracket"], state["plan"], regen_bowls=False,
        user_rows={h.user_row}, dry_run=True)
    assert game["_disk"] == disk_before_probe, \
        "a read-only update probe erased neutral-field staging metadata"
    again = playoff_live.sync(write=True)
    assert not again.get("save_written"), \
        "a fully staged field override created an Update Dynasty File loop"
    assert h.engine.load(h.user_row, "win") > 0
    played_payload = container.decode(h.save.read_bytes()).payload
    played = schedule.parse(played_payload).games[record]
    assert played.official and played.has_result


def test_cycle_second_round_campus_game_uses_cfp_field_identity(monkeypatch):
    """A campus game never inherits the borrowed record's bowl package.

    The Notre Dame 64-team run correctly put the second-round game at USC,
    but its borrowed record retained ``Military_Bowl`` internally. Renaming
    the display label did not change CFB's field/presentation asset lookup, so
    the Coliseum showed Military Bowl art. Every playable campus wave must
    swap onto a native first-round CFP identity while keeping venue=None, the
    engine's home-campus representation.
    """
    from backend import playoff_live
    from backend.saveparse import bowls, container, schedule

    user = "Oregon Ducks"
    fmt = eng._fmt(64)
    campus = {"mode": "higher_seed", "bowls": [], "games": []}
    fmt["sites"]["rounds"] = [dict(campus), dict(campus)]
    h = eng.Harness(BASE, user, 13, fmt, monkeypatch)

    first = playoff_live.sync(write=True)
    state = h.state()
    user_game, record = h.user_unfinished(first["bracket"], state["plan"])
    assert user_game is not None and record is not None
    assert user_game["site"]["type"] == "campus"
    payload = container.decode(h.save.read_bytes()).payload
    staged = schedule.parse(payload).games[record]
    btable = bowls.parse(payload)
    assert staged.venue_uid is None
    assert playoff_live._cfp_round_rows(btable).get(staged.bowl_row) == \
        "first_round"
    assert "military" not in btable.by_row(staged.bowl_row).internal.lower()

    assert h.engine.load(h.user_row, "win") > 0
    playoff_live.sync(write=False)

    second_game = None
    second_record = None
    for _ in range(5):
        out = playoff_live.sync(write=True)
        state = h.state()
        for rnd in out["bracket"]["rounds"]:
            recs = state["plan"].get(str(rnd["round"])) or []
            for game, rec in zip(rnd["games"], recs):
                if rnd["round"] == 2 and game.get("status") != "final" \
                        and any(slot.get("team") == user
                                for slot in game["slots"]):
                    second_game, second_record = game, rec
        if second_game is not None and second_record is not None:
            break
        assert h.engine.load() > 0
        playoff_live.sync(write=False)

    assert second_game is not None and second_record is not None
    assert second_game["site"]["type"] == "campus"
    payload = container.decode(h.save.read_bytes()).payload
    staged = schedule.parse(payload).games[second_record]
    btable = bowls.parse(payload)
    assert staged.venue_uid is None
    assert playoff_live._cfp_round_rows(btable).get(staged.bowl_row) == \
        "first_round"
    assert "military" not in btable.by_row(staged.bowl_row).internal.lower()


def test_native_plain_neutral_field_keeps_stadium_and_progresses(monkeypatch):
    """Native neutral treatment must not break the final-16 path."""
    from backend import playoff_live
    from backend.saveparse import bowls, container, schedule, stadiums

    user = "Oregon Ducks"
    fmt = eng._fmt(16)
    neutral = {
        "mode": "neutral", "bowls": [], "venue": "Custom Neutral",
        "city": "", "stadium": 0, "games": [],
    }
    fmt["sites"]["rounds"] = [dict(neutral) for _ in range(3)]
    h = eng.Harness(BASE, user, 1, fmt, monkeypatch)

    first = playoff_live.sync(write=True)
    state = h.state()
    user_game, record = h.user_unfinished(first["bracket"], state["plan"])
    assert user_game is not None and record is not None
    payload = container.decode(h.save.read_bytes()).payload
    staged = schedule.parse(payload).games[record]
    selected_stadium = stadiums.stadium_table(payload)[0]
    btable = bowls.parse(payload)
    assert staged.venue_uid is None
    assert stadiums.team_home_handle(payload, staged.home_row) == selected_stadium
    assert playoff_live._cfp_round_rows(btable).get(staged.bowl_row) == \
        "first_round"
    assert btable.by_row(staged.bowl_row).stadium_handle == 0
    assert stadiums.field_recipe_name(payload, 0) == ""

    result = eng.run_native(h, 16, elim_round=0)
    assert result["ok"], result.get("reason")
    assert result["champion"] == user


@pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture")
def test_stadium_field_recipe_writer_round_trips_without_stadium_handle():
    """The legacy schema value is independent from the stadium handle."""
    from backend.saveparse import container, stadiums

    payload = bytearray(container.decode(BASE.read_bytes()).payload)
    handles_before = stadiums.stadium_table(bytes(payload))
    assert stadiums.field_recipe_name(bytes(payload), 0) == ""
    assert stadiums.set_field_recipe(payload, 0, "ore_recipe")
    assert stadiums.field_recipe_name(bytes(payload), 0) == "ore_recipe"
    assert stadiums.stadium_table(bytes(payload)) == handles_before
    assert stadiums.set_field_recipe(payload, 0, "")
    assert stadiums.field_recipe_name(bytes(payload), 0) == ""


def test_plain_neutral_home_is_the_better_seed_after_an_upset():
    """Bracket branch order must not decide the field owner."""
    from backend import playoff_live

    game = {
        "site": {"type": "neutral", "stadium": 177},
        "slots": [
            {"type": "team", "team": "Virginia Cavaliers", "seed": 18},
            {"type": "team", "team": "Texas Tech Red Raiders", "seed": 7},
        ],
    }
    home, away = playoff_live._neutral_home_slots(game, game["slots"])
    assert home["team"] == "Texas Tech Red Raiders"
    assert away["team"] == "Virginia Cavaliers"

    # A named bowl owns its own presentation and retains authored orientation.
    game["site"]["bowl"] = {"name": "Orange Bowl"}
    home, away = playoff_live._neutral_home_slots(game, game["slots"])
    assert home["team"] == "Virginia Cavaliers"
    assert away["team"] == "Texas Tech Red Raiders"


@pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture")
def test_plain_neutral_team_stadium_is_restored_after_final(monkeypatch,
                                                            tmp_path):
    """The temporary venue relationship cannot leak past the played game."""
    from datetime import datetime

    from backend import confsetup, playoff_live
    from backend.saveparse import container, stadiums, teams

    raw = BASE.read_bytes()
    payload = bytearray(container.decode(raw).payload)
    roster = teams.parse_teams(bytes(payload))
    team_row = next(i for i, team in enumerate(roster)
                    if team.name == "Oregon Ducks")
    original = stadiums.team_home_handle(bytes(payload), team_row)
    selected = next(handle for handle in stadiums.stadium_table(bytes(payload))
                    if handle != original)
    assert stadiums.set_team_home_handle(payload, team_row, selected)

    encoded = container.encode(raw, bytes(payload), saved_at=datetime.now())
    save = tmp_path / "DYNASTY-NEUTRAL-RESTORE"
    save.write_bytes(encoded)
    ctx = {"raw": encoded, "payload": bytes(payload), "path": save,
           "roster": roster}
    monkeypatch.setattr(confsetup, "_read_table", lambda: dict(ctx))
    monkeypatch.setattr(confsetup, "_backup_once", lambda _path: None)

    bracket = {"rounds": [{"round": 1, "games": [{
        "id": "played", "status": "final", "slots": [],
        "_disk": {"team_stadium": {
            "team": team_row, "selected": selected, "original": original,
        }},
    }]}]}
    result = playoff_live._apply_to_save(
        bracket, {}, regen_bowls=False, only_rounds=set())
    assert result.get("written"), result
    restored = container.decode(save.read_bytes()).payload
    assert stadiums.team_home_handle(restored, team_row) == original


@pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture")
def test_engrave_rewrites_user_official_records(monkeypatch, tmp_path):
    # THE ENGRAVE: after the completion restore and the cosmetic bowl weeks,
    # the user's OFFICIAL postseason records are rewritten in place with the
    # custom run's matchups, venues, and scores, so the season schedule shows
    # the real playoff. Only records already holding the user are touched.
    from datetime import datetime
    from backend import playoff_live, confsetup
    from backend.saveparse import container, schedule, stadiums, teams
    raw = BASE.read_bytes()
    payload = bytearray(container.decode(raw).payload)
    store = schedule.parse(bytes(payload))
    roster = teams.parse_teams(bytes(payload))
    rows_by_name = {t.name: i for i, t in enumerate(roster)}
    # pick a scheduled bowl record; its home team plays the user. Mark it
    # OFFICIAL with a cosmetic result (what the engine's throwaway sim leaves)
    grec = next(g for g in store.games
                if g.bowl_row is not None and g.scheduled
                and g.home_row is not None and roster[g.home_row].name
                and g.away_row is not None and roster[g.away_row].name)
    user_row = grec.home_row
    user = roster[user_row].name
    off = store.records_off + grec.index * schedule.RECORD_SIZE
    payload[off + 97] |= 0x11  # result exists + official
    import struct
    struct.pack_into(">I", payload, off + 52, 0x80000123)  # request IDs:
    struct.pack_into(">I", payload, off + 60, 0x80000124)  # a played record has them
    schedule.set_result_scores(payload, grec, home=20, away=10)
    # the custom run: the user beat a different opponent 31-28 at a neutral site
    opp_row, opp = next((i, t.name) for i, t in enumerate(roster)
                        if i not in (user_row, grec.away_row) and t.name
                        and not t.name.upper().startswith("FCS"))
    bracket = {"seeds": [{"team": user}, {"team": opp}],
               "rounds": [{"round": 1, "name": "Championship", "games": [
                   {"id": "g1", "status": "final", "winner": user,
                    "slots": [{"type": "team", "team": user},
                              {"type": "team", "team": opp}],
                    "scores": [31, 28],
                    "site": {"type": "neutral", "stadium": 3}}]}]}
    enc = container.encode(raw, bytes(payload), saved_at=datetime.now())
    save = tmp_path / "DYNASTY-ENGRAVE"
    save.write_bytes(enc)
    ctx = {"raw": enc, "payload": bytes(payload), "path": save, "roster": roster}
    monkeypatch.setattr(confsetup, "_read_table", lambda: dict(ctx))
    monkeypatch.setattr(confsetup, "_backup_once", lambda p: None)
    r = playoff_live._engrave_user_games(bracket, {user})
    assert r.get("written") and r.get("games") == 1, r
    after = schedule.parse(container.decode(save.read_bytes()).payload)
    g2 = after.games[grec.index]
    assert (g2.home_row, g2.away_row) == (user_row, opp_row), \
        "matchup not rewritten to the custom game"
    assert (g2.home_score, g2.away_score) == (31, 28), "scores not engraved"
    assert g2.official and g2.has_result, "official result state disturbed"
    handles = stadiums.stadium_table(container.decode(enc).payload)
    assert g2.venue_uid == handles[3], "neutral venue not engraved"


@pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture")
def test_cfp_record_refuses_foreign_venue():
    # in-place writes (stock mode / the calendar tail) target the ENGINE's own
    # CFP records, whose identity cannot be repointed safely; a venue their
    # art cannot render (anything nonzero for the first round, non-NY6 for
    # QF/SF) must be refused so the game keeps a native venue instead of the
    # blank orange field.
    from backend import playoff_live
    from backend.saveparse import bowls as savebowls, container
    payload = container.decode(BASE.read_bytes()).payload
    btable = savebowls.parse(payload)
    cfp_rows = playoff_live._cfp_round_rows(btable)
    ny6 = {pb.stadium_handle for pb in btable.playoff_bowls if pb.stadium_handle}
    r1 = next(r for r, k in cfp_rows.items() if k == "first_round")
    qf = next(r for r, k in cfp_rows.items() if k == "quarterfinal")
    ncg = next(r for r, k in cfp_rows.items() if k == "championship")
    real = next(b.row for b in btable.bowls if not b.is_cfp and b.stadium_handle)
    foreign = 0x80DEADBE
    assert not playoff_live._venue_safe_for_record(r1, foreign, cfp_rows, ny6)
    assert not playoff_live._venue_safe_for_record(qf, foreign, cfp_rows, ny6)
    if ny6:
        assert playoff_live._venue_safe_for_record(qf, next(iter(ny6)), cfp_rows, ny6)
    assert playoff_live._venue_safe_for_record(ncg, foreign, cfp_rows, ny6)
    assert playoff_live._venue_safe_for_record(real, foreign, cfp_rows, ny6)
    assert playoff_live._venue_safe_for_record(r1, 0, cfp_rows, ny6)


def test_user_not_in_field_plays_own_bowl(monkeypatch):
    # ranked out of a 128-team field: the custom bracket sims around the user,
    # who keeps their own engine bowl and never hosts a CPU wave game.
    h = eng.Harness(BASE, "Oregon Ducks", 400, eng._fmt(128), monkeypatch)
    r = eng.run_hybrid(h, 128, elim_round=0)
    assert r["ok"], r.get("reason")
    assert r["champion"] and r["champion"] != "Oregon Ducks"
    assert r["user_played"] == 0


# ---------------------------------------------------------------------------
# Mode selection: the exact 12-team shape is STOCK, every bracket of 16 or
# fewer teams is NATIVE, and larger brackets are HYBRID (cycle only until 16
# remain, then follow the native postseason calendar). Fast classification
# checks, separate from the full emulated loops above.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture")
def test_native_shape_uses_stock_mode(monkeypatch):
    from backend import playoff, playoff_live
    from backend.saveparse import container
    h = eng.Harness(BASE, "Oregon Ducks", 1,
                    eng._fmt(12, [{"teams": 4, "rounds": 1}]), monkeypatch)
    payload = container.decode(h.save.read_bytes()).payload
    bracket = playoff.build_bracket(h.dynasty, h.fmt)
    assert [r["name"] for r in bracket["rounds"]] == \
        ["First Round", "Quarterfinals", "Semifinals", "National Championship"]
    assert playoff_live.stock_mode_fits(
        bracket, playoff_live._postseason_slots(payload))


@pytest.mark.skipif(BASE is None, reason="no CFBMOD_TEST_BASE_SAVE fixture")
@pytest.mark.parametrize("size,byes,mode", [
    (2, [], "native"), (4, [], "native"), (8, [], "native"),
    (16, [], "native"), (32, [], "hybrid"), (128, [], "hybrid"),
])
def test_custom_bracket_mode(size, byes, mode, monkeypatch):
    from backend import playoff, playoff_live
    from backend.saveparse import container
    h = eng.Harness(BASE, "Oregon Ducks", 13, eng._fmt(size, byes), monkeypatch)
    payload = container.decode(h.save.read_bytes()).payload
    bracket = playoff.build_bracket(h.dynasty, h.fmt)
    slots = playoff_live._postseason_slots(payload)
    assert playoff_live.classify_mode(bracket, slots) == mode


@pytest.mark.parametrize("size", [2, 4, 8])
def test_small_bracket_runs_natively(size, monkeypatch):
    # Small brackets start on the matching later bowl week and then progress
    # normally, one real postseason week per custom round.
    h = eng.Harness(BASE, "Oregon Ducks", 2, eng._fmt(size), monkeypatch)
    r = eng.run_native(h, size, elim_round=0)
    assert r["ok"], r.get("reason")
    assert r["state"].get("mode") == "native"
    assert r["champion"] == "Oregon Ducks"
    assert r["user_played"] == int(math.log2(size))


def test_small_bracket_user_out_of_field(monkeypatch):
    # the second half of the report: with the field seeded correctly the
    # reporter's team was OUT of the 4-team bracket; the bracket must still
    # sim to a champion around them instead of stalling.
    h = eng.Harness(BASE, "Oregon Ducks", 13, eng._fmt(4), monkeypatch)
    r = eng.run_native(h, 4, elim_round=0)
    assert r["ok"], r.get("reason")
    assert r["champion"] and r["champion"] != "Oregon Ducks"
    assert r["user_played"] == 0


def test_selection_reseeds_on_poll_edit_until_first_final(monkeypatch):
    # THE PRE-PLAYOFF EDIT WINDOW: after the field freezes but before any
    # game is final, editing the committee ranking re-picks and re-seeds the
    # field on the next sync (this is how "edit the polls right before the
    # playoff starts" works); once a result is recorded the bracket is
    # history and stops following the poll.
    import copy
    h = eng.Harness(BASE, "Oregon Ducks", 2, eng._fmt(4), monkeypatch)
    out = playoff_live_sync_selected(h)
    seeds0 = [s["team"] for s in out["bracket"]["seeds"]]
    assert "Oregon Ducks" in seeds0
    # hand-edit the poll: drop the user out of the top 4 entirely
    poll = copy.deepcopy(h.dynasty["all_teams"])
    others = [p for p in poll if p["team"] != "Oregon Ducks"]
    user = next(p for p in poll if p["team"] == "Oregon Ducks")
    reordered = others[:8] + [user] + others[8:]
    for i, p in enumerate(reordered):
        p["rank"] = i + 1
    h.dynasty["all_teams"] = reordered
    h.dynasty["national"]["ap_top25"] = reordered
    out2 = playoff_live_sync_selected(h)
    seeds1 = [s["team"] for s in out2["bracket"]["seeds"]]
    assert "Oregon Ducks" not in seeds1, "field did not re-seed from the edited poll"
    assert seeds1 == [p["team"] for p in reordered[:4]]
    # A four-team bracket starts on semifinal week. Advance through the two
    # earlier stock weeks, write that arrival, then play it: the first final
    # locks the custom field against later poll edits.
    h.engine.advance_week()
    h.engine.advance_week()
    playoff_live_sync_selected(h)
    h.engine.load(None, None)
    from backend import playoff_live
    playoff_live.sync(write=False)
    st = h.state()
    finals = [g for rnd in st["bracket"]["rounds"] for g in rnd["games"]
              if g.get("status") == "final"]
    assert finals, "emulator wave produced no finals"
    h.dynasty["all_teams"] = poll  # edit the poll back
    h.dynasty["national"]["ap_top25"] = poll
    out3 = playoff_live.sync(write=False)
    seeds2 = [s["team"] for s in out3["bracket"]["seeds"]]
    assert seeds2 == seeds1, "a bracket with recorded results re-seeded"


def playoff_live_sync_selected(h):
    """sync(write=True) and assert the field is frozen (selected or later)."""
    from backend import playoff_live
    out = playoff_live.sync(write=True)
    assert out.get("status") in ("selected", "in_progress"), out.get("status")
    return out


def test_pristine_write_honors_bracket_orientation(monkeypatch):
    # THE HOME-TEAM REPORT (Florida at SMU presented as a Florida home game):
    # on a pre-lock (pristine) wave write the user must land on the side the
    # BRACKET says, so an away game presents them as the visitor. The user is
    # seeded 2 of 4 in a higher-seed format: their first game hosts them at
    # the opponent only if the opponent seeds higher.
    fmt = eng._fmt(4)
    fmt["sites"]["rounds"] = [{"mode": "higher_seed", "games": []}]
    h = eng.Harness(BASE, "Oregon Ducks", 3, fmt, monkeypatch)
    from backend import playoff_live
    from backend.saveparse import container, schedule as savesched
    h.engine.advance_week()
    h.engine.advance_week()
    out = playoff_live.sync(write=True)
    st = h.state()
    assert st.get("mode") == "native"
    plan = st.get("plan") or {}
    bracket = st.get("bracket") or {}
    ug, urec = h.user_unfinished(bracket, plan)
    assert ug is not None and urec is not None, "user game not mapped"
    # seeded 3: the bracket puts the user in the AWAY slot (slot 1) at the
    # 2-seed's place
    assert ug["slots"][1].get("team") == "Oregon Ducks"
    payload = container.decode(h.save.read_bytes()).payload
    store = savesched.parse(payload)
    g = store.games[urec]
    assert g.away_row == h.user_row, \
        "user written as the home team for an away game"


@pytest.mark.parametrize("size,byes,rank,elim", [
    (8, [], 2, 0),                              # user wins it all
    (8, [], 2, 2),                              # user out in the second round
    (24, [{"teams": 8, "rounds": 1}], 13, 0),   # byes + reseed, user wins
])
def test_reseeded_bracket_completes(size, byes, rank, elim, monkeypatch):
    # THE RESEED OPTION: after every round the survivors re-pair by original
    # seed (best remaining vs worst remaining). Native and hybrid brackets
    # must both reach a champion, and every post-opening round must hold
    # exactly the previous round's winners (plus entering bye seeds).
    h = eng.Harness(BASE, "Oregon Ducks", rank, eng._fmt(size, byes, reseed=True),
                    monkeypatch)
    runner = eng.run_native if size <= 16 else eng.run_hybrid
    r = runner(h, size, elim_round=elim)
    assert r["ok"], r.get("reason")
    assert r["champion"], "no champion crowned"
    if elim == 0:
        assert r["champion"] == "Oregon Ducks"
    else:
        assert r["champion"] != "Oregon Ducks"
        assert r["user_played"] == elim
    bracket = r["state"]["bracket"]
    seed_no = {s["team"]: s["seed"] for s in bracket["seeds"]}
    rounds = bracket["rounds"]
    for i in range(1, len(rounds)):
        prev, rnd = rounds[i - 1], rounds[i]
        winners = {g["winner"] for g in prev["games"]}
        entering = {s["team"] for s in bracket["seeds"]
                    if s.get("entry_round") == rnd["round"]}
        participants = {s["team"] for g in rnd["games"] for s in g["slots"]}
        assert participants == winners | entering, f"round {rnd['round']} entrants wrong"
        entr = sorted(seed_no[t] for t in participants)
        for gi, g in enumerate(rnd["games"]):
            got = [seed_no[s["team"]] for s in g["slots"]]
            assert got == [entr[gi], entr[len(entr) - 1 - gi]], \
                f"round {rnd['round']} game {gi} not reseeded best vs worst"


def _slate_user():
    """A non-FCS team whose engine postseason game is in the base's CURRENT
    slate, so user_engine_week reads "here" and the anchor gate is actually
    consulted."""
    from backend.saveparse import container, schedule, teams
    payload = container.decode(BASE.read_bytes()).payload
    store = schedule.parse(payload)
    roster = teams.parse_teams(payload)
    for r in schedule.week_slate(payload):
        g = store.games[r]
        if g.bowl_row is None:
            continue
        for row in (g.away_row, g.home_row):
            if row is not None and not roster[row].name.upper().startswith("FCS"):
                return roster[row].name
    return None


def _guide_phase(out, key):
    return next((p for p in (out.get("guide") or {}).get("phases") or []
                 if p.get("key") == key), None)


def test_locked_arrival_never_becomes_base(monkeypatch):
    # THE POST-LOCK ANCHOR (user report 2026-07-12, 9-game first round stuck
    # at "0 of 9 recorded"): the user loaded into bowl week BEFORE the app's
    # first sync, so the newest autosave was already locked (the engine had
    # pre-simmed the week). Older builds snapshotted it anyway; every wave
    # written from it had its games cleared to the detached shape the engine
    # never sims, so load-and-exit recorded nothing, forever. The anchor must
    # refuse a locked world and walk the user to a fresh week instead.
    from backend import playoff_live
    user = _slate_user()
    assert user, "fixture has no slate team"
    h = eng.Harness(BASE, user, USER_RANK, eng._fmt(32), monkeypatch)
    h.engine.load()  # the user loads into bowl week before the app ever syncs
    out = playoff_live.sync(write=True)
    assert not (h.tmp / "cycle_base.sav").exists(), \
        "a locked world was snapshotted as the cycle base"
    assert not out.get("save_written"), "a wave was written with no usable base"
    assert not out.get("needs_write")
    anchor = _guide_phase(out, "anchor")
    assert anchor and anchor["state"] == "current", "no recovery phase shown"
    assert anchor["steps"][0]["id"] == "advance"
    assert "advance" in " ".join(n.lower() for n in out.get("notes") or []), \
        "no note telling the user to advance to a fresh week"
    # the user advances: the next arrival world is pre-lock (modeled by the
    # pristine fixture); the playoff must anchor there and start writing
    shutil.copyfile(BASE, h.save)
    out = playoff_live.sync(write=True)
    assert (h.tmp / "cycle_base.sav").exists(), "no anchor at the fresh week"
    assert out.get("save_written"), "wave 1 not written after the anchor"
    r = eng.run_hybrid(h, 32, elim_round=1)
    assert r["ok"], r.get("reason")
    assert r["champion"], "no champion crowned after a blocked first anchor"


def test_locked_base_self_heals(monkeypatch):
    # A run already stuck on a post-lock base (anchored by an older build):
    # the sync must stop the doomed wave loop, guide the user to advance, and
    # re-anchor the whole cycle on the next pre-lock arrival world.
    from backend import playoff_live
    from backend.saveparse import container, schedule as savesched
    user = _slate_user()
    assert user, "fixture has no slate team"
    h = eng.Harness(BASE, user, USER_RANK, eng._fmt(32), monkeypatch)
    # the user LOADED into bowl week and exited before the app first synced:
    # the week is locked and pre-simmed but nothing is official yet (the
    # exact shape of the reported stuck run's autosave)
    h.engine.load(official=False)
    # reproduce the old-build behavior: anchor blindly on the locked world
    with monkeypatch.context() as m:
        m.setattr(playoff_live, "_week_locked", lambda *a, **k: False)
        out = playoff_live.sync(write=True)
    st = h.state()
    assert st.get("base_locked") is True, "fixture did not produce a locked base"
    assert out.get("save_written"), "old-build repro should have written a wave"
    # the stuck shape from the user's attached save: the wave's games sit on
    # their records cleared to the dormant pattern the engine never sims
    payload = container.decode(h.save.read_bytes()).payload
    store = savesched.parse(payload)
    plan = st.get("plan") or {}
    wave_recs = [r for recs in plan.values() for r in recs if r is not None]
    assert wave_recs, "no wave games mapped"
    dormant = [r for r in wave_recs
               if payload[store.games[r].offset + 98] == 0x1D
               and payload[store.games[r].offset + 99] == 0x2D]
    assert dormant, "expected detached (never-simmed) wave records"
    # the self-heal: on the locked week nothing can sim, so the sync must
    # stop prompting update/load and walk the user forward instead
    out = playoff_live.sync(write=False)
    assert not out.get("needs_write") and not out.get("awaiting_reload")
    anchor = _guide_phase(out, "anchor")
    assert anchor and anchor["state"] == "current", "no recovery phase shown"
    # the user advances to a fresh (pre-lock) arrival world: re-anchor there
    shutil.copyfile(BASE, h.save)
    out = playoff_live.sync(write=True)
    st = h.state()
    assert not st.get("base_locked"), "base_locked survived the re-anchor"
    snap = container.decode((h.tmp / "cycle_base.sav").read_bytes()).payload
    assert not playoff_live._week_locked(snap), "re-anchored on a locked world"
    assert out.get("save_written"), "no wave written from the new base"
    r = eng.run_hybrid(h, 32, elim_round=2)
    assert r["ok"], r.get("reason")
    assert r["champion"], "no champion crowned after the self-heal"
