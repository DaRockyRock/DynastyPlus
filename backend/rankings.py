"""College football computer ranking algorithms over the save's own results.

The poll editor (backend/polledit.py) lets the user hand a poll to a computer:
every algorithm here turns the season's OFFICIAL results into a full ordering
of the save's ranked teams. These are faithful implementations of the classic
CFB rating systems (several were real BCS computer ratings):

  colley         Colley Matrix (Wes Colley's bias-free method): wins/losses
                 only, schedule-adjusted through a linear system. A BCS
                 computer rating.
  massey         Massey least-squares ratings on point differential, with the
                 sum-to-zero constraint replacing the last equation.
  elo            Sequential Elo in the FiveThirtyEight style: home advantage,
                 margin-of-victory multiplier with the autocorrelation
                 correction, ratings seeded from the current poll (the
                 preseason prior).
  srs            Simple Rating System (Sports-Reference style): rating =
                 average capped margin + average opponent rating, iterated.
  rpi            Rating Percentage Index: 25% WP + 50% OWP + 25% OOWP
                 (opponent win % excludes games against the team itself).
  bradley_terry  Bradley-Terry maximum-likelihood ratings via the classic MM
                 iteration, regularized with one fictitious win and loss
                 against an average team so undefeated seasons stay finite.
  pagerank       Markov chain / PageRank ranking (the "GeM" eigenvector
                 method): every team votes for the teams that beat or
                 outscored it; the Perron vector ranks the field.
  composite      BCS-style computer average: each team's rank across the six
                 rating systems above, best and worst dropped, averaged.

All functions are pure Python (no numpy; a ~140-team dense solve is trivial)
and deterministic: every sort is tie-broken by the PRIOR order (the poll as
the save currently has it), so identical records early in the season fall
back to the game's own ordering instead of jumping around, and a season with
no official results yet returns the prior untouched.

Teams that appear in results but are not in the rated set (FCS placeholder
rows the save leaves unranked) are rated internally, so games against them
still count, but they never appear in the returned order.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class GameResult:
    """One official result. Team ids are save team rows, but any hashable id
    works (the tests use small ints)."""
    home: int
    away: int
    home_score: int
    away_score: int
    neutral: bool = False

    @property
    def winner(self) -> int | None:
        if self.home_score == self.away_score:
            return None
        return self.home if self.home_score > self.away_score else self.away

    @property
    def loser(self) -> int | None:
        w = self.winner
        if w is None:
            return None
        return self.away if w == self.home else self.home


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def _participants(games: list[GameResult], rated: list[int]) -> list[int]:
    """Every team the system rates: the rated set plus every opponent that
    appears in a result (stable order: rated first, then first appearance)."""
    seen = dict.fromkeys(rated)
    for g in games:
        seen.setdefault(g.home)
        seen.setdefault(g.away)
    return list(seen)


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting. The Colley and Massey
    systems are small (~145 unknowns), diagonally dominant (Colley strictly
    so), and well-conditioned, so a dense direct solve is exact enough."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            raise ValueError("singular rating system")
        m[col], m[piv] = m[piv], m[col]
        pivval = m[col][col]
        for r in range(col + 1, n):
            f = m[r][col] / pivval
            if f == 0.0:
                continue
            for c in range(col, n + 1):
                m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))
        x[r] = s / m[r][r]
    return x


def _order_by_rating(rating: dict[int, float], rated: list[int],
                     prior_index: dict[int, int]) -> list[int]:
    """Rated teams best-first; exact ties fall back to the prior order."""
    return sorted(rated, key=lambda t: (-rating.get(t, 0.0),
                                        prior_index.get(t, 1 << 30)))


def _margin(g: GameResult, cap: int | None) -> int:
    m = abs(g.home_score - g.away_score)
    return min(m, cap) if cap else m


# ---------------------------------------------------------------------------
# the algorithms (each returns {team: rating}, higher = better)
# ---------------------------------------------------------------------------

def _colley(games: list[GameResult], teams: list[int],
             params: dict[str, Any]) -> dict[int, float]:
    """Colley Matrix: solve C r = b with C_ii = 2 + n_i, C_ij = -(games i vs
    j), b_i = 1 + (w_i - l_i)/2. Margins and venue never enter; every rating
    starts from the same 1/2 (Laplace's rule of succession), so the system is
    bias-free and early-season ratings shade gently away from 0.5."""
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    c = [[0.0] * n for _ in range(n)]
    b = [1.0] * n
    for i in range(n):
        c[i][i] = 2.0
    for g in games:
        hi, ai = idx[g.home], idx[g.away]
        # every game (a tie included) counts in the matrix; only a decision
        # moves b (the standard tie extension: half-win, half-loss)
        c[hi][hi] += 1.0
        c[ai][ai] += 1.0
        c[hi][ai] -= 1.0
        c[ai][hi] -= 1.0
        w, l = g.winner, g.loser
        if w is None:
            continue
        b[idx[w]] += 0.5
        b[idx[l]] -= 0.5
    r = _solve(c, b)
    return {t: r[idx[t]] for t in teams}


def _massey(games: list[GameResult], teams: list[int],
            params: dict[str, Any]) -> dict[int, float]:
    """Massey least squares: M r = p with M_ii = n_i, M_ij = -(games i vs j),
    p_i = total (capped) point differential.

    Massey's own fix for the singular M (replace the last equation with
    sum(r) = 0) assumes a CONNECTED schedule graph; early in a real season
    the graph is many islands and the system stays singular. Instead every
    team is anchored with one virtual TIE against a fixed average opponent
    (diagonal + 1, differential + 0): the classic dummy-game regularization.
    It makes the system positive definite in any season shape, pins no-data
    teams at 0, and washes out as real games accumulate. Ratings are
    mean-centered afterward, matching Massey's normalization."""
    cap = params.get("margin_cap")
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    m = [[0.0] * n for _ in range(n)]
    p = [0.0] * n
    for i in range(n):
        m[i][i] = 1.0  # the virtual tie vs the average team
    for g in games:
        hi, ai = idx[g.home], idx[g.away]
        d = _margin(g, cap)
        if g.home_score < g.away_score:
            d = -d
        m[hi][hi] += 1.0
        m[ai][ai] += 1.0
        m[hi][ai] -= 1.0
        m[ai][hi] -= 1.0
        p[hi] += d
        p[ai] -= d
    r = _solve(m, p)
    mean = sum(r) / n
    return {t: r[idx[t]] - mean for t in teams}


