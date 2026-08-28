"""Custom College Football Playoff format engine + per-dynasty format store.

The user can replace the default 12-team CFP with any format from 1 team (the
highest-ranked team is crowned, pre-BCS style) to 128 teams, with multi-tier
byes (single, double, triple), conference-champion auto-bids, bye selection
criteria, disqualification rules, the Notre Dame special-treatment toggle, and
per-round game sites (higher seed's stadium, a bowl tie-in, or a neutral site).

Research note (2026-07-06 survey of the real CFB27 dynasty save): the save
contains playoff STRUCTURES (a PlayoffBowlsInfo[] array, PlayoffBracketRequest
records, CFP round labels, and the New Year's Six bowl name table around offset
1.44MB) but no editable rule fields: no bracket size, auto-bid, bye, or seeding
configuration exists anywhere in the ~30MB payload (no NumPlayoffTeams,
BracketSize, AutoBid, or AtLarge tokens). The 12-team format is hardcoded in
game code, so a custom format cannot be pushed into the game's own UI. The
custom playoff therefore lives entirely in Dynasty+. The saveparse write seam
(backend/saveparse/container.encode) exists so playoff matchups can be patched
into the save's schedule region (big-endian u16 team-index pairs near 19.8MB)
once that region's write layout is fully reverse-engineered.

Bracket math: every team is given a weight of 2**byes (a team with one bye
covers two first-round slots, a double bye covers four, and so on). A format is
buildable exactly when the weights sum to a power of two. The bracket tree is
built by recursively splitting the seed list into two halves of equal weight,
assigning seeds best-first to the lighter half (ties alternate sides). For the
standard 12-team CFP this reproduces the real bracket exactly: 5v12 feeding 4,
8v9 feeding 1, 6v11 feeding 3, 7v10 feeding 2.
"""
from __future__ import annotations

import json
import math
from typing import Any

from . import config, dynasty_paths, school_names, school_sites

_SEED_FILE = config.DATA_DIR / "league_seed.json"


def _load_league_seed() -> list[dict[str, Any]]:
    """The checked-in FBS seed rows (data/league_seed.json), used to round out
    the projected selection pool with programs the save has not ranked yet.
    Empty list when the seed is absent."""
    if not _SEED_FILE.exists():
        return []
    try:
        rows = json.loads(_SEED_FILE.read_text(encoding="utf-8"))
        return rows if isinstance(rows, list) else rows.get("teams", [])
    except (OSError, ValueError):
        return []

NOTRE_DAME_ESPN_ID = 87

# Conferences that cannot produce a champion for auto-bid purposes.
_INDEPENDENT = {"FBS Independents", "Independent", "IND", None, ""}

# Bowl catalog. `asset` keys into /game-assets/bowls/<asset>.png (real game art
# extracted by scripts/extract_game_assets.py). The first six are the New
# Year's Six, the default playoff tie-ins. Order is prestige, biggest first:
# the engine assigns bowls down this list to the LATEST rounds first, so the
# marquee bowls land on the championship / semifinals, not the opening round.
BOWLS: list[dict[str, Any]] = [
    {"key": "rose", "name": "Rose Bowl", "venue": "Rose Bowl", "city": "Pasadena, CA", "asset": "rosebowl", "ny6": True},
    {"key": "sugar", "name": "Sugar Bowl", "venue": "Caesars Superdome", "city": "New Orleans, LA", "asset": "sugarbowl", "ny6": True},
    {"key": "orange", "name": "Orange Bowl", "venue": "Hard Rock Stadium", "city": "Miami Gardens, FL", "asset": "orangebowl", "ny6": True},
    {"key": "cotton", "name": "Cotton Bowl", "venue": "AT&T Stadium", "city": "Arlington, TX", "asset": "cottonbowl", "ny6": True},
    {"key": "fiesta", "name": "Fiesta Bowl", "venue": "State Farm Stadium", "city": "Glendale, AZ", "asset": "fiestabowl", "ny6": True},
    {"key": "peach", "name": "Peach Bowl", "venue": "Mercedes-Benz Stadium", "city": "Atlanta, GA", "asset": "peachbowl", "ny6": True},
    {"key": "citrus", "name": "Citrus Bowl", "venue": "Camping World Stadium", "city": "Orlando, FL", "asset": "citrusbowl"},
    {"key": "alamo", "name": "Alamo Bowl", "venue": "Alamodome", "city": "San Antonio, TX", "asset": "alamobowl"},
    {"key": "gator", "name": "Gator Bowl", "venue": "EverBank Stadium", "city": "Jacksonville, FL", "asset": "gatorbowl"},
    {"key": "holiday", "name": "Holiday Bowl", "venue": "Snapdragon Stadium", "city": "San Diego, CA", "asset": "holidaybowl"},
    {"key": "lasvegas", "name": "Las Vegas Bowl", "venue": "Allegiant Stadium", "city": "Las Vegas, NV", "asset": "lasvegasbowl"},
    {"key": "liberty", "name": "Liberty Bowl", "venue": "Simmons Bank Liberty Stadium", "city": "Memphis, TN", "asset": "libertybowl"},
    {"key": "musiccity", "name": "Music City Bowl", "venue": "Nissan Stadium", "city": "Nashville, TN", "asset": "musiccitybowl"},
    {"key": "poptarts", "name": "Pop-Tarts Bowl", "venue": "Camping World Stadium", "city": "Orlando, FL", "asset": "poptartsbowl"},
    {"key": "reliaquest", "name": "ReliaQuest Bowl", "venue": "Raymond James Stadium", "city": "Tampa, FL", "asset": "reliaquestbowl"},
    {"key": "sun", "name": "Sun Bowl", "venue": "Sun Bowl", "city": "El Paso, TX", "asset": "sunbowl"},
    {"key": "texas", "name": "Texas Bowl", "venue": "NRG Stadium", "city": "Houston, TX", "asset": "texasbowl"},
    {"key": "dukesmayo", "name": "Duke's Mayo Bowl", "venue": "Bank of America Stadium", "city": "Charlotte, NC", "asset": "dukesmayobowl"},
    {"key": "pinstripe", "name": "Pinstripe Bowl", "venue": "Yankee Stadium", "city": "Bronx, NY", "asset": "pinstripebowl"},
    {"key": "birmingham", "name": "Birmingham Bowl", "venue": "Protective Stadium", "city": "Birmingham, AL", "asset": "birminghambowl"},
    {"key": "military", "name": "Military Bowl", "venue": "Navy-Marine Corps Memorial Stadium", "city": "Annapolis, MD", "asset": "militarybowl"},
    {"key": "armedforces", "name": "Armed Forces Bowl", "venue": "Amon G. Carter Stadium", "city": "Fort Worth, TX", "asset": "armedforcesbowl"},
    {"key": "independence", "name": "Independence Bowl", "venue": "Independence Stadium", "city": "Shreveport, LA", "asset": "independencebowl"},
    {"key": "newmexico", "name": "New Mexico Bowl", "venue": "University Stadium", "city": "Albuquerque, NM", "asset": "newmexicobowl"},
    {"key": "bocaraton", "name": "Boca Raton Bowl", "venue": "FAU Stadium", "city": "Boca Raton, FL", "asset": "bocaratonbowl"},
    {"key": "frisco", "name": "Frisco Bowl", "venue": "Toyota Stadium", "city": "Frisco, TX", "asset": "friscobowl"},
    {"key": "hawaii", "name": "Hawaii Bowl", "venue": "Clarence T.C. Ching Complex", "city": "Honolulu, HI", "asset": "hawaiibowl"},
    {"key": "arizona", "name": "Arizona Bowl", "venue": "Arizona Stadium", "city": "Tucson, AZ", "asset": "arizonabowl"},
    {"key": "gasparilla", "name": "Gasparilla Bowl", "venue": "Raymond James Stadium", "city": "Tampa, FL", "asset": "gasparillabowl"},
    {"key": "fenway", "name": "Fenway Bowl", "venue": "Fenway Park", "city": "Boston, MA", "asset": "fenwaybowl"},
    {"key": "neworleans", "name": "New Orleans Bowl", "venue": "Caesars Superdome", "city": "New Orleans, LA", "asset": "neworleansbowl"},
    {"key": "idahopotato", "name": "Famous Idaho Potato Bowl", "venue": "Albertsons Stadium", "city": "Boise, ID", "asset": "famousidahopotatobowl"},
]

