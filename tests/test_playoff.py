"""Playoff format engine: bracket math, selection rules, and the format store."""
import pytest

from backend import playoff


def _fmt(**overrides):
    fmt = {
        "teams": 12,
        "byes": [{"teams": 4, "rounds": 1}],
        "bye_selection": "seeding",
        "auto_bids": {"champions": 0},
        "disqualify": {},
        "notre_dame_rule": False,
        "sites": {"rounds": [], "championship": {"venue": "Test Stadium", "city": "Testville"}},
    }
    fmt.update(overrides)
    return playoff.normalize_format(fmt)


CONFS = ["SEC", "Big Ten", "Big 12", "ACC", "Mountain West", "American", "MAC", "Sun Belt"]


def _dynasty(n_teams=30, overrides=None, conferences=None):
    """A minimal dynasty whose AP poll ranks Team 01..Team NN in order."""
    teams = []
    for i in range(n_teams):
        entry = {
            "rank": i + 1,
            "team": f"Team {i + 1:02d}",
            "abbr": f"T{i + 1:02d}",
            "espn_id": 1000 + i,
            "record": "9-1" if i < 12 else "7-3",
            "conference": (conferences or CONFS)[i % len(conferences or CONFS)],
        }
        if overrides and i + 1 in overrides:
            entry.update(overrides[i + 1])
        teams.append(entry)
    return {
        "season": {"year": 2026, "week": 12, "phase": "regular", "week_label": "Week 12"},
        "team": {"name": "Team 01", "espn_id": 1000},
        "national": {"ap_top25": teams},
    }


# ---------------------------------------------------------------------------
# Structure math
# ---------------------------------------------------------------------------

def test_default_12_team_structure_matches_real_cfp():
    structure = playoff.bracket_structure(_fmt())
    rounds = structure["rounds"]
    assert [r["name"] for r in rounds] == [
        "First Round", "Quarterfinals", "Semifinals", "National Championship"]

    r1 = rounds[0]["games"]
    pairs = {frozenset(s["seed"] for s in g["slots"]) for g in r1}
    assert pairs == {frozenset({8, 9}), frozenset({5, 12}), frozenset({7, 10}), frozenset({6, 11})}

    # Quarterfinals: 1 awaits the 8/9 winner, 4 the 5/12, 2 the 7/10, 3 the 6/11.
    r1_by_pair = {frozenset(s["seed"] for s in g["slots"]): g["id"] for g in r1}
    qf_map = {}
    for g in rounds[1]["games"]:
        seed_slot = next(s for s in g["slots"] if s["type"] == "seed")
        winner_slot = next(s for s in g["slots"] if s["type"] == "winner")
        qf_map[seed_slot["seed"]] = winner_slot["game"]
    assert qf_map[1] == r1_by_pair[frozenset({8, 9})]
    assert qf_map[4] == r1_by_pair[frozenset({5, 12})]
    assert qf_map[2] == r1_by_pair[frozenset({7, 10})]
    assert qf_map[3] == r1_by_pair[frozenset({6, 11})]

    assert structure["seed_entry_round"][1] == 2
    assert structure["seed_entry_round"][5] == 1


def test_four_team_bracket():
    structure = playoff.bracket_structure(_fmt(teams=4, byes=[]))
    rounds = structure["rounds"]
    assert [r["name"] for r in rounds] == ["Semifinals", "National Championship"]
    pairs = {frozenset(s["seed"] for s in g["slots"]) for g in rounds[0]["games"]}
    assert pairs == {frozenset({1, 4}), frozenset({2, 3})}


def test_two_team_bcs_style():
    structure = playoff.bracket_structure(_fmt(teams=2, byes=[]))
    assert len(structure["rounds"]) == 1
    assert structure["rounds"][0]["name"] == "National Championship"


def test_double_bye_structure():
    fmt = _fmt(teams=11, byes=[{"teams": 1, "rounds": 2}, {"teams": 2, "rounds": 1}])
    assert playoff.validate_format(fmt) == []
    structure = playoff.bracket_structure(fmt)
    entry = structure["seed_entry_round"]
    assert entry[1] == 3  # double bye straight to the semifinals
    assert entry[2] == 2 and entry[3] == 2
    assert all(entry[s] == 1 for s in range(4, 12))