def _elo(games: list[GameResult], teams: list[int],
         params: dict[str, Any]) -> dict[int, float]:
    """Sequential Elo, FiveThirtyEight style. Ratings are seeded from the
    prior order (the save's current poll standing in for a preseason rating),
    then every game moves points between the two teams:

        expected = 1 / (1 + 10^(-(elo_w - elo_l) / 400))
        mov mult = ln(|margin| + 1) * 2.2 / (0.001 * (elo_w - elo_l) + 2.2)
        delta    = K * mov_mult * (1 - expected)

    with the home side getting `hfa` Elo before the expectation (skipped on
    neutral fields). The 2.2/(...) term is 538's autocorrelation fix so
    strong favorites cannot farm blowout points."""
    k = float(params.get("k", 30.0))
    hfa = float(params.get("hfa", 55.0))
    spread = float(params.get("seed_spread", 200.0))
    prior_index: dict[int, int] = params["_prior_index"]
    ranked_n = max(len([t for t in teams if t in prior_index]), 2)
    elo: dict[int, float] = {}
    for t in teams:
        pi = prior_index.get(t)
        if pi is None or spread <= 0:
            elo[t] = 1500.0
        else:
            elo[t] = 1500.0 + spread * (0.5 - pi / (ranked_n - 1))
    for g in games:
        w = g.winner
        if w is None:
            continue
        home_edge = 0.0 if g.neutral else hfa
        eh = elo[g.home] + home_edge
        ea = elo[g.away]
        exp_home = 1.0 / (1.0 + 10.0 ** (-(eh - ea) / 400.0))
        margin = abs(g.home_score - g.away_score)
        diff_w = (eh - ea) if w == g.home else (ea - eh)
        mult = math.log(margin + 1.0) * (2.2 / (0.001 * diff_w + 2.2))
        s_home = 1.0 if w == g.home else 0.0
        delta = k * mult * (s_home - exp_home)
        elo[g.home] += delta
        elo[g.away] -= delta
    return elo


