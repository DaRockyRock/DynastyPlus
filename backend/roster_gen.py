"""Deterministic full-roster generator (Simulator-owned game data).

The Simulator stands in for CFB 27, which ships every program a full scholarship
roster. This builds that roster: an 85-man depth chart for the user's team with a
realistic position distribution, a rating curve that tapers by depth, plausible
classes / jersey numbers / NIL / retention risk, and unique names. It seeds
customization_game.DEFAULTS["players"]; the Store overlays the coach's edits on
top, the adapter writes it into the save, and the NIL board, phone, and archive
all read it straight from there.

Determinism matters: the roster is part of the save's content hash, so a fixed
seed keeps it byte-stable across process restarts and avoids churning meta.hash.

Leaf module: standard library plus customization_base constants only. It must not
import backend.sim (sim/__init__ imports the adapter, which imports the game
customization store, which imports this) or backend.customization_game, or the
import graph would cycle.
"""
from __future__ import annotations

import copy
import random
from typing import Any

from .customization_base import DEALBREAKERS

# Fixed seed -> identical roster every run -> stable save content hash.
_SEED = 20270824
ROSTER_SIZE = 85
# Keep committed roster NIL comfortably under the default $5M roster pool so the
# Dynasty Blueprint never opens already over budget. The long tail rounds to $0.
_TARGET_ROSTER_NIL = 4_000_000

# (code, display, count, starters, rating ceiling for the #1 at the spot)
_POSITION_PLAN: list[tuple[str, str, int, int, int]] = [
    ("QB",   "Quarterback",        4, 1, 91),
    ("RB",   "Running Back",       5, 1, 88),
    ("WR",   "Wide Receiver",     10, 3, 90),
    ("TE",   "Tight End",          4, 1, 84),
    ("OT",   "Offensive Tackle",   8, 2, 87),
    ("OG",   "Offensive Guard",    7, 2, 83),
    ("C",    "Center",             3, 1, 82),
    ("EDGE", "EDGE Rusher",        6, 2, 90),
    ("DT",   "Defensive Tackle",   7, 2, 86),
    ("LB",   "Linebacker",         9, 3, 87),
    ("CB",   "Cornerback",         9, 3, 88),
    ("S",    "Safety",             8, 2, 85),
    ("K",    "Kicker",             2, 1, 78),
    ("P",    "Punter",             2, 1, 76),
    ("LS",   "Long Snapper",       1, 1, 68),
]  # counts sum to 85

# Jersey number ranges that read true to the position, in preference order.
_JERSEY_RANGES: dict[str, list[range]] = {
    "QB":   [range(1, 20)],
    "RB":   [range(20, 50), range(1, 10)],
    "WR":   [range(1, 20), range(80, 90)],
    "TE":   [range(80, 90), range(40, 50)],
    "OT":   [range(50, 80)],
    "OG":   [range(50, 80)],
    "C":    [range(50, 80)],
    "EDGE": [range(40, 60), range(90, 100)],
    "DT":   [range(90, 100), range(50, 80)],
    "LB":   [range(1, 60)],
    "CB":   [range(1, 40)],
    "S":    [range(1, 50)],
    "K":    [range(90, 100), range(30, 50)],
    "P":    [range(90, 100), range(30, 50)],
    "LS":   [range(40, 60)],
}

