"""National recruiting cycle.

A second simulation engine, parallel to the game engine: it generates a deep
national class (~700 prospects) and runs every one of them through a full
recruiting process across the season. Each prospect carries an interest level in
the handful of schools recruiting him; those levels drift weekly, the leader
pulls ahead, and prospects commit on a season-long timeline (more late), then
sign at the end. Blue-blood programs naturally land stronger classes because
prestige seeds higher initial interest with more, higher-rated prospects.

The user's program is unified with the existing budget engine: for prospects the
user is recruiting, the user-school interest is taken from backend.budget (the
baseline fit plus whatever recruiting hours / NIL the coach has spent), so the
coach genuinely competes for, and can land, real national prospects.

Persisted at data/sim/<year>_recruiting.json. Recomputed views feed the adapter
(the user's board) and the national recruit browser. Deterministic from the
season seed; weekly progression is idempotent (each week processed once).
"""
from __future__ import annotations

import json
from typing import Any

from .. import budget, config
from .engine import make_rng

CLASS_SIZE = 700
USER_BOARD_SIZE = 70  # prospects the user's program actively recruits

# Position pool with rough roster-need weights.
POSITIONS = [
    ("QB", 4), ("RB", 7), ("WR", 12), ("TE", 5), ("OT", 9), ("IOL", 8),
    ("EDGE", 9), ("DT", 8), ("LB", 10), ("CB", 11), ("S", 8), ("ATH", 3),
]

# Recruiting hotbeds, weighted. Region used for a light proximity bonus.
STATES = [
    ("TX", 16, "South"), ("FL", 15, "South"), ("GA", 13, "South"), ("CA", 13, "West"),
    ("OH", 7, "Midwest"), ("AL", 6, "South"), ("LA", 6, "South"), ("NC", 5, "South"),
    ("VA", 4, "South"), ("PA", 5, "Northeast"), ("NJ", 4, "Northeast"), ("MI", 4, "Midwest"),
    ("IL", 4, "Midwest"), ("TN", 4, "South"), ("MD", 3, "Northeast"), ("SC", 3, "South"),
    ("MS", 3, "South"), ("AZ", 3, "West"), ("WA", 3, "West"), ("MO", 3, "Midwest"),
    ("IN", 2, "Midwest"), ("OK", 3, "Plains"), ("CO", 2, "West"), ("UT", 2, "West"),
    ("WI", 2, "Midwest"), ("MN", 2, "Midwest"), ("KS", 2, "Plains"), ("NE", 1, "Plains"),
    ("KY", 2, "South"), ("OR", 2, "West"), ("NV", 2, "West"), ("CT", 1, "Northeast"),
]

CONF_REGION = {
    "SEC": "South", "ACC": "South", "Big Ten": "Midwest", "Big 12": "Plains",
    "Pac-12": "West", "Mountain West": "West", "American": "South", "Sun Belt": "South",
    "MAC": "Midwest", "Conference USA": "South", "FBS Independents": "Northeast",
}

CITY_PREFIX = ["North", "South", "East", "West", "New", "Fort", "Lake", "Mount", "Port", ""]
CITY_BASE = ["Bridge", "Field", "Haven", "Crest", "Ridge", "Brook", "Vale", "Grove",
             "Park", "Forge", "Camden", "Dalton", "Easton", "Garland", "Hampton", "Irving",
             "Jackson", "Kingston", "Laurel", "Maddox"]
CITY_SUFFIX = ["ville", " City", " Heights", " Springs", "town", " Falls", " Park", ""]

FIRST = [
    "Marcus", "DeShawn", "Tyrell", "Cole", "Jalen", "Brock", "Eli", "Quinn", "Jamal", "Trey",
    "Xavier", "Cam", "Devin", "Isaiah", "Malik", "Drew", "Hunter", "Carter", "Jaylen", "Tre",
    "Bo", "Kade", "Rashad", "Donovan", "Micah", "Silas", "Gavin", "Roman", "Dante", "Knox",
    "Beau", "Zion", "Amari", "Cooper", "Maddox", "Tank", "Jaxon", "Keon", "Rory", "Tobias",
    "Damari", "Emory", "Kingston", "Lennox", "Nehemiah", "Otis", "Princeton", "Rasheed", "Sincere", "Titus",
    "Demarcus", "Javon", "Kyree", "Lamar", "Marquise", "Nasir", "Quintrell", "Saevion", "Tremaine", "Vince",
]
LAST = [
    "Whitfield", "Carter", "Banks", "Vermeer", "Ross", "Hentges", "Sorenson", "Holloway", "Pickens", "Mercer",
    "Vaughn", "Okafor", "Delgado", "Brooks", "Salazar", "Pruitt", "Ashby", "Calhoun", "Reyes", "Tillman",
    "Fontaine", "Boudreaux", "Hargrove", "Stallworth", "Kowalski", "Adeyemi", "Lindqvist", "Vance", "Driskell", "Yarbrough",
    "Beckham", "Cromwell", "Diaz", "Ellington", "Faulkner", "Gibbs", "Hollis", "Ireland", "Jennings", "Kearse",
    "Lott", "Mayfield", "Nunez", "Oliver", "Pannell", "Rivers", "Sheffield", "Trotter", "Underwood", "Whitlow",
    "Ackerman", "Barfield", "Castellano", "Dupree", "Eubanks", "Ferreira", "Goodson", "Holcomb", "Isaacs", "Jeffress",
]

