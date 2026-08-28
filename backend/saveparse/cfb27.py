"""CFB 27 dynasty save reader (the save boundary's entry point).

What is real today (parsed from the game's own files, never invented):
  * outer FBCHUNKS container + zlib inflate -> FrTk payload (`container.py`)
  * the full team table: school / nickname / abbreviation / slug (`teams.py`)
  * conference + division alignment, straight from the save (`conferences.py`)
  * dynasty identity, the user's program + coach, current week/season, record,
    and the next matchup, from the game's college profile (`profile.py`)

Still TODO (the schema tolerates their absence): rosters and player stats. The
recruiting editor separately maps the real Recruit, RecruitTarget,
and ProspectTargetSchool stores in `saveparse/recruiting.py`.

The `__main__` CLI is the standalone dump tool that proves real
teams/coaches/stadiums/recruits come out of a live save.

Payload region map (approximate byte offsets into the ~30 MB inflated payload,
observed from a fresh dynasty; treat as landmarks, not hard boundaries):
    0            FrTk header: [headerSize=128, ...section/record counts...]
    128          8-byte handle/index table
    ~2 KB..2 MB  type / field / enum name table + UI localization strings
    ~2 MB        coach / staff person records (first + last inline)
    ~4.5 MB      rivalry + scheduled-event name pool
    ~15..21 MB   dynasty state: rosters, recruits (Committed/StarLevel), Prestige
    ~25 MB       stadium records
    ~27 MB       team identity records (nickname / short / abbreviation / chant)
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from struct import error as struct_error
from typing import Any, Iterator

import json

from .. import config, schema
from .. import conferences as confmeta
from .. import teams as team_directory
from . import conferences as confstruct
from . import container, polls, profile, results, teams

INNER_MAGIC = b"FrTk"
_PRINTABLE = re.compile(rb"[\x20-\x7e]{3,}")


def saves_dir() -> Path:
    """The game's saves folder. Resolves through app_settings: a folder the user
    picked in Setup wins, else CFBMOD_SAVE_PATH, else the Documents default."""
    from .. import app_settings
    return app_settings.resolve_save_path()


def decode(source: str | Path | bytes) -> container.Container:
    """Decode the save's container and assert it is a CFB 27 (FrTk) payload."""
    c = container.decode(source)
    if not c.is_cfb27:
        raise ValueError(f"unexpected inner payload magic {c.payload[:4]!r}, expected {INNER_MAGIC!r}")
    return c


def iter_strings(payload: bytes, min_len: int = 3) -> Iterator[tuple[int, str]]:
    """Yield (offset, text) for every printable run of at least `min_len` chars."""
    for m in _PRINTABLE.finditer(payload):
        s = m.group()
        if len(s) >= min_len:
            yield m.start(), s.decode("latin1")


def grep(payload: bytes, needle: str, cap: int = 20) -> list[tuple[int, str]]:
    """Return up to `cap` (offset, containing-string) hits for a substring."""
    want = needle.encode("latin1")
    hits: list[tuple[int, str]] = []
    for off, text in iter_strings(payload):
        if want in text.encode("latin1"):
            hits.append((off, text))
            if len(hits) >= cap:
                break
    return hits


def read_save(save_path: str, slot: profile.Slot | None = None,
              *, school: str | None = None,
              dynasty_numeric_id: str | None = None) -> dict[str, Any] | None:
    """The save boundary's entry point: return a validated dynasty dict, or None.

    Decodes the FBCHUNKS container and maps it onto the dynasty schema. The
    dynasty's identity, week, coach, and record come from the save's profile
    slot (looked up in PROFILE-COLLEGE next to the save when not passed in).
    PROFILE-COLLEGE only retains rows for recently touched sessions, so a
    dynasty's row can vanish while its save lives on: `school` (from the app's
    own registry) resolves the user's program without a slot, and
    `dynasty_numeric_id` keeps the per-file identity stable so the dynasty's
    editor settings stay attached. Returns None when the file is not a CFB 27 save, is
    unreadable, or the user's program cannot be determined.
    """
    path = Path(save_path)
    if not path.exists() or not container.is_fbchunks(path):
        return None
    if slot is None:
        slot = profile.slot_for(path)
    try:
        d = to_dynasty(decode(path), slot=slot, save_name=path.name,
                       user_school=school, dynasty_numeric_id=dynasty_numeric_id)
    except Exception:  # noqa: BLE001 - never break the pipeline on a torn/odd save
        return None
    if not d or schema.validate(d):
        return None
    return d