_BOWL_INDEX = {b["key"]: b for b in BOWLS}

# The shipped default is the real 2025-26 CFP: 12 teams, straight seeding, four
# single byes, five conference-champion auto-bids, first round on campus, the
# New Year's Six hosting the quarterfinals and semifinals.
DEFAULT_FORMAT: dict[str, Any] = {
    "teams": 12,
    "byes": [{"teams": 4, "rounds": 1}],
    "bye_selection": "seeding",
    "auto_bids": {"champions": 5},
    "disqualify": {
        "max_losses": None,
        "losing_conf_record": False,
        "rivalry_week_loss": False,
        "champions_only": False,
        "ranked_only": False,
    },
    # Per-conference field limits: a cap on how many teams one conference can send
    # (None = no cap) and a floor guaranteeing each conference a minimum number of
    # bids (0 = none). The floor counts a conference's champion toward its minimum.
    "conference_limits": {"max_per_conf": None, "min_per_conf": 0},
    "notre_dame_rule": True,
    # Reseeding: after every round the surviving teams re-pair by seed (the
    # best remaining seed plays the worst remaining, NFL style) instead of
    # following the fixed bracket tree. Off = the real CFP's fixed bracket.
    "reseed": False,
    "sites": {
        "rounds": [
            {"mode": "higher_seed", "games": []},
            # Quarterfinals and semifinals tie into bowls; the engine fills the
            # marquee bowls into the latest rounds first, so the semifinals draw
            # the Rose and Sugar and the quarterfinals the rest of the New Year's Six.
            {"mode": "bowls", "bowls": [], "games": []},
            {"mode": "bowls", "bowls": [], "games": []},
        ],
        # The title game is its own neutral site by default; set mode "bowls"
        # (with an optional bowl) to make a bowl host it, e.g. the Rose Bowl.
        "championship": {"mode": "neutral", "bowl": None,
                         "venue": "Mercedes-Benz Stadium", "city": "Atlanta, GA"},
    },
}


class BracketError(ValueError):
    """A format that cannot be built into a closed bracket."""


# ---------------------------------------------------------------------------
# Format store (per dynasty)
# ---------------------------------------------------------------------------

def _store_path():
    return dynasty_paths.sub("playoff") / "format.json"


def get_format() -> dict[str, Any]:
    """The active format for the current dynasty (saved edits or the default)."""
    path = _store_path()
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            return normalize_format(saved)
        except (OSError, ValueError):
            pass
    return normalize_format(DEFAULT_FORMAT)


def set_format(fmt: dict[str, Any]) -> dict[str, Any]:
    """Validate, normalize, and persist a format. Raises BracketError if invalid."""
    normalized = normalize_format(fmt)
    problems = validate_format(normalized)
    if problems:
        raise BracketError("; ".join(problems))
    _store_path().write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    return normalized


def reset_format() -> dict[str, Any]:
    path = _store_path()
    if path.exists():
        path.unlink()
    return normalize_format(DEFAULT_FORMAT)


def is_customized() -> bool:
    return _store_path().exists()


# ---------------------------------------------------------------------------
# Normalization + validation
# ---------------------------------------------------------------------------

