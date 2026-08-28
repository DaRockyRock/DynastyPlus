"""Bowl assignment rules independent of a particular binary save build."""
import pytest

from backend import bowl_editor


def _team(row, *, wins, rank, playoff=False):
    return {
        "row": row,
        "name": f"Team {row}",
        "wins": wins,
        "losses": max(0, 12 - wins),
        "rank": rank,
        "record": f"{wins}-{max(0, 12 - wins)}",
        "bowl_eligible": wins >= 6,
        "playoff": playoff,
    }


def _slot(record, *, ny6=False, away=None, home=None, official=False):
    return {
        "record": record,
        "name": f"Bowl {record}",
        "ny6": ny6,
        "away_row": away,
        "home_row": home,
        "official": official,
    }


def test_four_team_layout_fills_four_unused_ny6_and_every_other_bowl():
    # Four playoff teams are excluded by the catalog. Four remaining NY6
    # games take the best eight teams, then ordinary bowls receive everyone
    # else with no duplicate postseason appearance.
    teams = [_team(row, wins=12 - row // 5, rank=row,
                   playoff=row in {1, 2, 3, 4})
             for row in range(1, 21)]
    slots = [_slot(900 + i, ny6=True) for i in range(4)]
    slots += [_slot(400 + i) for i in range(4)]

    assignments = bowl_editor.automatic_assignments(slots, teams)

    assert len(assignments) == 8
    used = [row for item in assignments
            for row in (item["away_row"], item["home_row"])]
    assert len(used) == len(set(used)) == 16
    assert not ({1, 2, 3, 4} & set(used))
    assert set(used[:8]) == set(range(5, 13))
    bowl_editor._validate(assignments, slots, teams)


def test_auto_assignment_preserves_valid_native_bowl_pairings():
    teams = [_team(row, wins=9, rank=row) for row in range(1, 9)]
    slots = [
        _slot(928, ny6=True),
        _slot(390, away=3, home=4),
        _slot(391, away=5, home=6),
        _slot(392, away=7, home=8),
    ]

    assignments = bowl_editor.automatic_assignments(slots, teams)
    by_record = {item["record"]: item for item in assignments}

    assert (by_record[928]["away_row"], by_record[928]["home_row"]) == (1, 2)
    assert (by_record[390]["away_row"], by_record[390]["home_row"]) == (3, 4)
    assert (by_record[391]["away_row"], by_record[391]["home_row"]) == (5, 6)
    assert (by_record[392]["away_row"], by_record[392]["home_row"]) == (7, 8)


def test_large_playoff_activates_only_bowls_with_unique_teams_available():
    teams = [_team(row, wins=8, rank=row) for row in range(1, 11)]
    slots = [_slot(900, ny6=True), _slot(901, ny6=True)]
    slots += [_slot(390 + row) for row in range(8)]

    active, inactive = bowl_editor._fit_layout(slots, teams)

    assert len(active) == 5
    assert len(inactive) == 5
    assert [slot["record"] for slot in active[:2]] == [900, 901]
    assignments = bowl_editor.automatic_assignments(active, teams)
    assert len({row for item in assignments
                for row in (item["away_row"], item["home_row"])}) == 10


def test_manual_validation_rejects_duplicates_and_playoff_teams():
    teams = [_team(1, wins=11, rank=1, playoff=True),
             _team(2, wins=10, rank=2), _team(3, wins=9, rank=3),
             _team(4, wins=8, rank=4), _team(5, wins=7, rank=5)]
    slots = [_slot(390), _slot(391)]

    with pytest.raises(ValueError, match="playoff or unavailable"):
        bowl_editor._validate([
            {"record": 390, "away_row": 1, "home_row": 2},
            {"record": 391, "away_row": 3, "home_row": 4},
        ], slots, teams)

    with pytest.raises(ValueError, match="more than one postseason game"):
        bowl_editor._validate([
            {"record": 390, "away_row": 2, "home_row": 3},
            {"record": 391, "away_row": 2, "home_row": 4},
        ], slots, teams)


def test_official_bowl_matchup_is_immutable():
    teams = [_team(row, wins=8, rank=row) for row in range(1, 5)]
    slots = [_slot(390, away=1, home=2, official=True),
             _slot(391, away=3, home=4)]
    assignments = [
        {"record": 390, "away_row": 2, "home_row": 1},
        {"record": 391, "away_row": 3, "home_row": 4},
    ]

    with pytest.raises(ValueError, match="final and cannot be changed"):
        bowl_editor._validate(assignments, slots, teams)


def test_reserved_bowl_names_include_catalog_aliases():
    bracket = {
        "rounds": [{"games": [
            {"site": {"bowl": {"key": "rose", "name": "Rose Bowl"}}},
            {"site": {"bowl": {"key": "alamo", "name": "Alamo Bowl"}}},
        ]}],
    }
    reserved = bowl_editor._reserved_bowl_names(bracket)
    assert "rosebowl" in reserved
    assert "alamobowl" in reserved