def test_open_bracket_needs_power_of_two():
    problems = playoff.validate_format(_fmt(teams=6, byes=[]))
    assert problems and "power of two" in problems[0]
    assert playoff.validate_format(_fmt(teams=6, byes=[{"teams": 2, "rounds": 1}])) == []


def test_six_team_pairs_like_nfl():
    structure = playoff.bracket_structure(_fmt(teams=6, byes=[{"teams": 2, "rounds": 1}]))
    r1 = {frozenset(s["seed"] for s in g["slots"]) for g in structure["rounds"][0]["games"]}
    assert r1 == {frozenset({4, 5}), frozenset({3, 6})}


def test_all_byes_normalize_away():
    fmt = playoff.normalize_format({"teams": 4, "byes": [{"teams": 4, "rounds": 1}]})
    assert fmt["byes"] == []


def test_field_size_bounds():
    assert playoff.validate_format(playoff.normalize_format({"teams": 0}))
    assert playoff.validate_format(playoff.normalize_format({"teams": 129}))
    assert playoff.validate_format(playoff.normalize_format({"teams": 128})) == []


def test_suggest_byes():
    assert playoff.suggest_byes(12) == [{"rounds": 1, "teams": 4}]
    assert playoff.suggest_byes(16) == []
    assert playoff.suggest_byes(24) == [{"rounds": 1, "teams": 8}]


def test_every_field_size_builds_with_its_standard_bye_shape():
    for teams in range(1, 129):
        fmt = _fmt(teams=teams, byes=playoff.suggest_byes(teams))
        assert playoff.validate_format(fmt) == [], teams
        structure = playoff.bracket_structure(fmt)
        assert len(structure["seed_entry_round"]) == teams


def test_every_field_size_has_native_final_sixteen_tail():
    """Every standard shape from 1 through 128 reaches the same native tail."""
    from backend import playoff_live

    for teams in range(1, 129):
        fmt = _fmt(teams=teams, byes=playoff.suggest_byes(teams))
        bracket = playoff.build_bracket(_dynasty(teams), fmt)
        mode = playoff_live.classify_mode(bracket)
        if teams <= 16:
            assert mode in {"stock", "native"}, teams
            assert playoff_live.native_tail_rounds(bracket) == {
                str(rnd["round"]) for rnd in bracket["rounds"]
            }, teams
        else:
            assert mode == "hybrid", teams
            tail = playoff_live.native_tail_rounds(bracket)
            assert len(tail) == 4, teams
            tail_rounds = [rnd for rnd in bracket["rounds"]
                           if str(rnd["round"]) in tail]
            assert [len(rnd["games"]) for rnd in tail_rounds] == [8, 4, 2, 1]


def test_underfilled_stock_shapes_run_native_not_stock():
    """Only the game's EXACT 12-team shape (4+4+2+1 games) is stock mode. A
    field whose byes underfill a stock week (a 10-team bracket's 2-game first
    round, reported 2026-07-15 as 'says this is the game's native 12-team
    playoff') leaves engine-owned records unclaimed, which only native mode's
    per-week FCS neutralize handles."""
    from backend import playoff_live

    for teams in (9, 10, 11):
        fmt = _fmt(teams=teams, byes=playoff.suggest_byes(teams))
        bracket = playoff.build_bracket(_dynasty(teams), fmt)
        assert playoff_live.classify_mode(bracket) == "native", teams
    bracket = playoff.build_bracket(
        _dynasty(12), _fmt(teams=12, byes=playoff.suggest_byes(12)))
    assert playoff_live.classify_mode(bracket) == "stock"


def test_user_matchup_guide_directs_user_to_play_without_owner_changes():
    """A scheduled user game is playable with no ownership workflow."""
    from types import SimpleNamespace

    from backend import playoff_live

    bracket = playoff.build_bracket(
        _dynasty(32), _fmt(teams=32, byes=[]))
    guide = playoff_live._build_guide(
        status="selected", mode="cycle", bracket=bracket,
        plan={}, store=SimpleNamespace(games=[]), user_names={"Team 01"},
        needs_write=False, awaiting_reload=True, slate_len=28,
        user_present=True, user_native=True,
        native_rounds=playoff_live.native_tail_rounds(bracket),
    )
    load = next(
        step for phase in guide["phases"] for step in phase.get("steps") or []
        if phase["key"] == "round-1" and step["id"] == "load"
    )
    assert load["detail"] == (
        "Your correct matchup is scheduled. Open the Actions tab and choose "
        "Play Game."
    )
    assert "owner" not in load["detail"].lower()
    assert "retire" not in load["detail"].lower()