def file_id(dynasty_id: str, save_name: str) -> str:
    """The app's identity for ONE save file: the game's numeric dynasty id plus
    the save's file name, so two saves of the same dynasty world are distinct
    and every per-file editor setting scopes to the exact file the user
    selected. Stable across scans (the file name is stable)."""
    tag = re.sub(r"[^a-z0-9]+", "-", (save_name or "").lower()).strip("-")
    return f"cfb27-{dynasty_id}-{tag}" if tag else f"cfb27-{dynasty_id}"


def discover(directory: str | Path | None = None) -> list[dict[str, Any]]:
    """Every dynasty SAVE FILE in the saves folder, one entry per file.

    Joins the profile's slot rows (identity, school, coach, week, record)
    against the DYNASTY-* files actually on disk, so stale rows for deleted
    saves drop out. Every live slot is its own entry (a dynasty with several
    saves shows each), keyed by `file_id` so edits target that exact file.
    Manual saves without a profile row are not listed; the game surfaces them
    once loaded and autosaved.

    Returns [{"dynasty_id", "game_id", "save_name", "save_path", "slot",
    "saved_at"}, ...], newest first.
    """
    d = Path(directory) if directory else saves_dir()
    if not d.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for slot in profile.read_slots(d):
        path = d / slot.save_name
        if not path.is_file():
            continue
        head = container.peek(path)
        if head is None:
            continue
        _version, saved_at, _build = head
        entries.append({
            "dynasty_id": file_id(slot.dynasty_id, slot.save_name),
            "game_id": slot.dynasty_id,   # the dynasty world these saves share
            "save_name": slot.save_name,
            "save_path": str(path),
            "slot": slot,
            "saved_at": saved_at.isoformat() if saved_at else "",
        })
    return sorted(entries, key=lambda e: e["saved_at"] or "", reverse=True)


def team_options(save_path: str | Path) -> list[dict[str, Any]] | None:
    """The save's team list (name / school / abbreviation + espn id, colors,
    logo, conference) for the manual-import team picker: when a save has no
    profile row, the user picks their program from this list. Returns None when
    the file is not a readable CFB 27 save."""
    p = Path(save_path)
    if not p.exists() or not container.is_fbchunks(p):
        return None
    try:
        roster = teams.parse_teams(decode(p).payload)
    except Exception:  # noqa: BLE001 - a torn/odd save yields no picker options
        return None
    return [{"name": t.name, "school": t.school, "abbreviation": t.abbreviation,
             **_identity(t.name)} for t in roster]