def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_format(fmt: dict[str, Any] | None) -> dict[str, Any]:
    """Fill defaults and coerce types. Never raises; validate_format reports."""
    fmt = fmt or {}
    out: dict[str, Any] = {}
    out["teams"] = _as_int(fmt.get("teams"), 12)

    tiers: dict[int, int] = {}
    for tier in fmt.get("byes") or []:
        rounds = _as_int((tier or {}).get("rounds"), 0)
        teams = _as_int((tier or {}).get("teams"), 0)
        if rounds > 0 and teams > 0:
            tiers[rounds] = tiers.get(rounds, 0) + teams
    # If every team has a bye the early rounds are empty; shift everyone down.
    if tiers and sum(tiers.values()) >= out["teams"]:
        shift = min(tiers.keys())
        tiers = {r - shift: t for r, t in tiers.items() if r - shift > 0}
    out["byes"] = [{"rounds": r, "teams": t} for r, t in sorted(tiers.items(), reverse=True)]

    bye_selection = fmt.get("bye_selection")
    out["bye_selection"] = bye_selection if bye_selection in ("seeding", "champs") else "seeding"

    out["auto_bids"] = {"champions": max(0, _as_int((fmt.get("auto_bids") or {}).get("champions"), 0))}

    dq_in = fmt.get("disqualify") or {}
    max_losses = dq_in.get("max_losses")
    out["disqualify"] = {
        "max_losses": _as_int(max_losses) if max_losses not in (None, "") else None,
        "losing_conf_record": bool(dq_in.get("losing_conf_record")),
        "rivalry_week_loss": bool(dq_in.get("rivalry_week_loss")),
        "champions_only": bool(dq_in.get("champions_only")),
        "ranked_only": bool(dq_in.get("ranked_only")),
    }

    cl_in = fmt.get("conference_limits") or {}
    max_pc = cl_in.get("max_per_conf")
    out["conference_limits"] = {
        "max_per_conf": _as_int(max_pc) if max_pc not in (None, "") else None,
        "min_per_conf": max(0, _as_int(cl_in.get("min_per_conf"), 0)),
    }

    out["notre_dame_rule"] = bool(fmt.get("notre_dame_rule", True))
    out["reseed"] = bool(fmt.get("reseed", False))

    def _stadium(value: Any) -> int | None:
        """A neutral site's save-stadium id (the stable index into the save's
        stadium table, see saveparse/stadiums.py); None = label-only site."""
        idx = _as_int(value, -1) if value not in (None, "") else -1
        return idx if 0 <= idx < 400 else None

    sites_in = fmt.get("sites") or {}
    rounds_cfg = []
    for rc in sites_in.get("rounds") or []:
        rc = rc or {}
        mode = rc.get("mode")
        rounds_cfg.append({
            "mode": mode if mode in ("higher_seed", "bowls", "neutral") else "bowls",
            "bowls": [k for k in (rc.get("bowls") or []) if k in _BOWL_INDEX],
            "venue": (rc.get("venue") or "").strip() or None,
            "city": (rc.get("city") or "").strip() or None,
            "stadium": _stadium(rc.get("stadium")),
            "games": [
                None if not g else {
                    "mode": g.get("mode") if g.get("mode") in ("higher_seed", "bowls", "neutral") else None,
                    "bowl": g.get("bowl") if g.get("bowl") in _BOWL_INDEX else None,
                    "venue": (g.get("venue") or "").strip() or None,
                    "city": (g.get("city") or "").strip() or None,
                    "stadium": _stadium(g.get("stadium")),
                }
                for g in (rc.get("games") or [])
            ],
        })
    champ = sites_in.get("championship") or {}
    champ_mode = champ.get("mode")
    out["sites"] = {
        "rounds": rounds_cfg,
        "championship": {
            "mode": champ_mode if champ_mode in ("neutral", "bowls") else "neutral",
            "bowl": champ.get("bowl") if champ.get("bowl") in _BOWL_INDEX else None,
            "venue": (champ.get("venue") or "").strip() or DEFAULT_FORMAT["sites"]["championship"]["venue"],
            "city": (champ.get("city") or "").strip() or DEFAULT_FORMAT["sites"]["championship"]["city"],
            "stadium": _stadium(champ.get("stadium")),
        },
    }
    return out


def _weights(teams: int, tiers: list[dict[str, int]]) -> list[int]:
    """Per-seed weights, best seed first. Deeper byes always go to better seeds."""
    weights: list[int] = []
    for tier in sorted(tiers, key=lambda t: -t["rounds"]):
        weights.extend([2 ** tier["rounds"]] * tier["teams"])
    weights.extend([1] * (teams - len(weights)))
    return weights


def validate_format(fmt: dict[str, Any]) -> list[str]:
    """Human-readable problems; empty means buildable."""
    problems: list[str] = []
    n = fmt.get("teams", 0)
    if not 1 <= n <= 128:
        problems.append("Field size must be between 1 and 128 teams")
        return problems

    cl = fmt.get("conference_limits") or {}
    max_pc = cl.get("max_per_conf")
    min_pc = cl.get("min_per_conf") or 0
    if max_pc is not None and max_pc < 1:
        problems.append("Max teams per conference must be at least 1")
    if min_pc and max_pc is not None and min_pc > max_pc:
        problems.append("Min teams per conference cannot exceed the max per conference")
    if min_pc and min_pc > n:
        problems.append("Min teams per conference cannot exceed the field size")

    tiers = fmt.get("byes") or []
    bye_teams = sum(t["teams"] for t in tiers)
    if n <= 2 and bye_teams:
        problems.append("A field of 1 or 2 teams cannot have byes")
        return problems
    if bye_teams >= n and n > 1:
        problems.append("At least one team must play in the opening round")
        return problems
    for tier in tiers:
        if tier["rounds"] > 6:
            problems.append("Byes deeper than 6 rounds are not supported")
            return problems

    if n == 1:
        return problems

    weights = _weights(n, tiers)
    total = sum(weights)
    if total & (total - 1):
        lower = 2 ** int(math.floor(math.log2(total)))
        upper = lower * 2
        problems.append(
            f"This bye structure does not close into a bracket: the field covers {total} "
            f"opening slots, which must be a power of two (nearest are {lower} and {upper}). "
            "Adjust the field size or the number of teams on byes."
        )
        return problems
    try:
        _build_tree(weights)
    except BracketError:
        problems.append("This combination of byes cannot be arranged into a bracket")
    return problems


def suggest_byes(teams: int) -> list[dict[str, int]]:
    """The standard bye tier for a field size: byes for the gap to the next
    power of two (12 teams -> 4 single byes; 24 -> 8; exact powers -> none)."""
    if teams <= 2:
        return []
    full = 2 ** math.ceil(math.log2(teams))
    gap = full - teams
    return [{"rounds": 1, "teams": gap}] if gap else []


# ---------------------------------------------------------------------------
# Bracket structure
# ---------------------------------------------------------------------------

def _build_tree(weights: list[int]) -> dict[str, Any] | None:
    """Build the bracket tree for per-seed weights (best seed first).

    Returns the root node: internal nodes are {"a": node, "b": node, "size": w},
    leaves are {"seed": i, "size": w}. None for a single-team field.
    """
    entries = [{"seed": i + 1, "size": w} for i, w in enumerate(weights)]
    if len(entries) == 1:
        return None
    total = sum(e["size"] for e in entries)
    return _split(entries, total)


