"""League-wide transfer-portal market (Simulator-owned).

A second market engine parallel to sim/recruiting.py. CFB27 opens the transfer
portal in offseason windows; until the real save is readable, the Simulator owns
that market here:

  * The portal is CLOSED during the regular season (empty), and OPENS in the
    offseason window right after the regular season (the real winter window).
  * On the first advance into the window it seeds a national pool of fictional
    portal entrants leaving programs across FBS, PLUS the user's own real roster
    players whose satisfaction (sim/satisfaction.py) pushed them to leave.
  * Each entrant carries interest in a handful of destination schools that drifts
    weekly; the user competes for incoming entrants through the SAME budget
    interest the high-school recruiting cycle uses (recruiting hours + NIL), so a
    coach can land a transfer. Entrants commit over the window and sign at close.

Non-user FBS teams have no stored rosters (only ratings/prestige), so generated
entrants are fictional, the way recruiting generates its national class. The
user's outgoing players are REAL roster names so departures match the roster.

Persisted at data/sim/<year>_portal.json. Deterministic from the season seed;
weekly progression is idempotent (each week processed once).
"""
from __future__ import annotations

import json
from typing import Any

from .. import budget, config, customization_game as customization
from . import polls, recruiting, satisfaction, standings
from .engine import make_rng

# How many offseason weeks the window stays open before the class signs. The
# window opens at weeks_total + 1 and signs at weeks_total + WINDOW_WEEKS.
WINDOW_WEEKS = 4
# Size of the generated national entrant pool (excludes the user's own outgoing).
POOL_SIZE = 320
# Entrants the user's program actively competes for (forced onto the user board).
USER_BOARD_SIZE = 45
# A user roster player at or above this risk may roll into the portal. Tuned to
# the satisfaction scale (a discontent player on a struggling team tops out around
# the mid-50s), so a normal cycle loses a realistic handful of mostly back-of-the-
# depth-chart players, more when the season went badly.
OUTGOING_THRESHOLD = 40


def _path(year: int):
    return config.SIM_DIR / f"{year}_portal.json"


def get(year: int) -> dict[str, Any] | None:
    p = _path(year)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _save(state: dict[str, Any]) -> None:
    try:
        _path(state["year"]).write_text(json.dumps(state))
    except OSError:
        pass


def reset(year: int) -> None:
    try:
        _path(year).unlink()
    except OSError:
        pass


# --- window ---------------------------------------------------------------
def window_open(week: int, weeks_total: int) -> bool:
    """True while the offseason portal window is actively open (entries + moves)."""
    return weeks_total < week <= weeks_total + WINDOW_WEEKS


def has_opened(week: int, weeks_total: int) -> bool:
    """True once the window has opened at all (open now, or signed and viewable)."""
    return week > weeks_total


def window(year: int, week: int, weeks_total: int) -> dict[str, Any]:
    """The window descriptor surfaced in the save under transfer_portal.window."""
    st = get(year)
    opened_week = st.get("opened_week") if st else None
    if not has_opened(week, weeks_total):
        return {"open": False, "label": "Closed", "opened_week": opened_week}
    if window_open(week, weeks_total):
        return {"open": True, "label": "Winter window", "opened_week": opened_week}
    return {"open": False, "label": "Window closed", "opened_week": opened_week}


# --- generation -----------------------------------------------------------
def _stars(ovr: int) -> int:
    if ovr >= 90:
        return 5
    if ovr >= 84:
        return 4
    if ovr >= 76:
        return 3
    return 2


_YEARS = ["SO", "JR", "SR", "GR"]