def test_every_editor_valid_single_double_triple_bye_shape_builds():
    """Exhaust every bye combination exposed by ByeTierEditor.

    Solving the opening-slot equation first avoids iterating millions of
    combinations that validation would immediately reject. Each accepted
    shape is still normalized, validated, and built through production code.
    """
    powers = [2 ** exponent for exponent in range(11)]
    built = 0
    for teams in range(1, 129):
        for triple in range(teams):
            for double in range(teams - triple):
                max_single = teams - triple - double - 1
                if max_single < 0:
                    continue
                base_weight = teams + (7 * triple) + (3 * double)
                for total_weight in powers:
                    single = total_weight - base_weight
                    if not 0 <= single <= max_single:
                        continue
                    byes = [
                        {"rounds": rounds, "teams": count}
                        for rounds, count in (
                            (3, triple), (2, double), (1, single))
                        if count
                    ]
                    fmt = _fmt(teams=teams, byes=byes)
                    assert playoff.validate_format(fmt) == [], (teams, byes)
                    structure = playoff.bracket_structure(fmt)
                    assert len(structure["seed_entry_round"]) == teams
                    built += 1
    assert built == 52_307


@pytest.mark.parametrize("user_seed", [1, 21, 32])
def test_large_bracket_prioritizes_bye_users_immediate_feeder(user_seed):
    """A bye user's open opponent must claim a scarce wave record first.

    A 96-team field has 32 first-round games, but a real bowl-week slate has
    only 28 host records. The USC report was seed 21 waiting in round two for
    R1G16 while all other first-round games ran. Seeds at both edges guard
    against fixing that one bracket position by accident.
    """
    from types import SimpleNamespace

    from backend import playoff_live

    dynasty = _dynasty(96)
    user = f"Team {user_seed:02d}"
    dynasty["team"] = {"name": user, "espn_id": 9999}
    bracket = playoff.build_bracket(
        dynasty,
        _fmt(teams=96, byes=[{"teams": 32, "rounds": 1}]),
    )
    user_game = next(
        game
        for rnd in bracket["rounds"]
        for game in rnd["games"]
        if any(slot.get("team") == user for slot in game["slots"])
    )
    direct_feeders = {slot["game"] for slot in user_game["slots"]
                      if slot.get("game")}
    assert len(direct_feeders) == 1
    direct = next(iter(direct_feeders))

    immediate, later = playoff_live._user_path_groups(bracket, {user})
    assert direct in immediate
    assert direct not in later

    # One generic host record makes the priority observable: regardless of
    # the feeder's game number, it must be the only matchup assigned.
    store = SimpleNamespace(
        games=[SimpleNamespace(away_row=None, home_row=None)],
    )
    rows_by_name = {
        seed["team"]: row for row, seed in enumerate(bracket["seeds"])
    }
    plan = {}
    changed = playoff_live._assign_records_cycle(
        bracket, plan, [0], store, rows_by_name,
        priority_names={user},
        path_ids=immediate | later,
        immediate_path_ids=immediate,
        user_alive=True,
    )
    assert changed
    assigned = {
        game["id"]
        for rnd in bracket["rounds"]
        for game, record in zip(rnd["games"], plan[str(rnd["round"])])
        if record == 0
    }
    assert assigned == {direct}