def _split(entries: list[dict[str, Any]], size: int) -> dict[str, Any]:
    if len(entries) == 1:
        if entries[0]["size"] != size:
            raise BracketError("bye structure does not fill its bracket region")
        return entries[0]
    half = size // 2
    a: list[dict[str, Any]] = []
    b: list[dict[str, Any]] = []
    wa = wb = 0
    toggle = True  # ties alternate sides, starting with the top half
    for e in entries:
        if wa == wb:
            pick_a = toggle
            toggle = not toggle
        else:
            pick_a = wa < wb
        if pick_a and wa + e["size"] > half:
            pick_a = False
        elif not pick_a and wb + e["size"] > half:
            pick_a = True
        if pick_a:
            a.append(e)
            wa += e["size"]
        else:
            b.append(e)
            wb += e["size"]
    if wa != half or wb != half or not a or not b:
        raise BracketError("bye structure does not split into a balanced bracket")
    return {"a": _split(a, half), "b": _split(b, half), "size": size}


_ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh"]


def _round_names(games_by_round: dict[int, list], total_rounds: int) -> dict[int, str]:
    names: dict[int, str] = {}
    early = 0
    for r in sorted(games_by_round.keys()):
        count = len(games_by_round[r])
        if r == total_rounds:
            names[r] = "National Championship"
        elif r == total_rounds - 1 and count == 2:
            names[r] = "Semifinals"
        elif r == total_rounds - 2 and count == 4:
            names[r] = "Quarterfinals"
        else:
            names[r] = f"{_ORDINALS[min(early, len(_ORDINALS) - 1)]} Round"
            early += 1
    return names


def bracket_structure(fmt: dict[str, Any]) -> dict[str, Any]:
    """The seed-level structure of a format, independent of any rankings.

    Returns {"rounds": [{"round", "name", "games": [{"id", "slots": [slot, slot]}]}],
    "seed_entry_round": {seed: round}} where a slot is {"type": "seed", "seed": n}
    or {"type": "winner", "game": "<id>"}.
    """
    n = fmt["teams"]
    if n == 1:
        return {"rounds": [], "seed_entry_round": {1: 0}, "total_rounds": 0}
    weights = _weights(n, fmt.get("byes") or [])
    root = _build_tree(weights)
    total_rounds = int(math.log2(sum(weights)))

    games_by_round: dict[int, list[dict[str, Any]]] = {}
    seed_entry: dict[int, int] = {}

    def collect(node: dict[str, Any]) -> dict[str, Any]:
        if "seed" in node:
            return {"type": "seed", "seed": node["seed"]}
        r = int(math.log2(node["size"]))
        slot_a = collect(node["a"])
        slot_b = collect(node["b"])
        game = {"round": r, "slots": [slot_a, slot_b]}
        games_by_round.setdefault(r, []).append(game)
        return {"type": "winner", "game": game}

    collect(root)

    # Assign ids in round order, top to bottom (DFS already ordered each round).
    for r in sorted(games_by_round.keys()):
        for i, game in enumerate(games_by_round[r]):
            game["id"] = f"R{r}G{i + 1}"
    for r, games in games_by_round.items():
        for game in games:
            for slot in game["slots"]:
                if slot["type"] == "winner":
                    slot["game"] = slot["game"]["id"]
                elif slot["type"] == "seed":
                    seed_entry[slot["seed"]] = r

    names = _round_names(games_by_round, total_rounds)
    rounds = [
        {"round": r, "name": names[r], "games": games_by_round[r]}
        for r in sorted(games_by_round.keys())
    ]
    return {"rounds": rounds, "seed_entry_round": seed_entry, "total_rounds": total_rounds}


# ---------------------------------------------------------------------------
# Selection: rankings pool, champions, disqualification, auto-bids
# ---------------------------------------------------------------------------

def _parse_record(record: str | None) -> tuple[int, int] | None:
    if not record or not isinstance(record, str):
        return None
    parts = record.split("-")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _team_directory(dynasty: dict) -> dict[Any, dict[str, Any]]:
    """espn_id (and name) -> {conference, abbr, ...} from the save's team list,
    falling back to the shared FBS league seed."""
    directory: dict[Any, dict[str, Any]] = {}

    def add(row: dict[str, Any], overwrite: bool = False) -> None:
        conf = row.get("conference")
        abbr = row.get("abbr") or row.get("abbreviation")
        name = row.get("name") or row.get("school")
        rec = {"conference": conf, "abbr": abbr, "name": name, "espn_id": row.get("espn_id"),
               "prestige": row.get("prestige"), "base_rating": row.get("base_rating"),
               "color": row.get("color")}
        merged = {k: v for k, v in rec.items() if v is not None}
        for key in (row.get("espn_id"), name):
            if key is None or key == "":
                continue
            if overwrite and key in directory:
                # the save's row updates what it knows (conference after a
                # realignment, the record's abbr) but keeps the seed's
                # strength fields, which the save does not carry
                directory[key] = {**directory[key], **merged}
            else:
                directory.setdefault(key, rec)

    for row in _load_league_seed():
        add(row)
    # The save's own team list wins over the seed (its alignment reflects the
    # dynasty's actual conferences, including in-game realignment).
    for row in dynasty.get("all_teams") or []:
        add(dict(row), overwrite=True)
    return directory


