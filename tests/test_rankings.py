"""Tests for the ranking algorithms (`backend.rankings`)."""
import math

import pytest

from backend import rankings as rk

G = rk.GameResult


def _rr_games(n=6):
    """Round robin where lower row always beats higher row, decisively."""
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            out.append(G(home=i, away=j, home_score=28 + (n - i), away_score=10 + j))
    return out


# ---------------------------------------------------------------------------
# Colley: verified against the worked example in Colley's own method paper
# (matrate.pdf eq. 24): 5 teams, 7 games, solution r = {19,24,23,22,27}/46.
# ---------------------------------------------------------------------------

def test_colley_paper_example():
    games = [
        G(home=0, away=3, home_score=21, away_score=10),   # 0 beats 3
        G(home=2, away=0, home_score=17, away_score=14),   # 2 beats 0
        G(home=4, away=0, home_score=28, away_score=7),    # 4 beats 0
        G(home=1, away=2, home_score=24, away_score=20),   # 1 beats 2
        G(home=4, away=1, home_score=31, away_score=13),   # 4 beats 1
        G(home=3, away=2, home_score=10, away_score=9),    # 3 beats 2
        G(home=2, away=4, home_score=35, away_score=34),   # 2 beats 4
    ]
    teams = [0, 1, 2, 3, 4]
    r = rk._colley(games, teams, {})
    want = {0: 19 / 46, 1: 24 / 46, 2: 23 / 46, 3: 22 / 46, 4: 27 / 46}
    for t in teams:
        assert r[t] == pytest.approx(want[t], abs=1e-9)
    order = rk.compute("colley", games, prior=[0, 1, 2, 3, 4])
    assert order == [4, 1, 2, 3, 0]


def test_colley_mean_is_half():
    games = _rr_games(6)
    r = rk._colley(games, list(range(6)), {})
    assert sum(r.values()) / 6 == pytest.approx(0.5, abs=1e-9)


# ---------------------------------------------------------------------------
# every algorithm: basic sanity on a decisive round robin
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algo", sorted(rk.ALGORITHMS))
def test_round_robin_order(algo):
    games = _rr_games(6)
    # a deliberately reversed prior must be overruled by the results
    assert rk.compute(algo, games, prior=[5, 4, 3, 2, 1, 0]) == [0, 1, 2, 3, 4, 5]


@pytest.mark.parametrize("algo", sorted(rk.ALGORITHMS))
def test_no_games_returns_prior(algo):
    prior = [3, 1, 2]
    assert rk.compute(algo, [], prior) == prior
    assert rk.compute(algo, _rr_games(4), []) == []


def test_unknown_algorithm_rejected():
    with pytest.raises(ValueError):
        rk.compute("magic", _rr_games(4), [0, 1, 2, 3])


def test_prior_breaks_exact_ties():
    # one game between 0 and 1; teams 2 and 3 idle -> identical ratings,
    # ordered by the prior
    games = [G(home=0, away=1, home_score=21, away_score=7)]
    assert rk.compute("colley", games, prior=[0, 1, 3, 2]) == [0, 3, 2, 1]
    assert rk.compute("colley", games, prior=[0, 1, 2, 3]) == [0, 2, 3, 1]


def test_outside_prior_teams_are_rated_but_filtered():
    # team 9 (an FCS placeholder outside the poll) beats team 1; the loss must
    # hurt team 1, and team 9 must not appear in the output
    games = [
        G(home=0, away=1, home_score=21, away_score=20),
        G(home=9, away=1, home_score=30, away_score=10),
        G(home=0, away=2, home_score=10, away_score=13),
        G(home=2, away=9, home_score=20, away_score=10),
    ]
    order = rk.compute("colley", games, prior=[0, 1, 2])
    assert 9 not in order
    assert set(order) == {0, 1, 2}
    assert order.index(1) == 2  # two losses incl. the out-of-poll one


# ---------------------------------------------------------------------------
# algorithm-specific behavior
# ---------------------------------------------------------------------------

def test_massey_handles_disconnected_islands():
    # two islands that never meet: the anchored system must still solve, and
    # each island's internal order must hold
    games = [
        G(home=0, away=1, home_score=35, away_score=7),
        G(home=2, away=3, home_score=21, away_score=20),
    ]
    order = rk.compute("massey", games, prior=[0, 1, 2, 3])
    assert order.index(0) < order.index(1)
    assert order.index(2) < order.index(3)


def test_massey_margin_cap():
    r_raw = rk._massey([G(0, 1, 70, 0)], [0, 1], {})
    r_cap = rk._massey([G(0, 1, 70, 0)], [0, 1], {"margin_cap": 24})
    assert r_raw[0] > r_cap[0] > 0


def test_elo_zero_sum_and_home_advantage():
    teams = [0, 1]
    params = {"_prior_index": {0: 0, 1: 1}, "seed_spread": 0.0}
    # a home win moves fewer points than the same win on the road
    home = rk._elo([G(home=0, away=1, home_score=21, away_score=14)], teams, dict(params))
    road = rk._elo([G(home=1, away=0, home_score=14, away_score=21)], teams, dict(params))
    assert home[0] + home[1] == pytest.approx(3000.0)
    assert home[0] - 1500.0 > 0
    assert (road[0] - 1500.0) > (home[0] - 1500.0)
    neutral = rk._elo([G(home=0, away=1, home_score=21, away_score=14, neutral=True)],
                      teams, dict(params))
    assert home[0] < neutral[0] < road[0]