def to_dynasty(c: container.Container, *, slot: profile.Slot | None = None,
               user_team_slug: str | None = None,
               save_name: str | None = None,
               user_school: str | None = None,
               dynasty_numeric_id: str | None = None) -> dict[str, Any] | None:
    """Map an FrTk payload onto the dynasty schema (backend/schema.py).

    Emits only what the game's files actually state: the full team list with
    the save's own alignment, the user's program, the season position, the
    coach, the record, and the next matchup (the last four from the profile
    slot). The user's program comes from the slot's school; `user_team_slug`
    (a teamdb slug like "bama") is the explicit override for tests and the
    CLI, and `user_school` + `dynasty_numeric_id` (the app's registry) stand
    in when the save's PROFILE-COLLEGE row has rotated away.
    """
    roster = teams.parse_teams(c.payload)
    user = _user_team(roster, slot, user_team_slug, user_school)
    if user is None:
        return None
    align = _save_alignment(c.payload, roster)

    def identity(t: teams.Team) -> dict[str, Any]:
        # the save's own alignment beats the league-seed guess (the game's 2026
        # conferences differ from the seed's 2025 snapshot, and the user may
        # have realigned in the game or through the conference setup editor)
        return {**_identity(t.name), **align.get(t.name, {})}

    team: dict[str, Any] = {
        "name": user.name,
        "school": user.school,
        "nickname": user.nickname,
        "abbreviation": user.abbreviation,
        "slug": user.slug,
        **identity(user),
    }
    if slot is not None:
        team["record"] = {"overall": slot.record, "wins": slot.wins, "losses": slot.losses}
        if slot.coach_name:
            team["head_coach"] = {"name": slot.coach_name, "title": "Head Coach", "is_user": True}

    d: dict[str, Any] = {
        "meta": {
            "source": "save",
            "generated_at": c.saved_at.isoformat() if c.saved_at else None,
            "app_version": "cfb27-saveparse",
            "dynasty_id": (file_id(dynasty_numeric_id, save_name or "")
                           if dynasty_numeric_id else _dynasty_id(c, user, slot, save_name)),
            # Cheap change marker: same save name + write stamp == same content.
            "hash": f"{save_name or ''}@{c.saved_at.isoformat() if c.saved_at else len(c.payload)}",
        },
        "season": _season(slot, save_name, payload=c.payload),
        "team": team,
        # Extra (non-schema) reference the companion can use to resolve opponents,
        # standings, and logos; modules ignore keys they do not read.
        "all_teams": [{**t.to_schema(), **identity(t)} for t in roster],
    }
    upcoming = _upcoming(slot, roster)
    if upcoming:
        d["schedule"] = {"upcoming": upcoming, "recent_results": []}

    # Results / standings / rankings, straight from the save (2026-07-07:
    # SeasonGameStore + the TeamStore rank fields are decoded). Additive and
    # best-effort: a save these fail on still loads as before, and modules
    # keep degrading through _MODULE_DATA_KEY when a key is absent.
    try:
        _apply_results(d, c.payload, roster, user, align)
    except Exception:  # noqa: BLE001 - results must never break a load
        pass
    return d


