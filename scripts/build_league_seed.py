"""Build data/league_seed.json: the FBS universe the simulation engine runs on.

One-time / refresh builder (run manually, like analyze_bracket.py). It pulls the
current FBS conference alignment from ESPN's public standings endpoint (a single
request that returns every conference and its teams), merges a curated power
rating + prestige table for brand programs with conference-tier baselines for
everyone else, and writes a checked-in seed. The app reads that JSON at runtime
and never depends on the network (same ethos as data/teams_cache.json).

    python scripts/build_league_seed.py            # refresh from ESPN
    python scripts/build_league_seed.py --offline  # rebuild ratings from existing seed alignment

Output row shape:
    {name, espn_id, abbr, conference, division|null, base_rating, prestige}

base_rating is a 0-100 program-strength number (~50 = average FBS, 90+ = elite)
that seeds each season's ratings. prestige is a 1-10 brand/recruiting number used
for tie-breaks and flavor. Both are intentionally editable; tune freely.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = ROOT / "data" / "league_seed.json"

STANDINGS_URL = "https://cdn.espn.com/core/college-football/standings?xhr=1"

# ESPN conference display name -> our backend/conferences.py key.
CONF_NAME_MAP = {
    "American Conference": "American",
    "Atlantic Coast Conference": "ACC",
    "Big 12 Conference": "Big 12",
    "Big Ten Conference": "Big Ten",
    "Conference USA": "Conference USA",
    "FBS Independents": "FBS Independents",
    "Mid-American Conference": "MAC",
    "Mountain West Conference": "Mountain West",
    "Pac-12 Conference": "Pac-12",
    "Southeastern Conference": "SEC",
    "Sun Belt Conference": "Sun Belt",
}

# Conference-tier baseline rating used when a team is not in CURATED below.
CONF_BASELINE = {
    "SEC": 70,
    "Big Ten": 69,
    "Big 12": 65,
    "ACC": 64,
    "American": 56,
    "Mountain West": 55,
    "Pac-12": 55,
    "Sun Belt": 51,
    "MAC": 50,
    "Conference USA": 49,
    "FBS Independents": 55,
}

# Curated power ratings for brand / contender programs (0-100). Everyone else
# inherits their conference baseline plus a small deterministic per-team offset.
# prestige (1-10) defaults are derived from base_rating when not given here.
CURATED: dict[str, int] = {
    "Georgia Bulldogs": 93, "Ohio State Buckeyes": 92, "Texas Longhorns": 91,
    "Alabama Crimson Tide": 90, "Oregon Ducks": 89, "Penn State Nittany Lions": 87,
    "Michigan Wolverines": 87, "Notre Dame Fighting Irish": 86, "Tennessee Volunteers": 85,
    "LSU Tigers": 85, "Ole Miss Rebels": 84, "Clemson Tigers": 84, "Oklahoma Sooners": 83,
    "Florida State Seminoles": 82, "Texas A&M Aggies": 82, "Miami Hurricanes": 81,
    "Missouri Tigers": 81, "Utah Utes": 80, "USC Trojans": 80, "Florida Gators": 79,
    "South Carolina Gamecocks": 79, "Washington Huskies": 79, "Kansas State Wildcats": 79,
    "Auburn Tigers": 78, "Iowa Hawkeyes": 78, "Louisville Cardinals": 78, "SMU Mustangs": 78,
    "Arizona State Sun Devils": 78, "Indiana Hoosiers": 77, "Wisconsin Badgers": 77,
    "BYU Cougars": 77, "Iowa State Cyclones": 77, "Texas Tech Red Raiders": 77,
    "Nebraska Cornhuskers": 76, "TCU Horned Frogs": 76, "Kansas Jayhawks": 75,
    "Colorado Buffaloes": 75, "Boise State Broncos": 75, "Michigan State Spartans": 74,
    "Tulane Green Wave": 74, "UNLV Rebels": 72, "Memphis Tigers": 72, "Army Black Knights": 72,
    "Liberty Flames": 72, "James Madison Dukes": 72, "Navy Midshipmen": 71,
    "Pittsburgh Panthers": 71, "NC State Wolfpack": 71, "Georgia Tech Yellow Jackets": 71,
    "Kentucky Wildcats": 71, "North Carolina Tar Heels": 70, "Virginia Tech Hokies": 70,
    "Oklahoma State Cowboys": 70, "Baylor Bears": 70, "UCLA Bruins": 69, "Minnesota Golden Gophers": 70,
    "Washington State Cougars": 64, "Oregon State Beavers": 63,
}


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def _collect_entries(group: dict, conf_name: str, out: list, division: str | None = None) -> None:
    """Walk a conference group, descending into divisions (Sun Belt East/West).

    A flat conference (no sub-groups) yields entries with division=None. A
    divided conference yields its sub-group name's trailing token (East/West).
    """
    standings = group.get("standings")
    if isinstance(standings, dict) and standings.get("entries"):
        for en in standings["entries"]:
            out.append((conf_name, division, en.get("team", {})))
    for sub in group.get("groups", []) or []:
        # "Sun Belt Conference - East" / "...West" -> "East" / "West".
        raw = (sub.get("name") or "").replace("-", " ")
        div = raw.split()[-1] if raw.strip() else None
        _collect_entries(sub, conf_name, out, division=div)


def _prestige_for(rating: int) -> int:
    # Map a 0-100 rating onto a 1-10 prestige band.
    return max(1, min(10, round((rating - 40) / 6)))


def _offset(espn_id) -> int:
    """Small deterministic per-team spread within a conference tier (-4..+4)."""
    try:
        return (int(espn_id) % 9) - 4
    except (TypeError, ValueError):
        return 0


def build_from_espn() -> list[dict]:
    data = _get(STANDINGS_URL)
    groups = data["content"]["standings"]["groups"]
    raw: list = []
    for g in groups:
        conf = CONF_NAME_MAP.get(g.get("name"), g.get("name"))
        _collect_entries(g, conf, raw)

    rows: list[dict] = []
    seen: set = set()
    for conf, division, t in raw:
        name = t.get("displayName")
        if not name or name in seen:
            continue
        seen.add(name)
        espn_id = t.get("id")
        try:
            espn_id = int(espn_id)
        except (TypeError, ValueError):
            pass
        base = CURATED.get(name)
        if base is None:
            base = CONF_BASELINE.get(conf, 50) + _offset(espn_id)
        base = max(40, min(96, base))
        rows.append({
            "name": name,
            "espn_id": espn_id,
            "abbr": (t.get("abbreviation") or name[:4]).upper(),
            "conference": conf,
            "division": division,
            "base_rating": base,
            "prestige": _prestige_for(base),
        })
    rows.sort(key=lambda r: (r["conference"], -r["base_rating"], r["name"]))
    return rows


def rebuild_ratings(existing: list[dict]) -> list[dict]:
    """Recompute ratings/prestige from a checked-in seed's alignment (offline)."""
    for r in existing:
        base = CURATED.get(r["name"])
        if base is None:
            base = CONF_BASELINE.get(r["conference"], 50) + _offset(r.get("espn_id"))
        r["base_rating"] = max(40, min(96, base))
        r["prestige"] = _prestige_for(r["base_rating"])
    return existing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="rebuild ratings from the existing seed alignment without hitting ESPN")
    args = ap.parse_args()

    if args.offline:
        if not SEED_FILE.exists():
            print("no existing seed to rebuild from", file=sys.stderr)
            return 1
        rows = rebuild_ratings(json.loads(SEED_FILE.read_text()))
    else:
        try:
            rows = build_from_espn()
        except Exception as exc:  # noqa: BLE001
            print(f"ESPN fetch failed ({type(exc).__name__}: {exc}).", file=sys.stderr)
            return 1

    SEED_FILE.write_text(json.dumps(rows, indent=2) + "\n")
    by_conf: dict[str, int] = {}
    for r in rows:
        by_conf[r["conference"]] = by_conf.get(r["conference"], 0) + 1
    print(f"Wrote {len(rows)} FBS teams to {SEED_FILE.relative_to(ROOT)}")
    for conf, n in sorted(by_conf.items()):
        print(f"  {conf}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