def test_cycle_finishes_active_round_before_ready_user_game():
    """A ready later user game cannot strand the current round's last wave."""
    from types import SimpleNamespace

    from backend import playoff_live

    completed = []
    waiting = []
    rows_by_name = {"SMU Mustangs": 0, "South Carolina Gamecocks": 1}
    next_row = 2
    for index in range(60):
        names = (f"Round One {index:02d} A", f"Round One {index:02d} B")
        rows_by_name[names[0]] = next_row
        rows_by_name[names[1]] = next_row + 1
        next_row += 2
        game = {
            "id": f"R1G{index + 1}",
            "status": "final" if index < 55 else "scheduled",
            "slots": [{"type": "team", "team": name} for name in names],
        }
        (completed if index < 55 else waiting).append(game)
    user_game = {
        "id": "R2G2",
        "status": "scheduled",
        "record_index": 380,
        "_disk": {"away": 1, "home": 0},
        "slots": [
            {"type": "team", "team": "SMU Mustangs"},
            {"type": "team", "team": "South Carolina Gamecocks"},
        ],
    }
    bracket = {
        "rounds": [
            {"round": 1, "games": completed + waiting},
            {"round": 2, "games": [user_game]},
        ],
    }
    original_round_one = list(range(55)) + [None] * 5
    plan = {"1": list(original_round_one), "2": [380]}

    notes = playoff_live._enforce_cycle_round_gate(bracket, plan)
    assert notes
    assert plan["1"] == original_round_one
    assert plan["2"] == [None]
    assert "record_index" not in user_game
    assert "_disk" not in user_game

    store = SimpleNamespace(
        games=[SimpleNamespace(away_row=None, home_row=None) for _ in range(6)],
    )
    changed = playoff_live._assign_records_cycle(
        bracket, plan, list(range(6)), store, rows_by_name,
        priority_names={"SMU Mustangs"}, user_alive=True,
    )
    assert changed
    assert all(record is not None for record in plan["1"][-5:])
    assert plan["2"] == [None]


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def test_straight_seeding_takes_top_n():
    bracket = playoff.build_bracket(_dynasty(), _fmt())
    seeds = bracket["seeds"]
    assert [s["team"] for s in seeds[:4]] == ["Team 01", "Team 02", "Team 03", "Team 04"]
    assert len(seeds) == 12
    assert [b["seed"] for b in bracket["byes"]] == [1, 2, 3, 4]


def test_auto_bid_pulls_in_lower_ranked_champion():
    # Give every top-13 team the same conference so the 5th-best champion sits
    # at rank 14; with 5 champion auto-bids it must make a 12-team field.
    confs = {i: {"conference": "SEC"} for i in range(1, 14)}
    confs[2] = {"conference": "Big Ten"}
    confs[3] = {"conference": "Big 12"}
    confs[4] = {"conference": "ACC"}
    confs[14] = {"conference": "Mountain West"}
    dyn = _dynasty(overrides=confs, conferences=["SEC"])
    fmt = _fmt(auto_bids={"champions": 5})
    bracket = playoff.build_bracket(dyn, fmt)
    teams = [s["team"] for s in bracket["seeds"]]
    assert "Team 14" in teams
    assert "Team 12" not in teams  # bumped by the group-of-five champion
    t14 = next(s for s in bracket["seeds"] if s["team"] == "Team 14")
    assert t14.get("auto_bid") and t14.get("champ")


def test_notre_dame_rule_guarantees_bid():
    # ND at rank 12; five champion auto-bids include a rank-14 champion, which
    # squeezes the field so the last at-large would go to rank 11 over ND.
    confs = {i: {"conference": "SEC"} for i in range(1, 14)}
    confs[2] = {"conference": "Big Ten"}
    confs[3] = {"conference": "Big 12"}
    confs[4] = {"conference": "ACC"}
    confs[14] = {"conference": "Mountain West"}
    confs[12] = {"team": "Notre Dame Fighting Irish", "espn_id": 87, "conference": "FBS Independents"}
    dyn = _dynasty(overrides=confs, conferences=["SEC"])

    without = playoff.build_bracket(dyn, _fmt(auto_bids={"champions": 5}, notre_dame_rule=False))
    assert "Notre Dame Fighting Irish" not in [s["team"] for s in without["seeds"]]

    with_rule = playoff.build_bracket(dyn, _fmt(auto_bids={"champions": 5}, notre_dame_rule=True))
    teams = [s["team"] for s in with_rule["seeds"]]
    assert "Notre Dame Fighting Irish" in teams
    nd = next(s for s in with_rule["seeds"] if s["espn_id"] == 87)
    assert nd.get("nd_rule")


