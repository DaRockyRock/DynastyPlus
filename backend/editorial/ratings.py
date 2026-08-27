"""The expectation model: Elo-style power ratings, win probability, surprisal.

"Newsworthy" needs "expected" to push against. This store gives every team a
rating (seeded from the save's coach prestige + the preseason poll, updated each
week from finals with a margin-of-victory multiplier per the FiveThirtyEight
formulation), converts matchups to win probabilities, and measures results in
bits of surprisal (-log2 p). When the sim publishes a Vegas line for a game, the
line IS the universe's own expectation, so it takes precedence over Elo for that
game's pre-game probability.

Persisted per dynasty+year under the editorial store; updates are idempotent
(processed games are keyed, re-running a week is a no-op).
"""
from __future__ import annotations

import json
import math
import re
import threading
from typing import Any

from .. import dynasty_paths

_lock = threading.Lock()

ELO_BASE = 1500.0
HFA_ELO = 55.0          # home-field bonus, Elo points
K = 20.0
SPREAD_SIGMA = 13.5     # CFB margin stddev; spread -> win prob via normal CDF
ELO_PER_POINT = 25.0    # rough Elo-points-per-spread-point conversion


def _path(year: int):
    return dynasty_paths.sub("editorial") / f"{year}_ratings.json"


def _empty(year: int) -> dict[str, Any]:
    return {"year": year, "teams": {}, "games": {}, "user": {}}


def _read(year: int) -> dict[str, Any]:
    p = _path(year)
    if not p.exists():
        return _empty(year)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("teams"), dict):
            return _empty(year)
        return data
    except (OSError, ValueError):
        return _empty(year)


def _write(year: int, data: dict[str, Any]) -> None:
    try:
        _path(year).write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass


# --- probabilities ----------------------------------------------------------
def win_prob(elo_a: float, elo_b: float, *, a_home: bool = False, b_home: bool = False) -> float:
    """P(team A beats team B) from Elo, with the home bonus applied pre-diff."""
    diff = elo_a - elo_b + (HFA_ELO if a_home else 0.0) - (HFA_ELO if b_home else 0.0)
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


def spread_prob(spread: float) -> float:
    """P(favorite wins) from a point spread via the normal CDF (sigma ~= 13.5)."""
    return 0.5 * (1.0 + math.erf((spread / SPREAD_SIGMA) / math.sqrt(2.0)))


def surprisal(p: float) -> float:
    """Bits of surprise for an outcome that had probability p."""
    return -math.log2(max(min(p, 1.0 - 1e-9), 1e-9))


_LINE_RE = re.compile(r"([A-Z&]{2,6})\s*([+-]\d+(?:\.\d+)?)")


def parse_line(line: str | None) -> tuple[str, float] | None:
    """'UGA -34.5' -> ('UGA', 34.5): the favorite's abbr and the spread."""
    if not line:
        return None
    m = _LINE_RE.search(str(line))
    if not m:
        return None
    pts = float(m.group(2))
    return (m.group(1), -pts) if pts < 0 else None  # only favorites carry minus


# --- seeding ----------------------------------------------------------------
def _seed_elo(prestige: int, ap_rank: int | None) -> float:
    """Initial rating from the save's own signals: prestige (1-10) sets the
    class of program, a preseason poll slot adds current-strength sheen."""
    elo = 1300.0 + float(prestige or 5) * 40.0
    if ap_rank:
        elo += max(0.0, (26 - ap_rank)) * 3.0
    return elo


def ensure(year: int, dynasty: dict) -> dict[str, Any]:
    """Load the store, seeding every team on first touch from the coach directory
    (prestige) and the preseason AP poll. Also seeds the user's projected wins by
    summing pre-game win probabilities over the full schedule."""
    with _lock:
        data = _read(year)
        if data["teams"]:
            return data
        ap = {r.get("team"): r.get("rank") for r in ((dynasty.get("national") or {}).get("ap_top25") or [])}
        for team, c in (dynasty.get("coaches") or {}).items():
            if isinstance(c, dict):
                data["teams"][team] = {"elo": _seed_elo(int(c.get("prestige") or 5), ap.get(team)),
                                       "abbr": c.get("abbr")}
        user = (dynasty.get("team") or {}).get("name")
        if user and user not in data["teams"]:
            rk = ((dynasty.get("team") or {}).get("rankings") or {})
            data["teams"][user] = {"elo": _seed_elo(6, rk.get("ap")),
                                   "abbr": (dynasty.get("team") or {}).get("abbreviation")}
        # preseason projection for the user (drives the expectation delta + hot seat)
        proj = 0.0
        for g in (dynasty.get("schedule") or {}).get("full") or []:
            opp = g.get("opponent")
            if not opp:
                continue
            ue = data["teams"].get(user, {}).get("elo", ELO_BASE)
            oe = data["teams"].get(opp, {}).get("elo", ELO_BASE)
            proj += win_prob(ue, oe, a_home=bool(g.get("home")), b_home=not bool(g.get("home")))
        data["user"] = {"team": user, "proj_wins": round(proj, 2), "expected_wins_played": 0.0,
                        "baseline_wins": round(max(proj, 0.0), 2)}
        _write(year, data)
        return data