def _srs(games: list[GameResult], teams: list[int],
         params: dict[str, Any]) -> dict[int, float]:
    """Simple Rating System, Sports-Reference CFB rules: rating = average
    point margin + average opponent rating, iterated to a fixed point.
    Margins are capped at 24 (a blowout is a decisive win, not a style
    score) and floored at 7 (a 1-point win counts like a 7-point win),
    both applied to losses symmetrically, no home-field element. Ratings
    are re-centered to mean 0 every pass (with unequal game counts the
    plain iteration's mean drifts) and read as points vs an average team."""
    cap = params.get("margin_cap", 24)
    floor = params.get("margin_floor", 7)
    played: dict[int, list[tuple[int, float]]] = {t: [] for t in teams}
    for g in games:
        d = float(_margin(g, cap))
        if d and floor:
            d = max(d, float(floor))
        if g.home_score < g.away_score:
            d = -d
        played[g.home].append((g.away, d))
        played[g.away].append((g.home, -d))
    mov = {t: (sum(d for _, d in gs) / len(gs) if gs else 0.0)
           for t, gs in played.items()}
    r = dict(mov)
    for _ in range(500):
        biggest = 0.0
        nxt = {}
        for t, gs in played.items():
            if not gs:
                nxt[t] = 0.0
                continue
            sos = sum(r[o] for o, _ in gs) / len(gs)
            # damp the Jacobi step: the plain iteration oscillates forever on
            # (near-)bipartite schedule graphs (two teams that only played
            # each other being the textbook case)
            nxt[t] = (mov[t] + sos + r[t]) / 2.0
            biggest = max(biggest, abs(nxt[t] - r[t]))
        mean = sum(nxt.values()) / max(len(nxt), 1)
        r = {t: v - mean for t, v in nxt.items()}
        if biggest < 1e-9:
            break
    return r


def _rpi(games: list[GameResult], teams: list[int],
         params: dict[str, Any]) -> dict[int, float]:
    """RPI: 0.25 * WP + 0.50 * OWP + 0.25 * OOWP. A team's opponents' winning
    percentage excludes their games against the team itself (the NCAA rule),
    so beating someone never pads their contribution to your schedule."""
    opps: dict[int, list[int]] = {t: [] for t in teams}
    wins: dict[int, dict[int, float]] = {t: {} for t in teams}   # vs-opponent wins
    counts: dict[int, dict[int, int]] = {t: {} for t in teams}   # vs-opponent games
    for g in games:
        w = g.winner
        if w is None:
            continue
        for me, opp in ((g.home, g.away), (g.away, g.home)):
            opps[me].append(opp)
            counts[me][opp] = counts[me].get(opp, 0) + 1
            wins[me].setdefault(opp, 0.0)
            if w == me:
                wins[me][opp] += 1.0

    def wp(t: int, excluding: int | None = None) -> float:
        wsum = sum(v for o, v in wins[t].items() if o != excluding)
        n = sum(v for o, v in counts[t].items() if o != excluding)
        return wsum / n if n else 0.0

    def owp(t: int) -> float:
        if not opps[t]:
            return 0.0
        return sum(wp(o, excluding=t) for o in opps[t]) / len(opps[t])

    owp_cache = {t: owp(t) for t in teams}

    def oowp(t: int) -> float:
        if not opps[t]:
            return 0.0
        return sum(owp_cache[o] for o in opps[t]) / len(opps[t])

    return {t: 0.25 * wp(t) + 0.50 * owp_cache[t] + 0.25 * oowp(t)
            for t in teams}


def _bradley_terry(games: list[GameResult], teams: list[int],
                   params: dict[str, Any]) -> dict[int, float]:
    """Bradley-Terry maximum likelihood via the classic MM update

        r_i <- w_i / sum_j n_ij / (r_i + r_j)

    regularized with one fictitious win AND loss against a fixed average team
    (rating 1), the standard fix that keeps undefeated and winless teams at
    finite ratings (Mease 2003's penalized MLE and the KRACH 'fictitious
    tie'; Ford's connectivity condition fails on real early-season
    schedules). Ratings are normalized to geometric mean 1 each pass."""
    wins = {t: 0.0 for t in teams}
    pairs: dict[int, dict[int, int]] = {t: {} for t in teams}
    for g in games:
        w, l = g.winner, g.loser
        if w is None:
            continue
        wins[w] += 1.0
        pairs[g.home][g.away] = pairs[g.home].get(g.away, 0) + 1
        pairs[g.away][g.home] = pairs[g.away].get(g.home, 0) + 1
    r = {t: 1.0 for t in teams}
    for _ in range(300):
        biggest = 0.0
        nxt = {}
        for t in teams:
            denom = 2.0 / (r[t] + 1.0)  # the fictitious win + loss vs rating 1
            for o, n in pairs[t].items():
                denom += n / (r[t] + r[o])
            nxt[t] = (wins[t] + 1.0) / denom
        gm = math.exp(sum(math.log(max(v, 1e-12)) for v in nxt.values())
                      / max(len(nxt), 1))
        for t in teams:
            nxt[t] /= gm
            biggest = max(biggest, abs(nxt[t] - r[t]))
        r = nxt
        if biggest < 1e-10:
            break
    return {t: math.log(max(v, 1e-12)) for t, v in r.items()}