def test_disqualification_max_losses():
    dyn = _dynasty(overrides={2: {"record": "7-5"}})
    fmt = _fmt(disqualify={"max_losses": 4})
    bracket = playoff.build_bracket(dyn, fmt)
    assert "Team 02" not in [s["team"] for s in bracket["seeds"]]
    excluded = bracket["selection"]["excluded"]
    assert any(e["team"] == "Team 02" and "losses" in e["reason"].lower() for e in excluded)


def test_champions_only_field():
    dyn = _dynasty()
    fmt = _fmt(teams=8, byes=[], disqualify={"champions_only": True})
    bracket = playoff.build_bracket(dyn, fmt)
    assert all(s.get("champ") for s in bracket["seeds"])


def test_champs_bye_selection_promotes_champions():
    # Conferences cycle through 8 names, so champs are ranks 1-8; force a case
    # where a champion sits below the bye line: 4 byes, champions at 1, 6, 7, 8.
    confs = {i: {"conference": "SEC"} for i in range(2, 6)}
    dyn = _dynasty(overrides=confs)
    fmt = _fmt(bye_selection="champs", auto_bids={"champions": 0})
    bracket = playoff.build_bracket(dyn, fmt)
    top4 = [s["team"] for s in bracket["seeds"][:4]]
    assert top4 == ["Team 01", "Team 06", "Team 07", "Team 08"]


def test_one_team_field_crowns_champion():
    bracket = playoff.build_bracket(_dynasty(), _fmt(teams=1, byes=[]))
    assert bracket["rounds"] == []
    assert bracket["champion"]["team"] == "Team 01"


def test_two_team_field_single_title_game():
    bracket = playoff.build_bracket(_dynasty(), _fmt(teams=2, byes=[]))
    assert len(bracket["rounds"]) == 1
    game = bracket["rounds"][0]["games"][0]
    assert {s["team"] for s in game["slots"]} == {"Team 01", "Team 02"}
    assert game["site"]["type"] == "championship"
    assert game["site"]["venue"] == "Test Stadium"


# ---------------------------------------------------------------------------
# Sites and bowls
# ---------------------------------------------------------------------------

def test_default_sites_campus_then_bowls():
    bracket = playoff.build_bracket(_dynasty(), playoff.normalize_format(playoff.DEFAULT_FORMAT))
    r1, qf, sf, nc = bracket["rounds"]
    assert all(g["site"]["type"] == "campus" for g in r1["games"])
    # Biggest bowls go to the latest round: the semifinals draw the Rose and
    # Sugar, the quarterfinals the rest of the New Year's Six.
    assert [g["site"]["bowl"]["key"] for g in sf["games"]] == ["rose", "sugar"]
    assert [g["site"]["bowl"]["key"] for g in qf["games"]] == ["orange", "cotton", "fiesta", "peach"]
    assert nc["games"][0]["site"]["type"] == "championship"
    assert nc["games"][0]["site"]["bowl"] is None  # neutral title game by default
    # First-round hosts are the better seeds.
    for g in r1["games"]:
        assert g["site"]["host_espn_id"] == g["slots"][0]["espn_id"]
        assert g["slots"][0]["seed"] < g["slots"][1]["seed"]


def test_championship_can_be_a_bowl():
    fmt = playoff.normalize_format({
        **playoff.DEFAULT_FORMAT,
        "sites": {
            "rounds": playoff.DEFAULT_FORMAT["sites"]["rounds"],
            "championship": {"mode": "bowls", "bowl": "rose", "venue": "", "city": ""},
        },
    })
    bracket = playoff.build_bracket(_dynasty(), fmt)
    nc = bracket["rounds"][-1]["games"][0]
    assert nc["site"]["type"] == "championship"
    assert nc["site"]["bowl"]["key"] == "rose"
    # The Rose is now the title game, so it is not reused in an earlier round.
    earlier = [g["site"]["bowl"]["key"] for rnd in bracket["rounds"][:-1]
               for g in rnd["games"] if g["site"].get("bowl")]
    assert "rose" not in earlier