def _apply_results(d: dict[str, Any], payload: bytes, roster: list[teams.Team],
                   user: teams.Team, align: dict[str, dict[str, Any]]) -> None:
    """Fill the schema blocks the save can now answer: the user's game log,
    conference standings, the national rankings, and every team's record and
    rivalry-week outcome (only OFFICIAL results; the engine pre-sims the
    current week and those scores must never leak, see saveparse/schedule.py)."""
    user_row = next((i for i, t in enumerate(roster) if t.slug == user.slug), None)
    row_conf = {i: (align.get(t.name) or {}).get("conference")
                for i, t in enumerate(roster)}
    blocks = results.build_blocks(payload, user_row=user_row, alignment=row_conf)

    sched = d.setdefault("schedule", {"upcoming": None, "recent_results": []})
    if blocks.get("recent_results"):
        # ResultCard's helmet needs opponent_espn_id; results.build_blocks only
        # knows the opponent's school name, so resolve the id here the same way
        # _upcoming does for the next game.
        for row in blocks["recent_results"]:
            if row.get("opponent"):
                eid = _identity(row["opponent"]).get("espn_id")
                if eid:
                    row["opponent_espn_id"] = eid
        sched["recent_results"] = blocks["recent_results"]
    if blocks.get("conference_standings"):
        d["conference_standings"] = blocks["conference_standings"]

    # every team's official record + current ranks onto all_teams (the
    # playoff selection pool and standings surfaces read these)
    records = blocks.get("team_records") or {}
    conf_records = blocks.get("conference_records") or {}
    ranks = {t.row: t for t in polls.parse(payload)}
    by_name = {t.name: i for i, t in enumerate(roster)}

    # the user's own committee + AP rank, for the top-bar HUD chips. The save
    # ranks every team (a full ordering, not just a top 25); a rank of 0 means
    # unranked, which the UI renders as "NR". A pushed custom poll writes these
    # same fields, so the chips follow the user's custom ranking automatically.
    if user_row is not None and user_row in ranks:
        ur = ranks[user_row]
        rankings = d.setdefault("team", {}).setdefault("rankings", {})
        rankings["cfp"] = ur.rank if ur.rank and ur.rank > 0 else None
        rankings["ap"] = ur.ap_rank if ur.ap_rank and ur.ap_rank > 0 else None
    for row_dict in d.get("all_teams") or []:
        i = by_name.get(row_dict.get("name"))
        if i is None:
            continue
        w, l = records.get(i, (0, 0))
        if w or l:
            row_dict["record"] = f"{w}-{l}"
        cw, cl = conf_records.get(i, (0, 0))
        if cw or cl:
            row_dict["conf_record"] = f"{cw}-{cl}"
        if i in ranks:
            row_dict["rank"] = ranks[i].rank

    # crowned conference champions (empty until the CCGs are official). The
    # playoff selection's champion auto-bids and champions-only rule read
    # these so the ACTUAL championship-game winner is the champion, not the
    # conference's best-ranked team.
    champs = blocks.get("conference_champions") or {}
    if champs:
        d["conference_champions"] = {conf: roster[r].name
                                     for conf, r in champs.items()
                                     if r < len(roster)}

    # rivalry-week outcomes for the playoff disqualifier (empty until the
    # regular season is over)
    rw = blocks.get("rivalry_week_lost") or {}
    if rw:
        sched["rivalry_week_losers"] = sorted(
            roster[t].name for t, lost in rw.items() if lost and t < len(roster))

    # national rankings: the CFP committee poll drives cfp_top25 + seeding,
    # the AP-style poll fills ap_top25 (flavor). Both fields rank every team,
    # so the top 25 is just the head of each.
    def poll(key: str) -> list[dict[str, Any]]:
        rows = sorted(ranks.values(), key=lambda t: getattr(t, key) or 999)
        out = []
        for t in rows:
            if getattr(t, key) < 1 or len(out) >= 25:
                break
            team = roster[t.row]
            w, l = records.get(t.row, (0, 0))
            out.append({"rank": getattr(t, key), "team": team.name,
                        "abbr": team.abbreviation, "record": f"{w}-{l}",
                        # the logo/helmet everywhere resolves off espn_id, so
                        # resolve it here (by name) or the whole national picture
                        # falls back to monograms
                        "espn_id": _identity(team.name).get("espn_id")})
        return out

    national = d.setdefault("national", {})
    cfp = poll("rank")
    if cfp:
        national["cfp_top25"] = cfp
        national["cfp_top12"] = cfp[:12]
        national["ap_top25"] = poll("ap_rank") or cfp
    if blocks.get("scoreboard"):
        # Stamp poll ranks onto the scoreboard sides (matched by abbreviation),
        # so upset / ranked-clash detection works on a real save's results.
        abbr_rank: dict[str, int] = {}
        for t in ranks.values():
            r = getattr(t, "ap_rank", 0) or getattr(t, "rank", 0)
            if r and 1 <= r <= 25 and t.row < len(roster):
                abbr_rank[roster[t.row].abbreviation] = r
        for g in blocks["scoreboard"]:
            for side in ("home", "away"):
                s = g.get(side) or {}
                ab = s.get("abbr")
                if ab and ab in abbr_rank:
                    s["rank"] = abbr_rank[ab]
                # marquee/result helmets need espn_id; the scoreboard sides carry
                # only name+abbr, so resolve the id by team name here
                if s.get("name") and s.get("espn_id") is None:
                    s["espn_id"] = _identity(s["name"]).get("espn_id")
        national["scoreboard"] = blocks["scoreboard"]