_FIRST_NAMES = [
    "Marcus", "DeShawn", "Tyrell", "Cole", "Jalen", "Brock", "Eli", "Quinn", "Jamal",
    "Trey", "Xavier", "Cam", "Devin", "Isaiah", "Malik", "Drew", "Hunter", "Carter",
    "Jaylen", "Tre", "Bo", "Kade", "Rashad", "Donovan", "Micah", "Silas", "Gavin",
    "Roman", "Dante", "Knox", "Beau", "Zion", "Amari", "Cooper", "Maddox", "Tank",
    "Caleb", "Nolan", "Reese", "Tobias", "Jaxon", "Emmanuel", "Khalil", "Brody",
    "Deon", "Landon", "Pierce", "Rylan", "Terrence", "Ezra", "Dominic", "Kai",
    "Jared", "Marquis", "Dexter", "Holden", "Asher", "Cedric", "Tristan", "Lamar",
    "Garrett", "Sterling", "Jermaine", "Wyatt", "Demetrius", "Cason", "Ronan",
    "Tyson", "Darnell", "Bennett", "Jaxson", "Keegan", "Marcellus", "Shane",
    "Dawson", "Corey", "Antoine", "Preston", "Rashawn", "Graham", "Easton",
    "Jabari", "Colt", "Ferris", "Omar", "Declan", "Vince", "Rocco", "Tariq",
    "Brennan", "Solomon", "Hayden", "Marlon", "Finn", "Darius", "Chase", "Ledger",
]
_LAST_NAMES = [
    "Whitfield", "Carter", "Banks", "Vermeer", "Ross", "Hentges", "Sorenson", "Holloway",
    "Pickens", "Mercer", "Vaughn", "Okafor", "Delgado", "Brooks", "Salazar", "Pruitt",
    "Ashby", "Calhoun", "Reyes", "Mceachern", "Tillman", "Fontaine", "Boudreaux", "Hargrove",
    "Stallworth", "Kowalski", "Adeyemi", "Lindqvist", "Vance", "Driskell", "Cromartie", "Yarbrough",
    "Beaumont", "Castillo", "Whitaker", "Osei", "Lemieux", "Rasmussen", "Coleman", "Tagovasa",
    "Esposito", "Mackey", "Devine", "Northcutt", "Abara", "Sundberg", "Quintero", "Falk",
    "Hutchins", "Mwangi", "Petrakis", "Olufemi", "Castellano", "Drummond", "Barghouti", "Renfroe",
    "Sasaki", "Villanueva", "Achebe", "Lindgren", "Forsythe", "Mbappe", "Calloway", "Henriksen",
    "Diallo", "Marchetti", "Strahan", "Onwuachi", "Dembele", "Vasquez", "Aldridge", "Beaulieu",
    "Tucholski", "Asante", "Crenshaw", "Penaloza", "Kingsbury", "Okereke", "Saldana", "Folsom",
    "Nwosu", "Throckmorton", "Galarza", "Wexler", "Ibrahim", "Steinmetz", "Cardenas", "Babatunde",
    "Cisneros", "Lindholm", "Ouattara", "Brunderman", "Sequeira", "Maravich", "Ojeda", "Tindall",
]

_NOTES: dict[str, list[str]] = {
    "QB": ["Reads coverage fast, lives in the up-tempo system", "Big arm, throws receivers open", "Cool in the two-minute drill"],
    "RB": ["One-cut downhill runner with contact balance", "Home-run speed in the open field", "Reliable in pass protection"],
    "WR": ["Contested-catch specialist on the boundary", "Vertical threat who stretches the field", "Crisp route runner out of the slot"],
    "TE": ["Mismatch in the red zone", "Reliable chain-mover and willing blocker", "Move tight end who flexes out wide"],
    "OT": ["Anchors the edge in pass protection", "Light feet, mirrors speed rushers", "Mauler in the run game"],
    "OG": ["Plays with a nasty finish to the whistle", "Pulls and climbs to the second level", "Pocket-pusher on the interior"],
    "C": ["Sets the protection and never blows a call", "Athletic snapper who reaches the second level", "Steady anchor up the middle"],
    "EDGE": ["Wrecks the edge with a relentless motor", "Bend and burst off the corner", "Sets a hard edge against the run"],
    "DT": ["Two-gap presence who eats double teams", "Disruptive interior pass rush", "Stout at the point of attack"],
    "LB": ["Tone-setter who fills downhill", "Sideline-to-sideline range", "Quarterback of the front seven"],
    "CB": ["Sticky in man coverage, travels with the WR1", "Ball-hawk who bates throws", "Physical press corner"],
    "S": ["Quarterback of the secondary", "Range to play the deep middle", "Enforcer in the box"],
    "K": ["Reliable from inside 50", "Big leg on kickoffs", "Ice in the fourth quarter"],
    "P": ["Flips the field with hang time", "Pins opponents inside the 10", "Booming directional punter"],
    "LS": ["Automatic on every snap", "Steady core special-teamer", "Dependable in the kicking game"],
}