DEALBREAKERS = [
    "Brand Exposure", "Playing Time", "NFL Readiness", "Development",
    "Proximity to Home", "Championship Culture", "Coaching Stability",
]

HT_WT = {
    "QB": (75, 215), "RB": (70, 205), "WR": (73, 190), "TE": (77, 248), "OT": (78, 305),
    "IOL": (76, 312), "EDGE": (76, 250), "DT": (75, 300), "LB": (74, 232), "CB": (71, 185),
    "S": (73, 200), "ATH": (73, 195),
}


def _path(year: int):
    return config.SIM_DIR / f"{year}_recruiting.json"


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


# --- generation -----------------------------------------------------------
def _weighted(rng, items: list[tuple]) -> Any:
    total = sum(w for _, w, *_ in items)
    pick = rng.uniform(0, total)
    acc = 0.0
    for entry in items:
        acc += entry[1]
        if pick <= acc:
            return entry
    return items[-1]


def _city(rng) -> str:
    pre = rng.choice(CITY_PREFIX)
    base = rng.choice(CITY_BASE)
    suf = rng.choice(CITY_SUFFIX)
    return (f"{pre} " if pre else "") + base + suf


def _stars_for_rank(rank: int) -> int:
    if rank <= 32:
        return 5
    if rank <= 330:
        return 4
    return 3


def _ovr_for_rank(rank: int, rng) -> int:
    base = 99 - (rank - 1) * (99 - 72) / (CLASS_SIZE - 1)
    return int(max(70, min(99, round(base + rng.gauss(0, 1.2)))))