def backfill_national_ids(dynasty: dict[str, Any]) -> dict[str, Any]:
    """Stamp espn_id onto national poll/scoreboard entries that lack it, in
    place. New parses already carry it; this repairs week snapshots archived
    before ids were added, so a browsed past week still resolves logos/helmets
    instead of falling back to monograms. Cheap and idempotent."""
    nat = dynasty.get("national") or {}
    for key in ("cfp_top25", "cfp_top12", "ap_top25"):
        for row in nat.get(key) or []:
            if isinstance(row, dict) and row.get("espn_id") is None and row.get("team"):
                row["espn_id"] = _identity(row["team"]).get("espn_id")
    for g in nat.get("scoreboard") or []:
        for side in ("home", "away"):
            s = g.get(side) or {}
            if s.get("espn_id") is None and s.get("name"):
                s["espn_id"] = _identity(s["name"]).get("espn_id")
    for row in (dynasty.get("schedule") or {}).get("recent_results") or []:
        if row.get("opponent") and not row.get("opponent_espn_id"):
            eid = _identity(row["opponent"]).get("espn_id")
            if eid:
                row["opponent_espn_id"] = eid
    return dynasty


def _match_school(roster: list[teams.Team], school: str) -> teams.Team | None:
    """Resolve a school display string against the save's team table.

    Exact, then prefix, then a normalized pass that shrugs off accents,
    periods, and 'St'/'State' abbreviation. The game's own strings are not
    consistent: the FCS-to-FBS movers' profile rows can spell their schools
    in forms the team table does not use, which made those dynasties
    silently unimportable (reported: Sacramento State, North Dakota State)."""
    school = (school or "").strip().lower()
    if not school:
        return None
    exact = next((t for t in roster if t.school.lower() == school), None)
    if exact is not None:
        return exact
    pre = next((t for t in roster if t.school.lower().startswith(school)), None)
    if pre is not None:
        return pre

    def canon(s: str) -> str:
        s = _norm_name(s).replace(".", "")
        return re.sub(r"\bst\b", "state", s)

    q = canon(school)
    return next((t for t in roster
                 if canon(t.school) == q or canon(t.school).startswith(q)), None)


def _user_team(roster: list[teams.Team], slot: profile.Slot | None,
               user_team_slug: str | None,
               user_school: str | None = None) -> teams.Team | None:
    """Resolve the user's program: an explicit slug override, else the school
    the CALLER passed (the import picker's explicit choice, or the app's
    registry hint), else the profile slot's school, matched against the save's
    own team table. The explicit choice outranks the slot so the user can
    always recover a save whose profile row spells their school
    unrecognizably."""
    if user_team_slug:
        return next((t for t in roster if t.slug == user_team_slug), None)
    for cand in (user_school, slot.school if slot else None):
        t = _match_school(roster, cand or "")
        if t is not None:
            return t
    return None


def _upcoming(slot: profile.Slot | None, roster: list[teams.Team]) -> dict[str, Any] | None:
    """The next matchup from the profile's display string (' @ Tulsa',
    ' vs Ohio State'). Only what the game states: opponent + home/away."""
    raw = (slot.next_game if slot else "").strip()
    if not raw:
        return None
    home = not raw.startswith("@")
    name = raw.lstrip("@").strip()
    if name.lower().startswith("vs"):
        name = name[2:].strip()
    opp = next((t for t in roster if t.school.lower() == name.lower()), None)
    out: dict[str, Any] = {"opponent": opp.name if opp else name, "home": home,
                           "week": slot.week if slot else None}
    if opp is not None:
        out["opponent_abbr"] = opp.abbreviation
        meta = _identity(opp.name)
        if meta.get("espn_id"):
            out["opponent_espn_id"] = meta["espn_id"]
    return out