def selection_pool(dynasty: dict, base_order: list[dict] | None = None) -> list[dict[str, Any]]:
    """Every known team in committee-ranking order, annotated with conference.

    base_order (e.g. the committee's synthesized ranking) heads the pool; the
    AP poll fills in ranked teams it misses; every other known FBS team follows,
    ordered by record when known, then name.
    """
    national = dynasty.get("national") or {}
    directory = _team_directory(dynasty)

    # Team colors drive the bracket tile art; the ESPN-backed directory has
    # them when its disk cache is warm (the app fetches it on startup).
    colors: dict[str, str] = {}
    try:
        from . import teams as team_directory
        for name, rec in team_directory.get_all_teams().items():
            if rec.get("color"):
                colors[name] = rec["color"]
    except Exception:
        pass

    pool: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(entry: dict[str, Any], ranked: bool) -> None:
        name = entry.get("team") or entry.get("name") or entry.get("school")
        if not name or name in seen:
            return
        seen.add(name)
        info = directory.get(entry.get("espn_id")) or directory.get(name) or {}
        espn_id = entry.get("espn_id", info.get("espn_id"))
        row = {
            "team": name,
            "short": school_names.short_name(espn_id, name),
            "abbr": entry.get("abbr") or entry.get("abbreviation") or info.get("abbr") or name[:4].upper(),
            "espn_id": espn_id,
            "record": entry.get("record") or "",
            "conference": entry.get("conference") or info.get("conference"),
            "color": entry.get("color") or info.get("color") or colors.get(name),
            "ranked": ranked,
        }
        if entry.get("conf_record"):
            row["conf_record"] = entry["conf_record"]
        pool.append(row)

    for t in base_order or []:
        add(dict(t), ranked=True)
    for key in ("cfp_top25", "cfp_top12", "ap_top25"):
        for t in national.get(key) or []:
            add(dict(t), ranked=True)

    # Conference standings carry conference records for teams we know about.
    conf_records: dict[str, str] = {}
    for row in dynasty.get("conference_standings") or []:
        team_name = row.get("team")
        if team_name:
            conf_records[team_name] = row.get("conf_record") or ""
            add(dict(row, record=row.get("overall")), ranked=False)

    unranked: list[dict[str, Any]] = []
    for row in dynasty.get("all_teams") or []:
        name = row.get("name") or row.get("school")
        if name and name not in seen:
            unranked.append(dict(row))
    for row in _load_league_seed():
        if row.get("name") not in seen and not any(u.get("name") == row.get("name") for u in unranked):
            unranked.append(dict(row))

    def sort_key(row: dict[str, Any]):
        """The save's own full national ranking wins when parsed (every team
        carries one, not just the top 25); then best record; teams with
        neither fall back to program strength from the league seed so the
        projected pool reads like a plausible poll, not an alphabet."""
        rank = row.get("rank")
        if isinstance(rank, int) and rank > 0:
            return (-1, rank, 0, 0, "")
        rec = _parse_record(row.get("record"))
        name = row.get("name") or row.get("school") or ""
        info = directory.get(row.get("espn_id")) or directory.get(name) or {}
        strength = (info.get("prestige") or 0) * 100 + (info.get("base_rating") or 0)
        if rec:
            wins, losses = rec
            pct = wins / max(1, wins + losses)
            return (0, -pct, -wins, -strength, name)
        return (1, 0.0, 0, -strength, name)

    for row in sorted(unranked, key=sort_key):
        add(row, ranked=False)

    # When the save exposes its own full national ranking (every FBS team
    # carries a CFP-committee rank, not just the top 25), that ordering is
    # authoritative for the ENTIRE pool, so a bracket bigger than 25 teams
    # seeds off the game's real pecking order all the way down rather than a
    # record heuristic. Stable so teams the save leaves unranked (FCS
    # placeholders) keep their record-based tail position.
    full_rank: dict[str, int] = {}
    for row in dynasty.get("all_teams") or []:
        nm = row.get("name") or row.get("school")
        rk = row.get("rank")
        if nm and isinstance(rk, int) and rk > 0:
            full_rank[nm] = rk
    if full_rank:
        pool.sort(key=lambda e: (0, full_rank[e["team"]]) if e["team"] in full_rank else (1, 0))

    for i, entry in enumerate(pool):
        entry["rank"] = i + 1
        if entry["team"] in conf_records:
            entry["conf_record"] = conf_records[entry["team"]]
    return pool