def _make_entrant(seed: int | str, year: int, idx: int, universe: dict[str, Any],
                  user: str) -> dict[str, Any]:
    rng = make_rng(seed, year, "portal", idx)
    pos = recruiting._weighted(rng, recruiting.POSITIONS)[0]
    ovr = int(max(68, min(95, round(rng.gauss(80, 6)))))
    others = [t for t in universe if t != user]
    origin = rng.choice(others) if others else user
    name = _make_name(rng, idx)
    klass = rng.choices(_YEARS, weights=[26, 34, 28, 12])[0]
    stars = _stars(ovr)
    return {
        "id": budget.entity_id(name),
        "name": name, "position": pos, "year": klass,
        "ovr": ovr, "rating": round(0.78 + (ovr - 68) / 27 * 0.20, 4), "stars": stars,
        "from": origin, "is_user_outgoing": False,
        "dealbreaker": rng.choice(recruiting.DEALBREAKERS),
        "expected_nil": recruiting._expected_nil(stars, rng),
        "schools": {}, "committed_to": None, "commit_week": None, "signed": False,
    }


def _make_name(rng, idx: int) -> str:
    return f"{rng.choice(recruiting.FIRST)} {rng.choice(recruiting.LAST)}"


def _destinations(seed: int | str, year: int, universe: dict[str, Any],
                  entrant: dict[str, Any], *, exclude: set[str], rng) -> dict[str, int]:
    n = max(3, min(8, 3 + (entrant["stars"] - 3) * 2 + rng.randint(0, 2)))
    schools = [s for s in recruiting._pick_schools(universe, entrant, n + len(exclude), rng)
               if s not in exclude][:n]
    interest = {}
    for s in schools:
        irng = make_rng(seed, year, "portal_interest", entrant["name"], s)
        interest[s] = recruiting._initial_interest("", universe.get(s, {}).get("rating", 55), "", irng)
    return interest


def _user_outgoing(year: int, week: int, st: dict[str, Any], records, ap_rank: int | None
                   ) -> list[dict[str, Any]]:
    """The user's REAL roster players who roll into the portal, driven by their
    live satisfaction risk. A higher risk means a higher chance of actually leaving."""
    universe = st["teams"]
    user = st["user_team"]
    seed = st["seed"]
    prestige = (universe.get(user) or {}).get("prestige", 5)
    coach_hot = (customization.head_coach() or {}).get("hot_seat")
    rated = satisfaction.compute(
        customization.section("players"), record=records.get(user),
        prestige=prestige, ap_rank=ap_rank, week=week,
        weeks_total=st["weeks_total"], seed=seed, coach_hot_seat=coach_hot)

    out: list[dict[str, Any]] = []
    others = [t for t in universe if t != user]
    for p in rated:
        risk = int(p.get("risk_of_leaving", 0))
        if risk < OUTGOING_THRESHOLD:
            continue
        prob = min(0.90, 0.05 + (risk - OUTGOING_THRESHOLD) / 22 * 0.85)
        if make_rng(seed, year, "portal_out_roll", p["name"]).random() >= prob:
            continue
        stars = _stars(int(p.get("rating", 78)))
        ent = {
            "id": budget.entity_id(p["name"]),
            "name": p["name"], "position": p.get("position"), "year": p.get("year"),
            "ovr": int(p.get("rating", 78)), "rating": round(0.78 + (int(p.get("rating", 78)) - 68) / 27 * 0.20, 4),
            "stars": stars, "from": user, "is_user_outgoing": True,
            "dealbreaker": p.get("dealbreaker"), "expected_nil": int(p.get("expected_nil", 0)),
            "risk_reason": p.get("risk_reason"),
            "schools": {}, "committed_to": None, "commit_week": None, "signed": False,
        }
        rng = make_rng(seed, year, "portal_out_dest", p["name"])
        ent["schools"] = _destinations(seed, year, universe, ent, exclude={user}, rng=rng)
        out.append(ent)
    return out