def _save_alignment(payload: bytes, roster: list[teams.Team]) -> dict[str, dict[str, Any]]:
    """team full name -> {conference, division} parsed from the save itself.

    Conference display names are canonicalized to the companion's names
    ('MWC' -> 'Mountain West') so logos and committee affiliations resolve.
    Returns {} when the structures cannot be parsed (graceful seed fallback)."""
    try:
        table = confstruct.parse(payload)
    except (ValueError, struct_error):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for conf in table.conferences:
        if conf.blank:
            continue
        rec = confmeta.resolve(conf.display)
        name = rec["name"] if rec else conf.display
        multi = len(conf.division_rows) > 1
        div_of: dict[int, str | None] = {}
        for dr in conf.division_rows:
            div = table.divisions[dr]
            for r in div.team_rows:
                div_of[r] = div.name if multi and div.name else None
        # membership comes from the CONFERENCE list, not the division union:
        # a realigned save can leave a conference's division list empty while
        # the conference list carries the real members (observed live, the
        # American), and reading divisions only sent those teams back to
        # their league-seed conferences in all_teams
        members = conf.team_rows or list(div_of)
        for r in members:
            if r < len(roster):
                out[roster[r].name] = {
                    "conference": name,
                    "division": div_of.get(r),
                }
    return out


def _identity(team_name: str) -> dict[str, Any]:
    """espn id / colors / logo / conference for a save team.

    The league seed (every FBS program, with espn ids + conferences + colors)
    is the primary source; the ESPN-backed team directory fills in colors when
    it has the school. The save's own ratings/color fields are not decoded yet."""
    seed = _seed_row(team_name)
    meta = team_directory.get_team(team_name)
    espn_id = (seed or {}).get("espn_id") or meta.get("espn_id")
    if espn_id is None:
        # named FCS opponent: resolve by school prefix (name is "School Nick")
        q = _norm_name(team_name)
        for school, fid in _FCS_TEAMS.items():
            if q == school or q.startswith(school + " "):
                espn_id = fid
                break
    # When the save's name did not match the directory (e.g. "UMass" vs
    # "Massachusetts") but the seed resolved an espn id, pull colors from the
    # directory record for that id so the team's tile is its real color, not
    # the gray default.
    by_id = meta if meta.get("espn_id") is not None else _directory_by_espn(espn_id)
    return {
        "espn_id": espn_id,
        "color": by_id.get("color") or meta.get("color"),
        "alt_color": by_id.get("alternate_color") or meta.get("alternate_color"),
        "logo": f"/game-assets/teams/{espn_id}/logo.png" if espn_id else None,
        "conference": (seed or {}).get("conference"),
    }


_directory_by_espn_cache: dict[Any, dict[str, Any]] | None = None


def _directory_by_espn(espn_id: Any) -> dict[str, Any]:
    """The ESPN-backed team directory record for an espn id (colors/logo)."""
    global _directory_by_espn_cache
    if espn_id is None:
        return {}
    if _directory_by_espn_cache is None:
        _directory_by_espn_cache = {}
        try:
            for rec in team_directory.get_all_teams().values():
                if rec.get("espn_id") is not None:
                    _directory_by_espn_cache.setdefault(rec["espn_id"], rec)
        except Exception:  # noqa: BLE001
            pass
    return _directory_by_espn_cache.get(espn_id, {})