def _projected_champions(pool: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """conference -> its best-ranked team (the PROJECTED champion)."""
    champs: dict[str, dict[str, Any]] = {}
    for entry in pool:
        conf = entry.get("conference")
        if conf in _INDEPENDENT:
            continue
        if conf not in champs:
            champs[conf] = entry
    return champs


def _champions(dynasty: dict, pool: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """conference -> its champion's pool entry.

    Before championship week the best-ranked team stands in as the projected
    champion. Once the save's conference championship games are official the
    ACTUAL winners (dynasty["conference_champions"], stamped by the save
    parser) override the projection, so an upset CCG winner gets the champion
    auto-bid, not the higher-ranked team it beat."""
    champs = _projected_champions(pool)
    actual = dynasty.get("conference_champions") or {}
    if actual:
        by_name = {e.get("team"): e for e in pool}
        for conf, team in actual.items():
            entry = by_name.get(team)
            if entry is None:
                continue
            # the save's alignment is authoritative: correct a pool entry
            # whose conference label came from a stale seed lookup, so the
            # champ marking and per-conference caps see the real conference
            if entry.get("conference") != conf:
                entry["conference"] = conf
            champs[conf] = entry
    return champs


def _is_notre_dame(entry: dict[str, Any]) -> bool:
    if entry.get("espn_id") == NOTRE_DAME_ESPN_ID:
        return True
    return "notre dame" in (entry.get("team") or "").lower()


def _rivalry_week_loss(dynasty: dict, entry: dict[str, Any]) -> bool | None:
    """True/False when we can tell, None when unknown.

    On a real save the whole league's rivalry-week outcomes are parsed
    (`schedule.rivalry_week_losers`, full team names, present once the
    regular season is official). The last-result heuristic remains as the
    fallback for the user's team on mock/old data."""
    losers = (dynasty.get("schedule") or {}).get("rivalry_week_losers")
    if losers is not None:
        name = entry.get("team") or entry.get("name") or ""
        return name in losers
    team = dynasty.get("team") or {}
    if entry.get("espn_id") != team.get("espn_id"):
        return None
    results = (dynasty.get("schedule") or {}).get("recent_results") or []
    season = dynasty.get("season") or {}
    if season.get("phase") not in ("conf_championship", "bowls", "playoff", "offseason"):
        return None  # rivalry week has not happened yet
    regular = [r for r in results if r.get("result")]
    if not regular:
        return None
    return regular[-1].get("result") == "L"


def _disqualify_reason(dynasty: dict, entry: dict[str, Any], dq: dict[str, Any],
                       champs: dict[str, dict[str, Any]]) -> str | None:
    rec = _parse_record(entry.get("record"))
    if dq.get("max_losses") is not None and rec and rec[1] > dq["max_losses"]:
        return f"More than {dq['max_losses']} losses"
    if dq.get("losing_conf_record"):
        conf_rec = _parse_record(entry.get("conf_record"))
        if conf_rec and conf_rec[0] < conf_rec[1]:
            return "Losing conference record"
    if dq.get("rivalry_week_loss") and _rivalry_week_loss(dynasty, entry) is True:
        return "Lost on rivalry week"
    if dq.get("ranked_only") and entry.get("rank", 99) > 25:
        return "Outside the committee top 25"
    if dq.get("champions_only"):
        conf = entry.get("conference")
        champ = champs.get(conf)
        if not champ or champ.get("team") != entry.get("team"):
            return "Not a conference champion"
    return None


def select_field(dynasty: dict, fmt: dict[str, Any],
                 base_order: list[dict] | None = None) -> dict[str, Any]:
    """Pick and seed the field for a format from the current rankings."""
    n = fmt["teams"]
    pool = selection_pool(dynasty, base_order)
    champs = _champions(dynasty, pool)
    dq_cfg = fmt.get("disqualify") or {}
    limits = fmt.get("conference_limits") or {}
    max_pc = limits.get("max_per_conf")
    min_pc = limits.get("min_per_conf") or 0
    conf_count: dict[str, int] = {}

    disqualified: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    for entry in pool:
        reason = _disqualify_reason(dynasty, entry, dq_cfg, champs)
        if reason:
            disqualified.append(dict(entry, reason=reason))
        else:
            eligible.append(entry)

    notes: list[str] = []
    selected: list[dict[str, Any]] = []
    picked: set[str] = set()

    def pick(entry: dict[str, Any], **tags: Any) -> None:
        if entry["team"] in picked or len(selected) >= n:
            return
        cf = entry.get("conference")
        # A per-conference cap blocks further teams once a (known) conference is
        # full. A conference champion is always its conference's first pick, so a
        # cap of 1 or more never strands one; teams with no known conference are
        # never capped.
        if max_pc is not None and cf and conf_count.get(cf, 0) >= max_pc:
            return
        picked.add(entry["team"])
        if cf:
            conf_count[cf] = conf_count.get(cf, 0) + 1
        selected.append(dict(entry, **tags))

    # Conference-champion auto-bids: the top-ranked champions get in regardless
    # of their ranking (unless a disqualification rule removes them).
    auto_n = (fmt.get("auto_bids") or {}).get("champions", 0)
    if auto_n:
        eligible_champs = [e for e in eligible
                           if champs.get(e.get("conference"), {}).get("team") == e["team"]]
        for entry in eligible_champs[:auto_n]:
            pick(entry, auto_bid=True, champ=True)

    # The Notre Dame rule: when on, an eligible Notre Dame ranked inside the
    # field size is guaranteed a bid (the independent's version of an auto-bid).
    if fmt.get("notre_dame_rule"):
        nd = next((e for e in eligible if _is_notre_dame(e)), None)
        if nd and nd.get("rank", 999) <= n:
            pick(nd, nd_rule=True)
            if nd["team"] in picked:
                notes.append("Notre Dame is guaranteed a bid under its independent access rule")

    # Minimum bids per conference: guarantee each conference its best eligible
    # teams up to the floor (a champion already picked above counts toward it).
    # Conferences are served in order of their best remaining team's rank, so the
    # strongest leagues fill first if the field runs out of room.
    if min_pc:
        by_conf: dict[str, list[dict[str, Any]]] = {}
        for e in eligible:
            cf = e.get("conference")
            if cf:
                by_conf.setdefault(cf, []).append(e)
        conf_order = sorted(by_conf, key=lambda cf: min(x.get("rank", 999) for x in by_conf[cf]))
        served = False
        for cf in conf_order:
            for e in sorted(by_conf[cf], key=lambda x: x.get("rank", 999)):
                if conf_count.get(cf, 0) >= min_pc or len(selected) >= n:
                    break
                before = len(selected)
                pick(e, conf_min=True)
                served = served or len(selected) > before
        if served:
            notes.append(
                f"Each conference is guaranteed up to {min_pc} bid{'s' if min_pc != 1 else ''}")

    # At-large: best remaining by committee rank.
    for entry in eligible:
        if len(selected) >= n:
            break
        pick(entry)

    if len(selected) < n:
        notes.append(f"Only {len(selected)} eligible teams are known; the field is short of {n}")

    # Mark champions in the selected field.
    for entry in selected:
        if champs.get(entry.get("conference"), {}).get("team") == entry["team"]:
            entry["champ"] = True

    # Seeding order: straight by committee rank, or promote champions into the
    # bye seeds first (the 2024-style bye rule).
    order = sorted(selected, key=lambda e: e["rank"])
    bye_slots = sum(t["teams"] for t in fmt.get("byes") or [])
    if bye_slots and fmt.get("bye_selection") == "champs":
        champ_rows = [e for e in order if e.get("champ") and not _is_notre_dame(e)][:bye_slots]
        promoted = {e["team"] for e in champ_rows}
        rest = [e for e in order if e["team"] not in promoted]
        order = champ_rows + rest
        if promoted:
            notes.append("Bye seeds are reserved for the top-ranked conference champions")

    seeds = [dict(e, seed=i + 1) for i, e in enumerate(order)]

    field_names = {e["team"] for e in seeds}
    cutoff_rank = max((e["rank"] for e in seeds), default=0)
    first_out = [e for e in eligible if e["team"] not in field_names][:4]
    excluded = [d for d in disqualified if d["rank"] <= cutoff_rank + 4]

    return {
        "seeds": seeds,
        "auto_bids": [e for e in seeds if e.get("auto_bid")],
        "first_out": first_out,
        "excluded": excluded,
        "notes": notes,
        "pool_size": len(pool),
    }


# ---------------------------------------------------------------------------
# Sites + final bracket assembly
# ---------------------------------------------------------------------------

def _bowl_payload(key: str | None) -> dict[str, Any] | None:
    bowl = _BOWL_INDEX.get(key or "")
    if not bowl:
        return None
    return {"key": bowl["key"], "name": bowl["name"], "venue": bowl["venue"],
            "city": bowl["city"], "asset": bowl["asset"]}


def _default_round_mode(round_index: int) -> str:
    return "higher_seed" if round_index == 0 else "bowls"


def _assign_bowls(structure: dict[str, Any], fmt: dict[str, Any],
                  champ_cfg: dict[str, Any]) -> dict[str, str]:
    """Assign a bowl to every game hosted by a bowl, biggest bowl to the latest
    round. Returns {game_id: bowl_key}.

    The New Year's Six and every other bowl are ranked by prestige (their order
    in BOWLS). Games that need a bowl are collected from the LATEST round back to
    the earliest (the championship first when it is bowl-hosted, then the
    semifinals, then the quarterfinals, and so on), so the marquee bowls land on
    the biggest games. Explicit choices (a per-game override or a per-round bowl
    list) are honored and reserved before the rest auto-fill from the pool.
    """
    rounds = structure["rounds"]
    total_rounds = structure["total_rounds"]
    sites_cfg = (fmt.get("sites") or {}).get("rounds") or []

    needing: list[tuple[str, str | None]] = []  # (game_id, explicit key), latest first
    for round_pos in reversed(range(len(rounds))):
        rnd = rounds[round_pos]
        if rnd["round"] == total_rounds:
            if champ_cfg.get("mode") == "bowls":
                needing.append((rnd["games"][0]["id"], champ_cfg.get("bowl")))
            continue
        cfg = sites_cfg[round_pos] if round_pos < len(sites_cfg) else {}
        round_mode = cfg.get("mode") or _default_round_mode(round_pos)
        round_bowls = cfg.get("bowls") or []
        games_cfg = cfg.get("games") or []
        for i, game in enumerate(rnd["games"]):
            override = games_cfg[i] if i < len(games_cfg) else None
            game_mode = (override or {}).get("mode") or round_mode
            if game_mode != "bowls":
                continue  # campus / neutral games take no bowl
            explicit = None
            if override and override.get("bowl"):
                explicit = override["bowl"]
            elif i < len(round_bowls):
                explicit = round_bowls[i]
            needing.append((game["id"], explicit))

    assigned: dict[str, str] = {}
    used: set[str] = set()
    for gid, explicit in needing:
        if explicit and explicit in _BOWL_INDEX and explicit not in used:
            assigned[gid] = explicit
            used.add(explicit)
    pool = [b["key"] for b in BOWLS if b["key"] not in used]
    pi = 0
    for gid, _explicit in needing:
        if gid in assigned:
            continue
        if pi < len(pool):
            assigned[gid] = pool[pi]
            pi += 1
    return assigned


def _assign_site(game: dict[str, Any], cfg: dict[str, Any], override: dict[str, Any] | None,
                 bowl_key: str | None, champ_cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve one game's site from the round config and optional per-game override.

    `bowl_key` is the bowl the global assignment gave this game (or None). The
    championship can itself be bowl-hosted (champ_cfg mode "bowls"), which keeps
    the title-game framing while showing the bowl's mark and venue.
    """
    if champ_cfg is not None:
        if champ_cfg.get("mode") == "bowls":
            bowl = _bowl_payload(bowl_key or champ_cfg.get("bowl"))
            if bowl:
                return {"type": "championship", "venue": bowl["venue"], "city": bowl["city"],
                        "bowl": bowl, "host_espn_id": None}
        return {"type": "championship", "venue": champ_cfg["venue"], "city": champ_cfg["city"],
                "bowl": None, "host_espn_id": None, "stadium": champ_cfg.get("stadium")}
    mode = (override or {}).get("mode") or cfg["mode"]
    if mode == "higher_seed":
        home = game["slots"][0]
        host = home if home.get("type") == "team" else None
        return {
            "type": "campus",
            "venue": f"{host['team']}" if host else "Higher seed's stadium",
            "city": (school_sites.campus_city(host.get("espn_id")) if host else None) or "Campus site",
            "bowl": None,
            "host_espn_id": host.get("espn_id") if host else None,
        }
    if mode == "neutral":
        venue = (override or {}).get("venue") or cfg.get("venue") or "Neutral site"
        city = (override or {}).get("city") or cfg.get("city") or ""
        stadium = (override or {}).get("stadium")
        if stadium is None:
            stadium = cfg.get("stadium")
        return {"type": "neutral", "venue": venue, "city": city, "bowl": None,
                "host_espn_id": None, "stadium": stadium}
    # bowls
    bowl = _bowl_payload(bowl_key)
    if not bowl:
        return {"type": "neutral", "venue": "Neutral site", "city": "", "bowl": None, "host_espn_id": None}
    return {"type": "bowl", "venue": bowl["venue"], "city": bowl["city"], "bowl": bowl,
            "host_espn_id": None}


def build_bracket(dynasty: dict, fmt: dict[str, Any] | None = None,
                  base_order: list[dict] | None = None) -> dict[str, Any]:
    """The full bracket JSON for a dynasty's current rankings and a format."""
    fmt = normalize_format(fmt) if fmt is not None else get_format()
    problems = validate_format(fmt)
    if problems:
        raise BracketError("; ".join(problems))

    selection = select_field(dynasty, fmt, base_order)
    seeds = selection["seeds"]
    seed_map = {s["seed"]: s for s in seeds}
    n = fmt["teams"]

    if n == 1:
        champion = seeds[0] if seeds else None
        return {
            "format": fmt,
            "field_size": 1,
            "customized": is_customized(),
            "rounds": [],
            "seeds": seeds,
            "byes": [],
            "selection": {k: selection[k] for k in ("auto_bids", "first_out", "excluded", "notes", "pool_size")},
            "champion": champion,
            "champion_note": "With a one-team field the top-ranked team is crowned champion outright, "
                             "as in the pre-BCS poll era.",
        }

    structure = bracket_structure(fmt)
    total_rounds = structure["total_rounds"]
    sites_cfg = (fmt.get("sites") or {}).get("rounds") or []
    champ_cfg = (fmt.get("sites") or {}).get("championship") or DEFAULT_FORMAT["sites"]["championship"]

    # Assign bowls once, globally: biggest bowls to the latest rounds.
    bowl_for = _assign_bowls(structure, fmt, champ_cfg)

    # RESEEDING: matchups re-pair by seed after every round, so later rounds
    # cannot be drawn as a fixed tree. Each seed records the round it enters
    # (fill_reseeded_rounds pairs a round's entrants once the previous round
    # is final); the opening round pairs its entrants best against worst, and
    # every later slot is a labeled placeholder until the reseed resolves it.
    reseed = bool(fmt.get("reseed"))
    first_round = structure["rounds"][0]["round"] if structure["rounds"] else 0
    if reseed:
        for s in seeds:
            s["entry_round"] = structure["seed_entry_round"].get(s["seed"], first_round)

    rounds_out: list[dict[str, Any]] = []
    game_labels: dict[str, str] = {}

    for round_pos, rnd in enumerate(structure["rounds"]):
        r = rnd["round"]
        is_final = r == total_rounds
        cfg = sites_cfg[round_pos] if round_pos < len(sites_cfg) else {}
        cfg = {
            "mode": cfg.get("mode") or _default_round_mode(round_pos),
            "bowls": list(cfg.get("bowls") or []),
            "venue": cfg.get("venue"),
            "city": cfg.get("city"),
            "stadium": cfg.get("stadium"),
            "games": cfg.get("games") or [],
        }
        reseed_pairs: list[tuple[int, int]] = []
        if reseed and round_pos == 0:
            entrants = sorted(sn for sn, er in structure["seed_entry_round"].items()
                              if er == r)
            reseed_pairs = [(entrants[i], entrants[len(entrants) - 1 - i])
                            for i in range(len(rnd["games"]))]

        games_out = []
        for i, game in enumerate(rnd["games"]):
            if reseed:
                if round_pos == 0:
                    slots = []
                    for sn in reseed_pairs[i]:
                        team = seed_map.get(sn)
                        if team:
                            slots.append(dict(team, type="team"))
                        else:
                            slots.append({"type": "tbd", "label": f"Seed {sn}", "seed": sn})
                else:
                    # slot k of game i holds the round's (i+1)-th best entrant
                    # on top and the mirrored worst on the bottom, by seed
                    n_slots = 2 * len(rnd["games"])
                    slots = [
                        {"type": "reseed", "label": f"No. {i + 1} seed left"},
                        {"type": "reseed", "label": f"No. {n_slots - i} seed left"},
                    ]
            else:
                slots = []
                for slot in game["slots"]:
                    if slot["type"] == "seed":
                        team = seed_map.get(slot["seed"])
                        if team:
                            slots.append(dict(team, type="team"))
                        else:
                            slots.append({"type": "tbd", "label": f"Seed {slot['seed']}", "seed": slot["seed"]})
                    else:
                        slots.append({"type": "winner", "game": slot["game"],
                                      "label": game_labels.get(slot["game"], "Winner")})
            override = cfg["games"][i] if i < len(cfg["games"]) else None
            resolved = {"slots": slots}
            site = _assign_site(resolved, cfg, override,
                                bowl_for.get(game["id"]), champ_cfg if is_final else None)
            game_id = game["id"]
            label = site["bowl"]["name"] if site.get("bowl") else f"{rnd['name']}"
            game_labels[game_id] = f"Winner, {label}" if label else "Winner"
            games_out.append({
                "id": game_id,
                "round": r,
                "slots": slots,
                "site": site,
                "status": "scheduled",
                "winner": None,
                "scores": None,
            })
        rounds_out.append({"round": r, "name": rnd["name"], "games": games_out})

    byes = [
        dict(seed_map[seed], first_round=entry_round)
        for seed, entry_round in sorted(structure["seed_entry_round"].items())
        if entry_round > structure["rounds"][0]["round"] and seed in seed_map
    ]

    return {
        "format": fmt,
        "field_size": n,
        "customized": is_customized(),
        "total_rounds": total_rounds,
        "rounds": rounds_out,
        "seeds": seeds,
        "byes": byes,
        "selection": {k: selection[k] for k in ("auto_bids", "first_out", "excluded", "notes", "pool_size")},
        "champion": None,
    }


# ---------------------------------------------------------------------------
# Reseeding: re-pair each round from the survivors
# ---------------------------------------------------------------------------

def fill_reseeded_rounds(bracket: dict[str, Any]) -> bool:
    """Fill a reseeded bracket's next round once the previous round is final.

    In a reseeded format (fmt["reseed"]) later rounds are built as labeled
    placeholders: the matchups only exist once the previous round's winners
    are known. When a round is fully final, its entrants (the winners plus
    any seeds whose bye ends at the next round) are ordered by ORIGINAL seed
    and paired best against worst, the NFL model: game i of the round takes
    the (i+1)-th best entrant (the top slot, the host for higher-seed sites)
    against the mirrored worst. Filled slots keep the feeder game id so the
    bracket UI can align and connect them; a campus site is updated to the
    new host. Deterministic from the results, so re-running is idempotent.
    Returns True when any slot was newly filled."""
    if not (bracket.get("format") or {}).get("reseed"):
        return False
    rounds = bracket.get("rounds") or []
    seeds = bracket.get("seeds") or []
    seed_no = {s.get("team"): s.get("seed") for s in seeds}
    changed = False
    for i in range(1, len(rounds)):
        prev, rnd = rounds[i - 1], rounds[i]
        if any(g.get("status") != "final" or not g.get("winner")
               for g in prev["games"]):
            break
        entrants: list[tuple[int, dict[str, Any], str | None]] = []
        for g in prev["games"]:
            won = next((s for s in g["slots"] if s.get("team") == g["winner"]), None)
            if won is None:
                return changed
            payload = {k: v for k, v in won.items() if k not in ("type", "game")}
            entrants.append((seed_no.get(g["winner"], 999), payload, g["id"]))
        for s in seeds:
            if s.get("entry_round") == rnd["round"]:
                entrants.append((s["seed"], dict(s), None))
        entrants.sort(key=lambda e: e[0])
        n = len(entrants)
        if n % 2 or n != 2 * len(rnd["games"]):
            break  # malformed state: leave the round for a rebuild to fix
        for gi, game in enumerate(rnd["games"]):
            if game.get("status") == "final":
                continue  # never disturb a recorded result
            top, bottom = entrants[gi], entrants[n - 1 - gi]
            want = []
            for entrant in (top, bottom):
                slot = dict(entrant[1], type="team")
                if entrant[2]:
                    slot["game"] = entrant[2]
                want.append(slot)
            if [s.get("team") for s in game["slots"]] == \
                    [w.get("team") for w in want]:
                continue
            game["slots"] = want
            site = game.get("site") or {}
            if site.get("type") == "campus":
                # the higher-seed host is now known
                site["venue"] = want[0].get("team") or site.get("venue")
                site["city"] = (school_sites.campus_city(want[0].get("espn_id"))
                                or "Campus site")
                site["host_espn_id"] = want[0].get("espn_id")
            changed = True
    return changed