def _rng() -> random.Random:
    return random.Random(_SEED)


def _rating(idx: int, starters: int, ceiling: int, jitter: int) -> int:
    """Decline gently across the starters, then steeply down the depth chart."""
    if idx < starters:
        base = ceiling - idx * 2
    else:
        base = ceiling - starters * 2 - (idx - starters + 1) * 5
    return max(55, min(99, base + jitter))


def _slot(idx: int, starters: int, display: str) -> str:
    if idx < starters:
        return f"Starting {display}"
    if idx < starters * 2:
        return f"Backup {display}"
    return f"Reserve {display}"


def _year(rng: random.Random, idx: int, count: int) -> str:
    """Starters skew upperclassman; the back of the depth chart skews young."""
    if idx < max(1, count // 3):
        return rng.choices(["SR", "JR", "GR", "SO"], weights=[34, 34, 14, 18])[0]
    if idx < (2 * count) // 3:
        return rng.choices(["JR", "SO", "SR", "FR"], weights=[30, 34, 16, 20])[0]
    return rng.choices(["FR", "SO", "JR"], weights=[52, 34, 14])[0]


def _jersey(rng: random.Random, code: str, used: set[int]) -> int:
    for rng_range in _JERSEY_RANGES.get(code, [range(0, 100)]):
        choices = [n for n in rng_range if n not in used]
        if choices:
            num = rng.choice(choices)
            used.add(num)
            return num
    free = [n for n in range(0, 100) if n not in used]
    num = rng.choice(free) if free else rng.randint(0, 99)
    used.add(num)
    return num


def _name(rng: random.Random, used_full: set[str], used_first: set[str]) -> str:
    # Prefer a fresh first name (the pool is larger than the roster) but allow the
    # occasional repeat, so the depth chart reads like a real one without three of
    # the same first name clustering at the top.
    for _ in range(60):
        first = rng.choice(_FIRST_NAMES)
        name = f"{first} {rng.choice(_LAST_NAMES)}"
        if name in used_full:
            continue
        if first in used_first and rng.random() < 0.85:
            continue
        used_full.add(name)
        used_first.add(first)
        return name
    for _ in range(200):  # fall back to any unique full name
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        if name not in used_full:
            used_full.add(name)
            return name
    # Pools are large enough that this is effectively unreachable; keep it total.
    name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)} {len(used_full)}"
    used_full.add(name)
    return name


def _stat_line(rng: random.Random, code: str, rating: int, idx: int, starters: int) -> str:
    """A plausible baseline season line. Starters get production; backups stay
    light or blank. The Simulator overwrites the top QB/RB/WR/EDGE lines with the
    real simulated totals, so these are the preseason placeholders for the rest."""
    if idx >= starters and rng.random() < 0.55:
        return ""
    s = max(0.4, (rating - 60) / 35)  # 0..~1 production scalar
    r = rng.uniform(0.8, 1.2)
    if code == "QB":
        return f"{int(2600 * s * r):,} yds, {int(22 * s * r)} TD, {rng.randint(3, 9)} INT"
    if code == "RB":
        return f"{int(950 * s * r):,} yds, {int(10 * s * r)} TD"
    if code in ("WR", "TE"):
        return f"{int(48 * s * r)} rec, {int(720 * s * r):,} yds, {int(6 * s * r)} TD"
    if code == "EDGE":
        return f"{round(8.5 * s * r, 1):g} sacks, {int(13 * s * r)} TFL"
    if code == "DT":
        return f"{int(34 * s * r)} tackles, {round(3.5 * s * r, 1):g} sacks"
    if code == "LB":
        return f"{int(78 * s * r)} tackles, {int(2 * s * r)} FF"
    if code == "CB":
        return f"{rng.randint(1, 4)} INT, {int(9 * s * r)} PBU"
    if code == "S":
        return f"{int(62 * s * r)} tackles, {rng.randint(1, 4)} INT"
    if code == "K":
        att = rng.randint(16, 26)
        return f"{int(att * (0.7 + 0.2 * s))}/{att} FG"
    if code == "P":
        return f"{round(rng.uniform(42, 47), 1)} avg, {rng.randint(12, 26)} inside 20"
    return ""  # OL, LS: no box-score stats