def _pagerank(games: list[GameResult], teams: list[int],
              params: dict[str, Any]) -> dict[int, float]:
    """Markov chain ranking, the GeM method (Govan & Meyer's PageRank over
    the season graph): every loss is a directed vote from the loser to the
    winner, weighted by the margin of defeat, so a fan drifting through the
    season keeps abandoning teams for the teams that beat them. Undefeated
    (and idle) teams are dangling nodes and vote uniformly, the standard
    PageRank fix. The stationary distribution of the damped chain is the
    rating; sports data wants a much lower damping than the web's 0.85
    (Govan found ~0.6 best for football), so 0.6 is the default."""
    damping = float(params.get("damping", 0.6))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    votes = [[0.0] * n for _ in range(n)]  # votes[j][i]: j's vote for i
    for g in games:
        w, l = g.winner, g.loser
        if w is None:
            continue
        votes[idx[l]][idx[w]] += float(abs(g.home_score - g.away_score))
    rank = [1.0 / n] * n
    for _ in range(200):
        nxt = [(1.0 - damping) / n] * n
        for j in range(n):
            total = sum(votes[j])
            if total <= 0:
                for i in range(n):      # dangling (unbeaten/idle): uniform
                    nxt[i] += damping * rank[j] / n
                continue
            for i in range(n):
                if votes[j][i]:
                    nxt[i] += damping * rank[j] * votes[j][i] / total
        if max(abs(nxt[i] - rank[i]) for i in range(n)) < 1e-12:
            rank = nxt
            break
        rank = nxt
    return {t: rank[idx[t]] for t in teams}


_RATERS: dict[str, Callable[[list[GameResult], list[int], dict[str, Any]],
                            dict[int, float]]] = {
    "colley": _colley,
    "massey": _massey,
    "elo": _elo,
    "srs": _srs,
    "rpi": _rpi,
    "bradley_terry": _bradley_terry,
    "pagerank": _pagerank,
}


# ---------------------------------------------------------------------------
# public registry + entry point
# ---------------------------------------------------------------------------

# id -> UI metadata. `uses` is display flavor for the picker so the user can
# see at a glance what each system counts.
ALGORITHMS: dict[str, dict[str, str]] = {
    "bcs": {
        "name": "BCS Formula",
        "blurb": "The Bowl Championship Series formula: two-thirds the human "
                 "poll (the game's other poll stands in for the Harris and "
                 "coaches polls) and one-third the computer average (the six "
                 "computer ratings below, each team's best and worst dropped).",
        "uses": "Human poll + computers",
    },
    "colley": {
        "name": "Colley Matrix",
        "blurb": "Wins and losses only, adjusted for schedule strength "
                 "through a linear system. Bias-free: no margins, no "
                 "preseason opinion. A real BCS computer rating.",
        "uses": "W/L, schedule",
    },
    "massey": {
        "name": "Massey Ratings",
        "blurb": "Least-squares ratings on point differential: every score "
                 "is a statement about the two teams' difference, solved "
                 "across the whole season at once.",
        "uses": "Margins, schedule",
    },
    "elo": {
        "name": "Elo",
        "blurb": "Game-by-game ratings in the FiveThirtyEight style: home "
                 "advantage, a margin-of-victory boost that fades for heavy "
                 "favorites, seeded from the current poll as the preseason "
                 "prior.",
        "uses": "Margins, venue, momentum",
    },
    "srs": {
        "name": "Simple Rating System",
        "blurb": "Average scoring margin (capped, so blowouts stop counting "
                 "past a point) plus average opponent rating, iterated until "
                 "stable. The Sports-Reference standard.",
        "uses": "Capped margins, schedule",
    },
    "rpi": {
        "name": "RPI",
        "blurb": "The committee-era Rating Percentage Index: 25% your record, "
                 "50% your opponents' record, 25% their opponents' record.",
        "uses": "W/L, schedule only",
    },
    "bradley_terry": {
        "name": "Bradley-Terry (MLE)",
        "blurb": "Maximum-likelihood ratings where every result is evidence: "
                 "the odds you beat a team are your rating against theirs. "
                 "Margins never enter, quality of wins is everything.",
        "uses": "W/L, opponent quality",
    },
    "pagerank": {
        "name": "PageRank (Markov)",
        "blurb": "Google's eigenvector trick on the season graph: every team "
                 "votes for the teams that beat or outscored it, and the "
                 "steady state ranks the field.",
        "uses": "Scores, season graph",
    },
    "composite": {
        "name": "Computer Composite",
        "blurb": "BCS-style average of the six computer ratings above with "
                 "each team's best and worst rank dropped, like the old BCS "
                 "computer component.",
        "uses": "All of the above",
    },
}