def _expected_nil(stars: int, rng) -> int:
    if stars == 5:
        return int(rng.uniform(400_000, 1_200_000) // 10_000 * 10_000)
    if stars == 4:
        return int(rng.uniform(80_000, 400_000) // 5_000 * 5_000)
    return int(rng.uniform(10_000, 80_000) // 1_000 * 1_000)


def _unique_name(rng, used: set) -> str:
    for _ in range(40):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if name not in used:
            used.add(name)
            return name
    # extremely unlikely fallback
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)} {len(used)}"
    used.add(name)
    return name


def _conf_region(universe: dict, school: str) -> str:
    return CONF_REGION.get(universe.get(school, {}).get("conference"), "")


def _initial_interest(prospect_region: str, school_rating: float, region: str, rng) -> int:
    base = (school_rating - 35) / (99 - 35) * 45 + 10
    if region and region == prospect_region:
        base += 8
    return int(max(5, min(68, round(base + rng.gauss(0, 8)))))


def _pick_schools(universe: dict, prospect, n: int, rng) -> list[str]:
    """Sample n schools weighted by prestige (rating)."""
    names = list(universe.keys())
    weights = [max(1.0, (universe[s]["rating"] - 30)) ** 1.6 for s in names]
    chosen: list[str] = []
    pool = list(zip(names, weights))
    for _ in range(min(n, len(pool))):
        total = sum(w for _, w in pool)
        pick = rng.uniform(0, total)
        acc = 0.0
        idx = 0
        for i, (_, w) in enumerate(pool):
            acc += w
            if pick <= acc:
                idx = i
                break
        chosen.append(pool[idx][0])
        pool.pop(idx)
    return chosen


def new_class(year: int, seed: int, universe: dict[str, Any], user_team: str | None) -> dict[str, Any]:
    used_names: set = set()
    prospects: list[dict[str, Any]] = []

    # 1) skeletons (name, position, location, raw ovr)
    for i in range(CLASS_SIZE):
        rng = make_rng(seed, year, "prospect", i)
        pos = _weighted(rng, POSITIONS)[0]
        st = _weighted(rng, STATES)
        state, region = st[0], st[2]
        ht, wt = HT_WT.get(pos, (73, 210))
        prospects.append({
            "name": _unique_name(rng, used_names),
            "position": pos,
            "state": state, "region": region, "city": _city(rng),
            "height": ht + rng.randint(-2, 3), "weight": wt + rng.randint(-12, 16),
            "_ovr_raw": _ovr_for_rank(i + 1, rng),
            "dealbreaker": rng.choice(DEALBREAKERS),
        })

    # 2) rank by ovr, assign stars / national + position ranks / NIL
    prospects.sort(key=lambda p: p["_ovr_raw"], reverse=True)
    pos_counter: dict[str, int] = {}
    for rank, p in enumerate(prospects, start=1):
        rng = make_rng(seed, year, "grade", p["name"])
        p["national_rank"] = rank
        p["ovr"] = p.pop("_ovr_raw")
        p["stars"] = _stars_for_rank(rank)
        p["rating"] = round(0.80 + (CLASS_SIZE - rank) / CLASS_SIZE * 0.19, 4)  # 0-1 composite
        pos_counter[p["position"]] = pos_counter.get(p["position"], 0) + 1
        p["position_rank"] = pos_counter[p["position"]]
        p["expected_nil"] = _expected_nil(p["stars"], rng)
        p["id"] = budget.entity_id(p["name"])

    # 3) recruiting schools + initial interest. Force the user onto the top
    #    USER_BOARD_SIZE prospects by user-fit so the coach always has a board.
    user_rating = universe.get(user_team, {}).get("rating", 70) if user_team else 0
    user_region = _conf_region(universe, user_team) if user_team else ""
    fit_rank = []
    for p in prospects:
        rng = make_rng(seed, year, "userfit", p["name"])
        # Base fit plus a prestige-vs-demand term: a stronger program reaches
        # higher-rated prospects, a weaker one skews to lower-ranked ones.
        fit = _initial_interest(p["region"], user_rating, user_region, rng)
        fit += (user_rating - p["ovr"]) * 0.5
        fit_rank.append((fit, p))
    fit_rank.sort(key=lambda t: t[0], reverse=True)
    user_board_ids = {p["id"] for _, p in fit_rank[:USER_BOARD_SIZE]} if user_team else set()

    for p in prospects:
        rng = make_rng(seed, year, "schools", p["name"])
        n = max(3, min(9, 3 + (p["stars"] - 3) * 2 + rng.randint(0, 2)))
        schools = _pick_schools(universe, p, n, rng)
        if user_team and p["id"] in user_board_ids and user_team not in schools:
            schools[-1] = user_team  # ensure the user is in the set
        interest = {}
        for s in schools:
            irng = make_rng(seed, year, "interest", p["name"], s)
            interest[s] = _initial_interest(p["region"], universe.get(s, {}).get("rating", 55),
                                            _conf_region(universe, s), irng)
        p["schools"] = interest
        p["committed_to"] = None
        p["commit_week"] = None
        p["signed"] = False

    state = {
        "year": year, "seed": seed, "user_team": user_team,
        "last_advanced_week": 0, "prospects": prospects,
    }
    _save(state)
    return state


# --- weekly progression ---------------------------------------------------
def _commit_prob(week: int, top_interest: float, weeks_total: int) -> float:
    if top_interest < 66:
        return 0.0
    timing = 0.06 + (week / max(1, weeks_total)) * 0.26
    strength = (top_interest - 66) / 34 * 0.5
    return min(0.9, timing + strength)


def advance(year: int, week: int, universe: dict[str, Any], weeks_total: int = 12) -> dict[str, Any]:
    """Progress every uncommitted prospect one week. Idempotent per week."""
    state = get(year)
    if not state or week <= state.get("last_advanced_week", 0):
        return state or {}

    seed = state["seed"]
    user_team = state.get("user_team")
    # The coach's interest in each prospect, after his hours/NIL spend.
    user_interest = budget.load(year).get("interest", {}) if user_team else {}

    signing = week >= weeks_total  # final week locks the class

    for p in state["prospects"]:
        if p["committed_to"]:
            p["signed"] = True
            continue
        schools = p["schools"]
        leader = max(schools, key=schools.get)
        for s in list(schools):
            rng = make_rng(seed, year, week, "drift", p["name"], s)
            drift = rng.gauss(0, 4) + (2.4 if s == leader else 0) + (universe.get(s, {}).get("rating", 55) - 60) * 0.06
            schools[s] = int(max(0, min(100, schools[s] + drift)))
        # Inject the coach's competitive interest (baseline fit + spend).
        if user_team and user_team in schools and p["id"] in user_interest:
            schools[user_team] = int(user_interest[p["id"]])

        leader = max(schools, key=schools.get)
        top = schools[leader]
        crng = make_rng(seed, year, week, "commit", p["name"])
        if signing or crng.random() < _commit_prob(week, top, weeks_total):
            p["committed_to"] = leader
            p["commit_week"] = week
            p["signed"] = signing

    state["last_advanced_week"] = week
    _save(state)
    return state


# --- views ----------------------------------------------------------------
def _leader_and_predicted(p: dict) -> tuple[str | None, str | None]:
    if not p["schools"]:
        return None, None
    leader = max(p["schools"], key=p["schools"].get)
    return leader, (p["committed_to"] or leader)


def national_list(year: int, universe: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Flat browsable list of every prospect for the national board UI.

    When the universe is supplied, the committed and leading schools are enriched
    with their abbreviation + ESPN id so the board can render logos.
    """
    state = get(year)
    if not state:
        return []
    universe = universe or {}

    def meta(school: str | None) -> dict[str, Any]:
        info = universe.get(school) if school else None
        return {"abbr": (info or {}).get("abbr"), "espn_id": (info or {}).get("espn_id")}

    out = []
    for p in state["prospects"]:
        leader, predicted = _leader_and_predicted(p)
        status = "Signed" if p["signed"] else ("Committed" if p["committed_to"] else "Uncommitted")
        cm, lm = meta(p["committed_to"]), meta(leader)
        out.append({
            "id": p["id"], "name": p["name"], "position": p["position"],
            "stars": p["stars"], "ovr": p["ovr"], "rating": p["rating"],
            "national_rank": p["national_rank"], "position_rank": p["position_rank"],
            "hometown": f"{p['city']}, {p['state']}", "state": p["state"],
            "height": p["height"], "weight": p["weight"],
            "expected_nil": p["expected_nil"], "dealbreaker": p["dealbreaker"],
            "status": status, "committed_to": p["committed_to"], "commit_week": p["commit_week"],
            "committed_abbr": cm["abbr"], "committed_espn_id": cm["espn_id"],
            "leader": leader, "leader_abbr": lm["abbr"], "leader_espn_id": lm["espn_id"],
            "interest_count": len(p["schools"]),
        })
    return out


def user_board(year: int) -> dict[str, list[dict[str, Any]]]:
    """The user's commits + targets, shaped for budget.py and the recruiting page."""
    state = get(year)
    if not state:
        return {"commits": [], "targets": []}
    user = state.get("user_team")
    commits: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    for p in state["prospects"]:
        if user not in p["schools"]:
            continue
        if p["committed_to"] and p["committed_to"] != user:
            continue  # lost him to another program; drop off the board
        leader, predicted = _leader_and_predicted(p)
        hometown = f"{p['city']}, {p['state']}"
        interest = int(p["schools"].get(user, 0))
        common = {
            "name": p["name"], "position": p["position"], "stars": p["stars"],
            "rating": p["rating"], "ovr": p["ovr"], "national_rank": p["national_rank"],
            "hometown": hometown, "expected_nil": p["expected_nil"],
            "dealbreaker": p["dealbreaker"], "interest": interest,
        }
        if p["committed_to"] == user:
            commits.append({**common, "status": "Enrolled" if p["signed"] else "Committed",
                            "stage": "Hard Commit"})
        else:
            targets.append({**common, "leader": leader, "predicted": predicted,
                            "visit": None, "stage": budget.stage_for_interest(interest)})
    commits.sort(key=lambda r: -r["stars"])
    targets.sort(key=lambda r: -r["interest"])
    return {"commits": commits, "targets": targets}


def class_rankings(year: int) -> dict[str, Any]:
    """National + conference class rank for the user, by committed talent."""
    state = get(year)
    if not state:
        return {"national": None, "conference": None}
    points: dict[str, float] = {}
    for p in state["prospects"]:
        if p["committed_to"]:
            points[p["committed_to"]] = points.get(p["committed_to"], 0) + p["ovr"] + p["stars"] * 6
    ranked = sorted(points, key=points.get, reverse=True)
    user = state.get("user_team")
    nat = ranked.index(user) + 1 if user in ranked else None
    return {"national": nat, "conference": None, "committed_points": points.get(user, 0)}