def _draft_stock(rng: random.Random, rating: int, year: str) -> str:
    if year not in ("JR", "SR", "GR"):
        return ""
    if rating >= 90:
        return rng.choice(["Round 1 lock", "Top-15 buzz"])
    if rating >= 87:
        return rng.choice(["Round 1-2 buzz", "Day 2 lock"])
    if rating >= 84:
        return rng.choice(["Day 2-3 range", "Late-round flier"])
    return ""


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (name[:2] or "??").upper()


def _build() -> list[dict[str, Any]]:
    rng = _rng()
    used_names: set[str] = set()
    used_first: set[str] = set()
    used_jerseys: set[int] = set()
    players: list[dict[str, Any]] = []

    for code, display, count, starters, ceiling in _POSITION_PLAN:
        for idx in range(count):
            jitter = rng.randint(-2, 2)
            rating = _rating(idx, starters, ceiling, jitter)
            year = _year(rng, idx, count)
            name = _name(rng, used_names, used_first)
            is_starter = idx < starters
            risk = (rng.randint(8, 26) if is_starter else rng.randint(24, 56))
            players.append({
                "name": name,
                "position": code,
                "year": year,
                "jersey": _jersey(rng, code, used_jerseys),
                "rating": rating,
                "depth_chart_slot": _slot(idx, starters, display),
                "stat_line": _stat_line(rng, code, rating, idx, starters),
                "note": rng.choice(_NOTES[code]),
                "draft_stock": _draft_stock(rng, rating, year),
                # NIL filled in after the curve is known (see below).
                "expected_nil": 0,
                "current_nil": 0,
                "risk_of_leaving": risk,
                "dealbreaker": rng.choice(DEALBREAKERS),
                "image": "",
                # _starter/_group are scratch fields stripped before returning.
                "_starter": is_starter,
            })

    _assign_nil(rng, players)
    for p in players:
        p.pop("_starter", None)

    # Lead with the headliners so [:5]/[:6] consumers (archive, article search)
    # and the roster view surface the stars first.
    players.sort(key=lambda p: (p["rating"], p["position"] == "QB"), reverse=True)
    return players


# Position pay weights: the market pays for premium positions (quarterback first),
# barely anything for the specialists.
_POS_NIL_WEIGHT = {
    "QB": 1.6, "WR": 1.2, "EDGE": 1.2, "CB": 1.15, "OT": 1.1, "RB": 1.1,
    "DT": 1.0, "S": 1.0, "LB": 1.0, "TE": 0.95, "OG": 0.85, "C": 0.85,
    "K": 0.35, "P": 0.35, "LS": 0.2,
}


def _assign_nil(rng: random.Random, players: list[dict[str, Any]]) -> None:
    """Distribute a fixed NIL pot across the roster on a steep, top-heavy curve so
    the stars command real money and the deep tail rounds to near $0."""
    def raw(p: dict[str, Any]) -> float:
        base = max(0, p["rating"] - 60) ** 3.3
        if p["_starter"]:
            base *= 2.0
        return base * _POS_NIL_WEIGHT.get(p["position"], 1.0)

    total = sum(raw(p) for p in players) or 1.0
    for p in players:
        current = round(raw(p) / total * _TARGET_ROSTER_NIL / 5000) * 5000
        expected = round(current * rng.uniform(1.05, 1.3) / 5000) * 5000
        p["current_nil"] = current
        p["expected_nil"] = expected


# Built once at import; stable for the life of the process.
_ROSTER: list[dict[str, Any]] = _build()


def _star_name(position: str) -> str:
    for p in _ROSTER:
        if p["position"] == position:
            return p["name"]
    return ""


# The top QB and RB, exposed so the media store's seed phone contacts can link to
# real roster players for in-chat NIL offers.
STAR_QB_NAME = _star_name("QB")
STAR_RB_NAME = _star_name("RB")
STAR_QB_AVATAR = _initials(STAR_QB_NAME)
STAR_RB_AVATAR = _initials(STAR_RB_NAME)


def build_roster() -> list[dict[str, Any]]:
    """A deep copy of the canonical generated roster (so callers can mutate it)."""
    return copy.deepcopy(_ROSTER)
