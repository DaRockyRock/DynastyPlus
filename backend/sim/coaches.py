"""Fictional head coaches for every FBS team.

CFB27 owns a head coach for every program; the season tool stands in until
the real save format is readable. Each team gets a STABLE, FICTIONAL coach, seeded
by the team name + the season seed, so:

  * every program receives a distinct fictional coach for rankings, schedules,
    and coaching data, and
  * the names are consistent week to week and across a save.

Names come from first/last banks chosen to avoid real, recognizable head coaches.
`coach_map` de-duplicates so 136 teams get distinct names. The user's own program
is NOT set here, its coach comes from the customization identity store.
"""
from __future__ import annotations

import random

_FIRST = [
    "Wade", "Marcus", "Gil", "Dom", "Rex", "Hal", "Cliff", "Vance", "Brett", "Dane",
    "Russ", "Lonnie", "Chip", "Owen", "Hank", "Roy", "Carl", "Stan", "Max", "Gus",
    "Dean", "Wes", "Curt", "Reggie", "Dale", "Monte", "Earl", "Glenn", "Ray", "Buck",
    "Trent", "Cole", "Vince", "Sal", "Pete", "Lou", "Ned", "Cyrus", "Theo", "Grady",
    "Walt", "Nolan", "Drew", "Boyd", "Marv", "Sterling", "Dexter", "Roland", "Clint", "Abe",
]

_LAST = [
    "Hollis", "Avery", "Castellano", "Brennan", "Dawson", "Okeke", "Calloway", "Whitlock",
    "Fairchild", "Merle", "Brooks", "Harmon", "Sutton", "Mercer", "Calhoun", "Donovan",
    "Rourke", "Maddox", "Lang", "Boone", "Crews", "Hatcher", "Yates", "Ramsey", "Lockhart",
    "Easton", "Vickers", "Holloway", "Mathis", "Carver", "Renfro", "Tolliver", "Burch",
    "Hardin", "Ellison", "Garrity", "Coyle", "Devlin", "Beckett", "Stallworth", "Mund",
    "Paxton", "Quill", "Ackerman", "Buford", "Driscoll", "Fenwick", "Galloway", "Hargrove",
    "Ingram", "Kessler", "Larkin", "Mortenson", "Norwood", "Ortega", "Prentiss", "Radcliffe",
    "Salisbury", "Thornbury", "Underwood", "Vandermeer", "Westbrook", "Yardley",
]


def coach_for(team_name: str, seed: int | str) -> str:
    """A stable fictional coach name for one team (seeded by team + season seed)."""
    rng = random.Random(f"{seed}|coach|{team_name}")
    return f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"


def coach_map(team_names, seed: int | str) -> dict[str, str]:
    """{team name -> fictional coach} for every team, de-duplicated so two programs
    never share a coach. Deterministic for a given (teams, seed)."""
    used: set[str] = set()
    out: dict[str, str] = {}
    for name in sorted(team_names):  # sorted so the result is order-independent
        rng = random.Random(f"{seed}|coach|{name}")
        coach = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
        # On the rare collision, re-roll with a salt until the name is unique.
        salt = 0
        while coach in used and salt < 50:
            salt += 1
            coach = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
        used.add(coach)
        out[name] = coach
    return out


def tenure_for(team_name: str, seed: int | str) -> int:
    """A stable tenure (years at the program) for a team's coach, 1 to 11."""
    return random.Random(f"{seed}|tenure|{team_name}").randint(1, 11)


def _wl(record: str) -> tuple[int, int]:
    try:
        w, l = str(record).split("-")[:2]
        return int(w), int(l)
    except (ValueError, AttributeError):
        return 0, 0


# Weight (in games) of a coach's preseason expectation, so a tiny sample does not
# swing the heat. A 0-1 start barely moves it; a winless month or a 4-0 surge does.
_PRIOR_GAMES = 6


def hot_seat_heat(prestige: int, record: str, tenure: int) -> int:
    """A 0-100 hot-seat heat. A high-prestige program (expected to win) that is
    underperforming its expectation runs hot; a low-prestige program is given more
    rope. The record is shrunk toward the program's expectation by a prior worth a
    few games, so a single early loss does not max out the seat, while a sustained
    slide at a blue blood does."""
    prestige = max(1, min(10, prestige or 5))
    expected = 0.30 + (prestige - 1) / 9 * 0.55  # 0.30 (cupcake) .. 0.85 (blue blood)
    w, l = _wl(record)
    games = w + l
    # Bayesian shrinkage: treat the coach as if he also has _PRIOR_GAMES at his
    # program's expected win rate, so early results regress to the expectation.
    blended = (w + expected * _PRIOR_GAMES) / (games + _PRIOR_GAMES)
    gap = expected - blended  # positive = underperforming the program's standard
    heat = 34 + gap * 180 + (tenure - 5) * 2
    if tenure >= 7 and gap > 0.05:
        heat += 8  # a long-tenured coach who is sliding gets less patience
    return int(max(3, min(99, round(heat))))


def _trend(record_row: dict) -> str:
    """Heat trend from the team's current streak: losing heats the seat up, winning
    cools it down."""
    streak = str((record_row or {}).get("streak") or "").upper()
    if streak.startswith("L"):
        return "up"
    if streak.startswith("W"):
        return "down"
    return "flat"


def build_directory(universe: dict, records: dict, seed: int | str, *, user: str,
                    user_coach: str | None = None, user_tenure: int | None = None,
                    user_hot_seat: int | None = None) -> dict[str, dict]:
    """The league's coaching directory: {team -> coach entity}. Each entity carries
    name, tenure, the team's record, a hot-seat heat and trend, and identity bits.
    CFB27 owns this; the season tool stands in. The user's own program uses its
    identity coach (name/tenure/hot seat from the customization store)."""
    names = coach_map(universe.keys(), seed)
    out: dict[str, dict] = {}
    for team, info in universe.items():
        prestige = info.get("prestige") or 5
        rec_row = records.get(team) or {}
        record = rec_row.get("overall") or "0-0"
        is_user = team == user
        tenure = (user_tenure if is_user and user_tenure else tenure_for(team, seed))
        if is_user:
            heat = user_hot_seat if user_hot_seat is not None else hot_seat_heat(prestige, record, tenure)
            name = user_coach or names[team]
        else:
            heat = hot_seat_heat(prestige, record, tenure)
            name = names[team]
        out[team] = {
            "name": name, "team": team, "espn_id": info.get("espn_id"), "abbr": info.get("abbr"),
            "conference": info.get("conference"), "prestige": prestige,
            "tenure_years": tenure, "record": record, "hot_seat": heat, "trend": _trend(rec_row),
            "is_user": is_user,
        }
    return out