def _norm_name(s: str) -> str:
    """Accent-insensitive, whitespace-collapsed lowercase key so the save's
    'San Jose State' matches the seed's 'San José State'."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


# Programs the CFB 27 save spells differently from the league seed / ESPN.
# Keyed by the save's school name (normalized) -> the seed's school name
# (normalized); the shared nickname makes the reconstructed full name match.
_SCHOOL_ALIASES = {
    "umass": "massachusetts",
    "usf": "south florida",
    "miami university": "miami (oh)",
    "appalachian state": "app state",
    "southern mississippi": "southern miss",
}

# Legacy espn-id fallback for programs the league seed may not list. North
# Dakota State and Sacramento State joined FBS for 2026 and are full members
# of the league seed now (data/league_seed.json, MWC / MAC), so for a current
# seed this map is dead code; it stays because a frozen build never overwrites
# a user's already-seeded league_seed.json (config._seed_bundled_data), and an
# install carrying a pre-2026 seed still needs their espn ids to resolve.
_FCS_TEAMS = {
    "north dakota state": 2449,
    "sacramento state": 16,
}

_seed_by_name: dict[str, dict[str, Any]] | None = None
_seed_by_norm: dict[str, dict[str, Any]] | None = None


def _seed_row(team_name: str) -> dict[str, Any] | None:
    global _seed_by_name, _seed_by_norm
    if _seed_by_name is None:
        _seed_by_name = {}
        try:
            seed = json.loads((config.DATA_DIR / "league_seed.json").read_text(encoding="utf-8"))
            rows = seed["teams"] if isinstance(seed, dict) else seed
            _seed_by_name = {r["name"]: r for r in rows if r.get("name")}
        except (OSError, ValueError, KeyError):
            pass
        _seed_by_norm = {_norm_name(n): r for n, r in _seed_by_name.items()}
    if team_name in _seed_by_name:
        return _seed_by_name[team_name]
    q = _norm_name(team_name)
    if q in _seed_by_norm:
        return _seed_by_norm[q]
    # apply a school-name alias (replace the save's school prefix with the
    # seed's), then match on the reconstructed name
    for save_school, seed_school in _SCHOOL_ALIASES.items():
        if q == save_school or q.startswith(save_school + " "):
            aliased = seed_school + q[len(save_school):]
            if aliased in _seed_by_norm:
                return _seed_by_norm[aliased]
            hit = next((r for n, r in _seed_by_norm.items() if n.startswith(seed_school)), None)
            if hit:
                return hit
    # last resort: prefix match either direction on the normalized names
    return next((r for n, r in _seed_by_norm.items() if n.startswith(q) or q.startswith(n)), None)


def _season(slot: profile.Slot | None, save_name: str | None = None,
            payload: bytes | None = None) -> dict[str, Any]:
    """Current season/week, from the profile slot (the game's own position).

    Without a slot (the save's profile row rotated away, or a manual save),
    the position is derived from the save's own schedule store: how far the
    official results reach says whether the season is in the regular weeks,
    conference championship week, or bowl season. Falls back to the
    `DYNASTY-WEEK<n>` file-name convention, else preseason.
    """
    if slot is not None:
        label_word = slot.week_label or "Week"
        return {
            "year": slot.year,
            "week": slot.week,
            "week_label": f"{label_word} {slot.week}" if slot.week else "Preseason",
            "phase": "regular" if label_word.lower() == "week" and slot.week >= 1 else (
                "preseason" if slot.week == 0 else label_word.lower()),
        }
    if payload is not None:
        try:
            return {"year": profile.FIRST_SEASON_YEAR, **_season_from_schedule(payload)}
        except Exception:  # noqa: BLE001 - fall through to the name heuristic
            pass
    week = 0
    if save_name:
        m = re.search(r"WEEK(\d+)", save_name, re.IGNORECASE)
        if m:
            week = int(m.group(1))
    regular = week >= 1
    return {
        "year": profile.FIRST_SEASON_YEAR,
        "week": week,
        "week_label": f"Week {week}" if regular else "Preseason",
        "phase": "regular" if regular else "preseason",
    }


def _season_from_schedule(payload: bytes) -> dict[str, Any]:
    """Approximate season position from the schedule store's official results
    (exact weeks are not stored per game; this is stable within each phase,
    which is what the pipeline's pointer and the playoff runtime need)."""
    from . import schedule as schedstore
    store = schedstore.parse(payload)
    max_bowl = max((g.index for g in store.games if g.bowl_row is not None),
                   default=-1)
    no_bowl = [g for g in store.games if g.bowl_row is None and g.scheduled]
    played = [g for g in no_bowl if g.official]
    if not played:
        return {"week": 0, "week_label": "Preseason", "phase": "preseason"}
    unplayed = [g for g in no_bowl if not g.official]
    if any(g.index > max_bowl for g in played):
        # the CCG block (above the bowl records) has official results
        return {"week": 17, "week_label": "Bowl Week", "phase": "bowls"}
    if all(g.index > max_bowl for g in unplayed):
        # only the championship games remain: conference title week
        return {"week": 16, "week_label": "Conference Championships",
                "phase": "conf_championship"}
    # rough regular-season position: the busiest team's games played + 1
    per_team: dict[int, int] = {}
    for g in played:
        for t in (g.away_row, g.home_row):
            if t is not None:
                per_team[t] = per_team.get(t, 0) + 1
    week = min(15, max(per_team.values(), default=0) + 1)
    return {"week": week, "week_label": f"Week {week}", "phase": "regular"}


def _dynasty_id(c: container.Container, user: teams.Team, slot: profile.Slot | None,
                save_name: str | None) -> str:
    """The app's identity for this save FILE (see `file_id`): the game's numeric
    dynasty id plus the file name, so each save file is its own thing and edits
    to one never touch another. Falls back to the build-id + program slug for
    saves with no profile row."""
    if slot is not None and slot.dynasty_id:
        return file_id(slot.dynasty_id, save_name or "")
    base = f"{c.build_id}-{user.slug}-{save_name or ''}"
    return "cfb27-" + re.sub(r"[^A-Za-z0-9_-]+", "-", base).strip("-").lower()


def newest_save(directory: str | Path | None = None) -> Path | None:
    """The newest DYNASTY-* save in the CFB 27 saves folder (or `directory`).
    A last-resort fallback for tooling; the app resolves saves per dynasty
    through `discover()` (the profile join) instead."""
    d = Path(directory) if directory else saves_dir()
    if not d.is_dir():
        return None
    saves = sorted((p for p in d.glob("DYNASTY-*") if p.is_file()),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return saves[0] if saves else None


# --- standalone dump tool -------------------------------------------------
def _default_save() -> Path | None:
    return newest_save()


def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Decode + survey a CFB 27 dynasty save.")
    ap.add_argument("save", nargs="?", help="path to a DYNASTY-* save (defaults to newest autosave)")
    ap.add_argument("--grep", action="append", default=[], help="substring to locate (repeatable)")
    ap.add_argument("--region", nargs=2, type=int, metavar=("START", "END"),
                    help="print all strings whose offset falls in [START, END)")
    ap.add_argument("--teams", action="store_true", help="extract and print the full team list")
    args = ap.parse_args(argv)

    save = Path(args.save) if args.save else _default_save()
    if not save or not save.exists():
        print("no save found; pass a path to a DYNASTY-* file")
        return 2

    c = decode(save)
    print(f"save:      {save.name}")
    print(f"version:   {c.version}")
    print(f"saved at:  {c.saved_at}")
    print(f"build id:  {c.build_id}")
    print(f"payload:   {len(c.payload):,} bytes (compressed {c.compressed_len:,}), inner magic {c.payload[:4]!r}")

    if args.teams:
        rows = teams.parse_teams(c.payload)
        print(f"\n--- {len(rows)} teams ---")
        print(f"  {'slug':<12}{'abbr':<6}{'school':<26}nickname")
        for t in rows:
            print(f"  {t.slug:<12}{t.abbreviation:<6}{t.school:<26}{t.nickname}")
        return 0

    if args.region:
        lo, hi = args.region
        print(f"\n--- strings in [{lo:,} .. {hi:,}) ---")
        for off, text in iter_strings(c.payload):
            if lo <= off < hi:
                print(f"  {off:>9}: {text}")
        return 0

    needles = args.grep or ["Crimson Tide", "Bulldogs", "Wolverines", "ROLLTIDE", "Haines", "Bryant-Denny"]
    print("\n--- proof: real records located by substring ---")
    for needle in needles:
        hits = grep(c.payload, needle, cap=5)
        shown = ", ".join(f"@{o}:{t!r}" for o, t in hits) or "(none)"
        print(f"  {needle!r:>16}: {shown}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(_main(sys.argv[1:]))