def elo_of(data: dict, team: str | None) -> float:
    return float((data.get("teams") or {}).get(team or "", {}).get("elo", ELO_BASE))


# --- weekly update ----------------------------------------------------------
def _mov_multiplier(margin: int, winner_elo_edge: float) -> float:
    """FiveThirtyEight's margin-of-victory multiplier: diminishing credit for
    blowouts, inflated credit for upsets (negative winner edge)."""
    return math.log(abs(margin) + 1.0) * (2.2 / (winner_elo_edge * 0.001 + 2.2))


def process_week(year: int, week: int, dynasty: dict) -> list[dict[str, Any]]:
    """Fold this week's finals into the ratings. Returns the processed game
    records (pre-game probability, surprisal, rating shift) for the candidate
    detectors; idempotent via per-game keys, so re-scans never double-apply."""
    data = ensure(year, dynasty)
    out: list[dict[str, Any]] = []
    with _lock:
        games = data.setdefault("games", {})
        user_team = (data.get("user") or {}).get("team")
        for g in ((dynasty.get("national") or {}).get("scoreboard") or []):
            if g.get("status") != "final" or g.get("home_score") is None:
                continue
            home, away = g.get("home") or {}, g.get("away") or {}
            hn, an = home.get("name"), away.get("name")
            key = f"{year}:{g.get('week', week)}:{an}@{hn}"
            if not hn or not an:
                continue
            if key in games:
                out.append(games[key])
                continue
            he, ae = elo_of(data, hn), elo_of(data, an)
            neutral = bool(g.get("neutral"))
            p_home = win_prob(he, ae, a_home=not neutral)
            # the sim's own line is the universe's expectation when present
            parsed = parse_line(g.get("line"))
            if parsed:
                fav_abbr, spread = parsed
                p_fav = spread_prob(spread)
                p_home = p_fav if fav_abbr == (home.get("abbr") or "") else 1.0 - p_fav
            hs, as_ = int(g["home_score"]), int(g["away_score"])
            home_won = hs >= as_
            p_actual = p_home if home_won else 1.0 - p_home
            margin = abs(hs - as_)
            winner_edge = (he - ae + (0 if neutral else HFA_ELO)) * (1 if home_won else -1)
            shift = K * _mov_multiplier(margin, winner_edge) * ((1.0 if home_won else 0.0) - p_home)
            data["teams"].setdefault(hn, {"elo": ELO_BASE})["elo"] = he + shift
            data["teams"].setdefault(an, {"elo": ELO_BASE})["elo"] = ae - shift
            rec = {
                "key": key, "week": g.get("week", week),
                "home": hn, "away": an,
                "score": f"{max(hs, as_)}-{min(hs, as_)}",   # winner's score first, as written

                "winner": hn if home_won else an, "loser": an if home_won else hn,
                "winner_rank": (home if home_won else away).get("rank"),
                "loser_rank": (away if home_won else home).get("rank"),
                "p_winner_pregame": round(p_actual, 4),
                "surprisal": round(surprisal(p_actual), 3),
                "margin": margin, "user": bool(g.get("user")),
            }
            games[key] = rec
            out.append(rec)
            if user_team in (hn, an):
                u = data.setdefault("user", {})
                u["expected_wins_played"] = round(float(u.get("expected_wins_played", 0.0))
                                                  + (p_home if user_team == hn else 1.0 - p_home), 3)
        _write(year, data)
    return out


def expected_wins_played(year: int, dynasty: dict) -> float:
    return float((ensure(year, dynasty).get("user") or {}).get("expected_wins_played", 0.0))


def projected_wins(year: int, dynasty: dict) -> float:
    return float((ensure(year, dynasty).get("user") or {}).get("proj_wins", 6.0))


def game_prob(year: int, dynasty: dict, team_a: str, team_b: str, *,
              a_home: bool = False, line: str | None = None,
              a_abbr: str | None = None) -> float:
    """P(team A wins) for an upcoming game: the published line when there is one,
    Elo otherwise."""
    parsed = parse_line(line)
    if parsed and a_abbr:
        fav, spread = parsed
        p_fav = spread_prob(spread)
        return p_fav if fav == a_abbr else 1.0 - p_fav
    data = ensure(year, dynasty)
    return win_prob(elo_of(data, team_a), elo_of(data, team_b), a_home=a_home, b_home=not a_home)