def _open(year: int, week: int, st: dict[str, Any], records, ap_rank: int | None) -> dict[str, Any]:
    """Seed the entrant pool the first time the window opens this season."""
    universe = st["teams"]
    user = st["user_team"]
    seed = st["seed"]

    entrants = [_make_entrant(seed, year, i, universe, user) for i in range(POOL_SIZE)]

    # Force the user onto the boards of the top-fit incoming entrants so the coach
    # always has portal targets to chase (mirrors recruiting's user board).
    user_rating = (universe.get(user) or {}).get("rating", 70)
    fit = sorted(entrants, key=lambda e: (user_rating - e["ovr"]) * 0.5
                 + make_rng(seed, year, "portal_fit", e["name"]).gauss(0, 6), reverse=True)
    board_ids = {e["id"] for e in fit[:USER_BOARD_SIZE]}

    for e in entrants:
        rng = make_rng(seed, year, "portal_dest", e["name"])
        e["schools"] = _destinations(seed, year, universe, e, exclude=set(), rng=rng)
        if e["id"] in board_ids and user not in e["schools"]:
            irng = make_rng(seed, year, "portal_interest", e["name"], user)
            e["schools"][user] = recruiting._initial_interest("", user_rating, "", irng)

    # The user's own departures (real roster names).
    entrants += _user_outgoing(year, week, st, records, ap_rank)

    state = {
        "year": year, "seed": seed, "user_team": user,
        "opened_week": week, "last_advanced_week": 0, "entrants": entrants,
    }
    _save(state)
    return state


# --- weekly progression ---------------------------------------------------
def _commit_prob(week: int, weeks_total: int, top_interest: float, signing: bool) -> float:
    if signing:
        return 1.0
    if top_interest < 60:
        return 0.0
    into = week - weeks_total  # 1..WINDOW_WEEKS
    timing = 0.18 + into / max(1, WINDOW_WEEKS) * 0.30
    strength = (top_interest - 60) / 40 * 0.4
    return min(0.9, timing + strength)


def advance(year: int, week: int, st: dict[str, Any]) -> dict[str, Any]:
    """Open the window (once) and progress every uncommitted entrant one week.
    No-op outside the window. Idempotent per week. `st` is the live sim season."""
    weeks_total = st["weeks_total"]
    if not window_open(week, weeks_total):
        return get(year) or {}

    universe = st["teams"]
    user = st["user_team"]
    seed = st["seed"]
    # Records + AP rank as of the week just played, to drive the user's departures.
    records = standings.compute_records(universe, st["schedule"], st["results"], week + 1)
    ap_rank = polls.rank_of(polls.compute(universe, records)["_ap_order"], user)

    state = get(year)
    if state is None:
        state = _open(year, week, st, records, ap_rank)
    if week <= state.get("last_advanced_week", 0):
        return state

    user_interest = budget.load(year).get("interest", {})
    signing = week >= weeks_total + WINDOW_WEEKS

    for e in state["entrants"]:
        if e["committed_to"]:
            e["signed"] = signing or e["signed"]
            continue
        schools = e["schools"]
        if not schools:
            continue
        leader = max(schools, key=schools.get)
        for s in list(schools):
            rng = make_rng(seed, year, week, "portal_drift", e["name"], s)
            drift = rng.gauss(0, 4) + (2.4 if s == leader else 0) \
                + (universe.get(s, {}).get("rating", 55) - 60) * 0.06
            schools[s] = int(max(0, min(100, schools[s] + drift)))
        # The coach's competitive interest (baseline fit + recruiting hours / NIL).
        if not e["is_user_outgoing"] and user in schools and e["id"] in user_interest:
            schools[user] = int(user_interest[e["id"]])

        leader = max(schools, key=schools.get)
        top = schools[leader]
        crng = make_rng(seed, year, week, "portal_commit", e["name"])
        if crng.random() < _commit_prob(week, weeks_total, top, signing):
            e["committed_to"] = leader
            e["commit_week"] = week
            e["signed"] = signing

    state["last_advanced_week"] = week
    _save(state)
    return state


# --- views ----------------------------------------------------------------
def _meta(universe: dict[str, Any] | None, school: str | None) -> dict[str, Any]:
    info = (universe or {}).get(school) if school else None
    return {"abbr": (info or {}).get("abbr"), "espn_id": (info or {}).get("espn_id")}


def _leader(e: dict[str, Any]) -> str | None:
    return max(e["schools"], key=e["schools"].get) if e["schools"] else None