_COMPOSITE_MEMBERS = ["colley", "massey", "elo", "srs", "bradley_terry",
                      "pagerank"]


def _order_points(order: list[int], prior: list[int]) -> dict[int, float]:
    """BCS-style points for a poll ordering over the rated field: the best
    listed team gets len(prior) points, the next one fewer, and so on; a team
    the ordering omits gets 0 (it was unranked in that poll)."""
    n = len(prior)
    pts = {t: 0.0 for t in prior}
    p = 0
    for t in order:
        if t in pts:
            pts[t] = float(n - p)
            p += 1
    return pts


def _bcs(games: list[GameResult], prior: list[int],
         prior_index: dict[int, int], params: dict[str, Any]) -> list[int]:
    """The Bowl Championship Series formula (2004-2013 shape): each component
    is scored as a percentage of the maximum points, then

        BCS = (human polls) * 2/3 + (computer average) * 1/3

    The computer third is the six ratings' points with each team's single
    best and single worst dropped, averaged (the BCS's own drop-high-drop-low
    over its six computers). The human two-thirds is the save's OTHER poll(s)
    standing in for the Harris and coaches polls (passed as `human_orders`);
    reading the other poll, not the one being written, keeps the weekly
    re-apply from feeding a poll its own last output. With no human poll
    available the score falls back to the computer average alone."""
    field = _participants(games, list(prior))
    n = len(prior)

    per_team: dict[int, list[float]] = {t: [] for t in prior}
    for member in _COMPOSITE_MEMBERS:
        rating = _RATERS[member](games, field, params)
        pts = _order_points(_order_by_rating(rating, list(prior), prior_index), prior)
        for t in prior:
            per_team[t].append(pts[t])
    computer_pct: dict[int, float] = {}
    for t in prior:
        vals = sorted(per_team[t])
        trimmed = vals[1:-1] if len(vals) > 2 else vals
        computer_pct[t] = (sum(trimmed) / len(trimmed)) / n if n else 0.0

    human_orders = [o for o in (params.get("human_orders") or []) if o]
    if human_orders:
        human_pct = {t: 0.0 for t in prior}
        for order in human_orders:
            pts = _order_points(order, prior)
            for t in prior:
                human_pct[t] += (pts[t] / n) / len(human_orders)
        w_human, w_comp = 2.0 / 3.0, 1.0 / 3.0
    else:
        human_pct = {t: 0.0 for t in prior}
        w_human, w_comp = 0.0, 1.0

    score = {t: w_human * human_pct[t] + w_comp * computer_pct[t] for t in prior}
    return _order_by_rating(score, list(prior), prior_index)


def compute(algorithm: str, games: list[GameResult], prior: list[int],
            params: dict[str, Any] | None = None) -> list[int]:
    """Rank `prior`'s teams by `algorithm` over the official results.

    prior: the rated teams in the save's CURRENT poll order, best first. It
    defines exactly which teams come back (opponents outside it are rated
    internally but filtered out) and breaks every exact tie, so early-season
    output degrades toward the game's own ordering instead of shuffling.
    Returns the same teams, best first."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown ranking algorithm: {algorithm!r}")
    if not prior:
        return []
    if not games:
        return list(prior)
    params = dict(params or {})
    prior_index = {t: i for i, t in enumerate(prior)}
    params["_prior_index"] = prior_index
    teams = _participants(games, list(prior))

    if algorithm == "composite":
        ranks: dict[int, list[int]] = {t: [] for t in prior}
        for member in _COMPOSITE_MEMBERS:
            rating = _RATERS[member](games, teams, params)
            order = _order_by_rating(rating, list(prior), prior_index)
            for pos, t in enumerate(order):
                ranks[t].append(pos + 1)
        score: dict[int, float] = {}
        for t, rs in ranks.items():
            rs = sorted(rs)
            trimmed = rs[1:-1] if len(rs) > 2 else rs
            score[t] = -sum(trimmed) / len(trimmed)
        return _order_by_rating(score, list(prior), prior_index)

    if algorithm == "bcs":
        return _bcs(games, list(prior), prior_index, params)

    rating = _RATERS[algorithm](games, teams, params)
    return _order_by_rating(rating, list(prior), prior_index)