def test_elo_blowout_credit_fades_for_favorites():
    # same 28-point win: a heavy favorite must gain less than an underdog
    # (seeded from the prior: team 0 starts at 1700, team 1 at 1300)
    prior = {0: 0, 1: 1}
    params = {"_prior_index": prior, "seed_spread": 400.0}
    fav_win = rk._elo([G(home=0, away=1, home_score=42, away_score=14,
                         neutral=True)], [0, 1], dict(params))
    dog_win = rk._elo([G(home=1, away=0, home_score=42, away_score=14,
                         neutral=True)], [0, 1], dict(params))
    gain_fav = fav_win[0] - 1700.0
    gain_dog = dog_win[1] - 1300.0
    assert gain_fav > 0 and gain_dog > 0
    assert gain_dog > gain_fav


def test_srs_cap_and_floor():
    # Sports-Reference CFB rules: a 1-point win counts as 7, a 70-point win as 24
    close = rk._srs([G(0, 1, 21, 20)], [0, 1], {})
    blowout = rk._srs([G(0, 1, 70, 0)], [0, 1], {})
    assert close[0] == pytest.approx(3.5)     # +7 margin, mean-centered
    assert blowout[0] == pytest.approx(12.0)  # +24 margin, mean-centered
    assert sum(close.values()) == pytest.approx(0.0, abs=1e-9)


def test_rpi_weights():
    # 0 beats 1, 1 beats 2: by hand,
    #   WP:  0 -> 1, 1 -> 1/2, 2 -> 0
    #   OWP (excluding games vs self): 0 -> 1's WP w/o games vs 0 = 1
    #                                  1 -> (0: no other games -> 0) and (2: 0) = 0
    #                                  2 -> 1's WP w/o games vs 2 = 0
    #   OOWP: 0 -> OWP(1) = 0; 1 -> (OWP(0)+OWP(2))/2 = 0.5; 2 -> OWP(1) = 0
    games = [G(0, 1, 21, 7), G(1, 2, 21, 7)]
    r = rk._rpi(games, [0, 1, 2], {})
    assert r[0] == pytest.approx(0.25 * 1.0 + 0.50 * 1.0 + 0.25 * 0.0)
    assert r[1] == pytest.approx(0.25 * 0.5 + 0.50 * 0.0 + 0.25 * 0.5)
    assert r[2] == pytest.approx(0.25 * 0.0 + 0.50 * 0.0 + 0.25 * 0.0)


def test_bradley_terry_undefeated_stays_finite():
    games = [G(0, 1, 30, 0), G(0, 2, 30, 0), G(1, 2, 20, 10)]
    r = rk._bradley_terry(games, [0, 1, 2], {})
    assert all(math.isfinite(v) for v in r.values())
    assert r[0] > r[1] > r[2]


def test_pagerank_winner_over_loser():
    games = [G(0, 1, 35, 3)]
    r = rk._pagerank(games, [0, 1], {})
    assert r[0] > r[1]
    assert sum(r.values()) == pytest.approx(1.0, abs=1e-6)


def test_pagerank_blowout_beats_squeaker():
    # 0 and 2 both beat 1; 0 crushed it, 2 squeaked by, otherwise identical
    games = [G(0, 1, 45, 3), G(2, 1, 21, 20)]
    r = rk._pagerank(games, [0, 1, 2], {})
    assert r[0] > r[2] > r[1]


def test_bcs_blends_human_poll_and_computers():
    # computers alone would order the round robin 0..5; a human poll that
    # loves team 5 (worst on the field) must drag it up, since the human vote
    # is two-thirds of the BCS
    games = _rr_games(6)
    human = [5, 4, 3, 2, 1, 0]  # exact reverse of the computer order
    order = rk.compute("bcs", games, prior=[0, 1, 2, 3, 4, 5],
                       params={"human_orders": [human]})
    # team 0 (computer #1, human last) vs team 5 (computer last, human #1):
    # the 2/3 human weight pulls 5 well up from the bottom
    assert order.index(5) < 5
    # and a team the humans rank #1 outranks one they rank low, all else equal
    assert order.index(5) < order.index(4) or order.index(0) > 0


def test_bcs_without_human_poll_is_computer_only():
    games = _rr_games(6)
    with_none = rk.compute("bcs", games, prior=[0, 1, 2, 3, 4, 5],
                           params={"human_orders": []})
    assert with_none == [0, 1, 2, 3, 4, 5]


def test_bcs_human_poll_breaks_a_symmetric_swap():
    # computers rank 0 over 1; the humans swap exactly those two. Because the
    # human vote is 2/3 to the computers' 1/3, the human #1 (team 1) wins the
    # symmetric swap and takes the top line.
    games = _rr_games(6)
    human = [1, 0, 2, 3, 4, 5]
    order = rk.compute("bcs", games, prior=[0, 1, 2, 3, 4, 5],
                       params={"human_orders": [human]})
    assert order[0] == 1
    assert order[1] == 0


def test_ties_do_not_crash_and_count_as_half():
    games = [G(0, 1, 21, 21), G(0, 2, 28, 7)]
    order = rk.compute("colley", games, prior=[0, 1, 2])
    assert order[0] == 0
    r = rk._massey(games, [0, 1, 2], {})
    assert r[0] > r[2]