def test_champion_bowl_auto_picks_top_bowl():
    # Championship set to bowls with no specific bowl -> gets the top bowl.
    fmt = playoff.normalize_format({
        **playoff.DEFAULT_FORMAT,
        "sites": {
            "rounds": playoff.DEFAULT_FORMAT["sites"]["rounds"],
            "championship": {"mode": "bowls", "bowl": None, "venue": "", "city": ""},
        },
    })
    bracket = playoff.build_bracket(_dynasty(), fmt)
    nc = bracket["rounds"][-1]["games"][0]
    assert nc["site"]["bowl"]["key"] == "rose"


def test_bowls_never_repeat_across_rounds():
    fmt = _fmt(teams=16, byes=[], sites={
        "rounds": [{"mode": "bowls", "bowls": ["rose", "sugar"]},
                   {"mode": "bowls", "bowls": ["rose"]}],
        "championship": {"venue": "X", "city": "Y"},
    })
    bracket = playoff.build_bracket(_dynasty(), fmt)
    keys = [g["site"]["bowl"]["key"]
            for rnd in bracket["rounds"] for g in rnd["games"] if g["site"].get("bowl")]
    assert len(keys) == len(set(keys))


def test_neutral_round_site():
    fmt = _fmt(sites={
        "rounds": [{"mode": "neutral", "venue": "Wembley Stadium", "city": "London, UK"}],
        "championship": {"venue": "X", "city": "Y"},
    })
    bracket = playoff.build_bracket(_dynasty(), fmt)
    g = bracket["rounds"][0]["games"][0]
    assert g["site"]["type"] == "neutral" and g["site"]["venue"] == "Wembley Stadium"


def test_per_game_bowl_override():
    fmt = _fmt(sites={
        "rounds": [{"mode": "higher_seed", "games": [None, {"mode": "bowls", "bowl": "alamo"}]}],
        "championship": {"venue": "X", "city": "Y"},
    })
    bracket = playoff.build_bracket(_dynasty(), fmt)
    games = bracket["rounds"][0]["games"]
    assert games[0]["site"]["type"] == "campus"
    assert games[1]["site"]["bowl"]["key"] == "alamo"


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def test_format_store_roundtrip():
    assert not playoff.is_customized()
    saved = playoff.set_format(_fmt(teams=8, byes=[]))
    assert saved["teams"] == 8
    assert playoff.is_customized()
    assert playoff.get_format()["teams"] == 8
    playoff.reset_format()
    assert not playoff.is_customized()
    assert playoff.get_format()["teams"] == 12


def test_set_format_rejects_invalid():
    with pytest.raises(playoff.BracketError):
        playoff.set_format(_fmt(teams=6, byes=[]))


# ---------------------------------------------------------------------------
# Reseeding
# ---------------------------------------------------------------------------

def _finish(game, winner):
    game["status"] = "final"
    game["winner"] = winner
    game["scores"] = [30, 20]


def test_reseed_bracket_structure_and_first_round():
    bracket = playoff.build_bracket(_dynasty(), _fmt(reseed=True))
    assert bracket["format"]["reseed"] is True
    r1, qf, sf, ncg = bracket["rounds"]
    # opening round pairs its entrants best against worst, in order
    pairs = [tuple(s["seed"] for s in g["slots"]) for g in r1["games"]]
    assert pairs == [(5, 12), (6, 11), (7, 10), (8, 9)]
    # every later slot is a placeholder until the reseed resolves it
    for rnd in (qf, sf, ncg):
        for g in rnd["games"]:
            assert all(s["type"] == "reseed" for s in g["slots"])
    # bye seeds carry the round they enter
    entry = {s["seed"]: s.get("entry_round") for s in bracket["seeds"]}
    assert entry[1] == qf["round"] and entry[5] == r1["round"]