def user_outgoing_names(year: int) -> set[str]:
    """Names of the user's roster players who have entered the portal (for the
    adapter to flag on the roster). Empty until the window opens."""
    st = get(year)
    if not st:
        return set()
    return {e["name"] for e in st["entrants"] if e.get("is_user_outgoing")}


def user_board(year: int, universe: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    """The user's portal board: incoming (committed in), outgoing (real departures),
    and targets (incoming entrants the user is pursuing). Shaped for the Dynasty+
    portal page (name/position/from/to + interest/stage/grade)."""
    st = get(year)
    if not st:
        return {"incoming": [], "outgoing": [], "targets": []}
    user = st["user_team"]
    incoming, outgoing, targets = [], [], []
    for e in st["entrants"]:
        if e.get("is_user_outgoing"):
            dest = e["committed_to"] or _leader(e) or "Undecided"
            outgoing.append({
                "name": e["name"], "position": e["position"], "to": dest,
                **{f"to_{k}": v for k, v in _meta(universe, e["committed_to"]).items()},
                "ovr": e["ovr"], "stars": e["stars"],
                "reason": e.get("risk_reason"),
            })
            continue
        if e["committed_to"] == user:
            incoming.append({
                "name": e["name"], "position": e["position"], "from": e["from"],
                **{f"from_{k}": v for k, v in _meta(universe, e["from"]).items()},
                "ovr": e["ovr"], "stars": e["stars"], "expected_nil": e["expected_nil"],
                "status": "Enrolled" if e["signed"] else "Committed",
            })
        elif user in e["schools"] and not e["committed_to"]:
            interest = int(e["schools"].get(user, 0))
            targets.append({
                "name": e["name"], "position": e["position"], "from": e["from"],
                **{f"from_{k}": v for k, v in _meta(universe, e["from"]).items()},
                "ovr": e["ovr"], "stars": e["stars"], "expected_nil": e["expected_nil"],
                "interest": interest, "stage": budget.stage_for_interest(interest),
                "leader": _leader(e),
            })
    incoming.sort(key=lambda r: -r["ovr"])
    targets.sort(key=lambda r: -r["interest"])
    outgoing.sort(key=lambda r: -r["ovr"])
    return {"incoming": incoming, "outgoing": outgoing, "targets": targets}


def class_grade(year: int) -> dict[str, Any]:
    """A grade for the user's incoming portal haul, by count + talent."""
    board = user_board(year)
    inc = board["incoming"]
    n = len(inc)
    if not n:
        return {"grade": "NR", "gpa": 0.0,
                "summary": "No portal additions have committed yet."}
    avg = sum(p["ovr"] for p in inc) / n
    grade = "A" if avg >= 86 else "B+" if avg >= 82 else "B" if avg >= 78 else "C+"
    gpa = round(min(4.0, 2.4 + (avg - 75) / 12), 2)
    pos = ", ".join(sorted({p["position"] for p in inc}))
    return {"grade": grade, "gpa": gpa,
            "summary": (f"Added {n} transfer{'s' if n != 1 else ''} from the portal"
                        + (f", reinforcing {pos}. " if pos else ". ")
                        + "The board leaned toward immediate help.")}


def national_list(year: int, universe: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Flat browsable list of every portal entrant for a national board UI."""
    st = get(year)
    if not st:
        return []
    out = []
    for e in st["entrants"]:
        leader = _leader(e)
        status = "Signed" if e["signed"] else ("Committed" if e["committed_to"] else "In portal")
        out.append({
            "id": e["id"], "name": e["name"], "position": e["position"], "year": e["year"],
            "ovr": e["ovr"], "stars": e["stars"], "from": e["from"],
            **{f"from_{k}": v for k, v in _meta(universe, e["from"]).items()},
            "status": status, "committed_to": e["committed_to"],
            **{f"to_{k}": v for k, v in _meta(universe, e["committed_to"]).items()},
            "leader": leader, "expected_nil": e["expected_nil"], "is_user_outgoing": e["is_user_outgoing"],
        })
    return out