def test_reseed_fills_next_round_from_survivors():
    bracket = playoff.build_bracket(_dynasty(), _fmt(reseed=True))
    r1, qf, sf, _ = bracket["rounds"]
    # upsets: 12 beats 5, 11 beats 6; 7 and 8 hold serve
    for g, winner in zip(r1["games"], ("Team 12", "Team 11", "Team 07", "Team 08")):
        _finish(g, winner)
    assert playoff.fill_reseeded_rounds(bracket) is True
    # survivors 1,2,3,4 (byes) + 7,8,11,12 pair best against worst
    got = [tuple(s["team"] for s in g["slots"]) for g in qf["games"]]
    assert got == [("Team 01", "Team 12"), ("Team 02", "Team 11"),
                   ("Team 03", "Team 08"), ("Team 04", "Team 07")]
    # winners keep their feeder game for the bracket UI's connectors
    assert qf["games"][0]["slots"][1].get("game") == r1["games"][0]["id"]
    # bye entrants have none
    assert "game" not in qf["games"][0]["slots"][0]
    # idempotent: nothing new on a re-run
    assert playoff.fill_reseeded_rounds(bracket) is False
    # the semifinals stay placeholders until the quarterfinals finish
    assert all(s["type"] == "reseed" for g in sf["games"] for s in g["slots"])
    for g, winner in zip(qf["games"], ("Team 12", "Team 02", "Team 03", "Team 04")):
        _finish(g, winner)
    assert playoff.fill_reseeded_rounds(bracket) is True
    got = [tuple(s["team"] for s in g["slots"]) for g in sf["games"]]
    assert got == [("Team 02", "Team 12"), ("Team 03", "Team 04")]


def test_reseed_campus_site_follows_the_new_host():
    fmt = _fmt(reseed=True)
    fmt["sites"]["rounds"] = [{"mode": "higher_seed", "games": []},
                              {"mode": "higher_seed", "games": []}]
    bracket = playoff.build_bracket(_dynasty(), fmt)
    r1, qf = bracket["rounds"][0], bracket["rounds"][1]
    for g, winner in zip(r1["games"], ("Team 05", "Team 06", "Team 07", "Team 08")):
        _finish(g, winner)
    playoff.fill_reseeded_rounds(bracket)
    g0 = qf["games"][0]
    assert [s["team"] for s in g0["slots"]] == ["Team 01", "Team 08"]
    assert g0["site"]["type"] == "campus"
    assert g0["site"]["host_espn_id"] == 1000  # Team 01 hosts


def test_reseed_works_with_tiered_byes():
    # 24 teams, 8 single byes: R1 has 8 games (seeds 9..24), the next round's
    # entrants are the 8 winners + the 8 bye seeds, re-paired by seed.
    fmt = _fmt(teams=24, byes=[{"teams": 8, "rounds": 1}], reseed=True)
    bracket = playoff.build_bracket(_dynasty(), fmt)
    r1 = bracket["rounds"][0]
    pairs = [tuple(s["seed"] for s in g["slots"]) for g in r1["games"]]
    assert pairs == [(9, 24), (10, 23), (11, 22), (12, 21),
                     (13, 20), (14, 19), (15, 18), (16, 17)]
    for g in r1["games"]:
        _finish(g, g["slots"][1]["team"])  # every underdog wins
    playoff.fill_reseeded_rounds(bracket)
    r2 = bracket["rounds"][1]
    got = [tuple(s["team"] for s in g["slots"]) for g in r2["games"]]
    # survivors: byes 1..8 + winners 17..24 -> 1v24, 2v23, ...
    assert got == [("Team 01", "Team 24"), ("Team 02", "Team 23"),
                   ("Team 03", "Team 22"), ("Team 04", "Team 21"),
                   ("Team 05", "Team 20"), ("Team 06", "Team 19"),
                   ("Team 07", "Team 18"), ("Team 08", "Team 17")]


def test_reseed_never_disturbs_a_final_game():
    bracket = playoff.build_bracket(_dynasty(), _fmt(reseed=True))
    r1, qf = bracket["rounds"][0], bracket["rounds"][1]
    for g, winner in zip(r1["games"], ("Team 05", "Team 06", "Team 07", "Team 08")):
        _finish(g, winner)
    playoff.fill_reseeded_rounds(bracket)
    # the first quarterfinal is recorded; a later re-run must leave it alone
    _finish(qf["games"][0], "Team 01")
    before = [dict(s) for s in qf["games"][0]["slots"]]
    playoff.fill_reseeded_rounds(bracket)
    assert qf["games"][0]["slots"] == before


def test_reseed_normalizes_and_defaults_off():
    assert playoff.normalize_format({})["reseed"] is False
    assert playoff.normalize_format({"reseed": 1})["reseed"] is True
    bracket = playoff.build_bracket(_dynasty(), _fmt())
    assert playoff.fill_reseeded_rounds(bracket) is False  # off: no-op
