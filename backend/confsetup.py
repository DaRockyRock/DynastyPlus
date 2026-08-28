"""The conference setup editor: Dynasty+'s view of the game's conferences.

The editor state has one entry per conference. In-game conferences come from
the real save (parsed by `saveparse.conferences`); the user can rename them,
retitle their championship game, move teams between them (including to and
from the Independents pool), shuffle divisions where the game has them, and
attach companion-only flavor (abbreviation, logo, description, rivalries).
Custom conferences created here are companion-only: they drive Dynasty+ media,
standings framing, and the custom playoff's champion auto-bids, but they are
never written into the save (the game has no spare conference slot that can be
activated safely, see saveparse/conferences.py).

Persistence is per dynasty (data/dynasties/<id>/conference_setup.json) and
stores the full editor state only once the user saves an edit; until then the
state mirrors the save. "Apply to game" patches the writable slice (renames +
membership + division names/membership) into a NEW save file next to the
existing ones; it never overwrites a save the game wrote, and it is gated to
the preseason/offseason because the game's generated schedule bakes in
conference membership once a season starts (the game itself only realigns at
season boundaries).
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from . import conferences as confmeta
from . import app_settings, config, dynasty_paths
from .saveparse import cfb27, conferences as savestruct
from .saveparse import container, teams as saveteams

_lock = threading.Lock()
_log = logging.getLogger(__name__)

MIN_TEAMS, MAX_TEAMS = 4, 20
NAME_CAP = savestruct.CONF_FIELDS["display"][1] - 1        # 20
CHAMP_CAP = savestruct.CONF_FIELDS["champ_game"][1] - 1    # 27
DIV_NAME_CAP = savestruct.DIV_FIELDS["name"][1] - 1        # 20
GATE_REASON = ("Conference changes can only be written to the game in the "
               "preseason or offseason, before the schedule is generated.")


# --- reading the save -------------------------------------------------------

def _save_file() -> Path | None:
    """The real CFB 27 save the editor works against, scoped to the ACTIVE
    dynasty. Resolution mirrors pipeline._read_save so the editor pages
    (conferences, polls, the live playoff) and the dynasty loader always agree
    on the file:

    1. an explicit single-FILE CFBMOD_SAVE_PATH override (tests/tooling);
    2. the active dynasty's own save, via the profile join (discover());
    3. the registry's remembered file name: PROFILE-COLLEGE only keeps rows
       for recently touched sessions, so a live dynasty's row can rotate away
       while its save file lives on;
    4. the newest save, ONLY when no dynasty is active (never-scanned cold
       start). With a dynasty selected, a newest-file fallback could hand the
       editors a DIFFERENT dynasty's save, and every read (and write!) would
       silently target the wrong file.

    The saves folder itself resolves through cfb27.saves_dir() (the folder
    picked in Setup, else CFBMOD_SAVE_PATH, else the Documents default), the
    same resolution Scan uses, so a custom saves location works here too."""
    explicit = Path(config.SAVE_PATH)
    if explicit.exists() and not explicit.is_dir():
        return explicit if container.is_fbchunks(explicit) else None

    current = dynasty_paths.current_id()  # e.g. "cfb27-1920640934-<save-name>"
    if current:
        for entry in cfb27.discover():
            if entry.get("dynasty_id") == current:
                p = Path(entry["save_path"])
                if container.is_fbchunks(p):
                    return p
        from . import dynasties  # lazy: same deferred import as pipeline
        reg = dynasties.get(current)
        if reg and reg.get("save_name"):
            p = cfb27.saves_dir() / reg["save_name"]
            if p.is_file() and container.is_fbchunks(p):
                return p
        return None
    p = cfb27.newest_save()
    if p is not None and container.is_fbchunks(p):
        return p
    return None


_table_cache: dict[str, Any] = {}


def invalidate_caches() -> None:
    """Drop cached save data so the next read picks up the active dynasty's save.

    Called whenever the active dynasty changes (select, scan, watcher switch)."""
    _table_cache.clear()
    _overlay_cache.clear()


def _read_table() -> dict[str, Any] | None:
    """Decode the save and parse what the editors need, cached by file mtime.

    The decoded payload + team roster are the essentials: every payload-only
    reader that shares this accessor (the poll editor, the playoff sync, the
    stadium/schedule readers) depends on them and nothing else. The CONFERENCE
    table is parsed separately and is allowed to fail: a save whose conference
    structures we cannot read (heavy in-game realignment, an unmapped layout)
    still yields a usable ctx with ``table=None``, so a conference-parse problem
    can never take down the polls/playoff pages the way it used to (they all
    reach the payload through here). Only the conference editor itself treats
    ``table is None`` as unavailable. Returns None only when the save cannot be
    decoded or its team table cannot be read at all."""
    path = _save_file()
    if path is None:
        return None
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return None
    if _table_cache.get("key") == (str(path), mtime):
        return _table_cache["value"]
    try:
        raw = path.read_bytes()
        c = container.decode(raw)
        roster = saveteams.parse_teams(c.payload)
    except (OSError, ValueError):
        return None
    try:
        table = savestruct.parse(c.payload)
    except Exception:  # noqa: BLE001 - conferences are optional; see the docstring
        table = None
    value = {"path": path, "raw": raw, "payload": c.payload, "table": table,
             "roster": roster, "rows_by_name": {t.name: i for i, t in enumerate(roster)}}
    _table_cache["key"] = (str(path), mtime)
    _table_cache["value"] = value
    return value


def current_payload() -> bytes | None:
    """The ACTIVE dynasty's decoded save payload (mtime-cached). Shared by the
    other save readers (the playoff stadium picker, the schedule reader) so
    the 30MB save is decoded once per file change."""
    ctx = _read_table()
    return ctx["payload"] if ctx else None


def _conf_slug(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-") or "conference"


def _canonical(display: str) -> str:
    """The companion's canonical name for a save conference ('MWC' ->
    'Mountain West') so logos/committee affiliations keep resolving."""
    rec = confmeta.resolve(display)
    return rec["name"] if rec else display


def _team_entry(team: saveteams.Team) -> dict[str, Any]:
    ident = cfb27._identity(team.name)
    return {
        "name": team.name,
        "school": team.school,
        "abbreviation": team.abbreviation,
        "espn_id": ident.get("espn_id"),
        "logo": ident.get("logo"),
    }


def _base_conferences(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Editor entries straight from the save (no user edits applied)."""
    table: savestruct.ConferenceTable = ctx["table"]
    roster: list[saveteams.Team] = ctx["roster"]

    def names(rows: list[int]) -> list[str]:
        return [roster[r].name for r in rows if r < len(roster)]

    out = []
    for conf in table.conferences:
        if conf.blank:
            continue
        canonical = _canonical(conf.display)
        meta = confmeta.resolve(canonical) or {}
        divisions = []
        for dr in conf.division_rows:
            div = table.divisions[dr]
            divisions.append({"row": dr, "name": div.name or conf.display,
                              "teams": names(div.team_rows)})
        # division-only + no championship = the Independents pool; a
        # conference activated into the blank row is division-only WITH one
        independents = conf.direct_division and not conf.champ_game
        members = names(conf.team_rows)
        out.append({
            "id": _conf_slug(conf.name),
            "row": conf.row,
            "key": conf.name,
            "name": conf.display,
            "champ_game": conf.champ_game,
            "abbr": meta.get("abbr") or conf.display,
            "logo": meta.get("logo"),
            "description": "",
            "in_game": True,
            "independents": independents,
            "divisions": divisions if len(divisions) > 1 else [],
            "teams": members,
            "rivalries": _default_rivalries(conf.name, set(members)),
            "limits": (None if independents
                       else {"min": MIN_TEAMS, "max": MAX_TEAMS}),
        })
    return out


_rivalry_seed: dict[str, list[dict[str, str]]] | None = None


def _default_rivalries(conf_key: str, members: set[str]) -> list[dict[str, Any]]:
    """Seeded protected rivalries for a conference, keyed by its save key and
    filtered to pairs whose teams are both current members."""
    global _rivalry_seed
    if _rivalry_seed is None:
        try:
            raw = json.loads((config.DATA_DIR / "conference_rivalries.json").read_text(encoding="utf-8"))
            _rivalry_seed = {k: v for k, v in raw.items() if isinstance(v, list)}
        except (OSError, ValueError):
            _rivalry_seed = {}
    return [dict(r) for r in _rivalry_seed.get(conf_key, [])
            if r.get("a") in members and r.get("b") in members]


# --- the per-dynasty store ---------------------------------------------------

def _store_path() -> Path:
    return dynasty_paths.current_root() / "conference_setup.json"


def _load_store() -> list[dict[str, Any]] | None:
    path = _store_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("conferences")
        return entries if isinstance(entries, list) else None
    except (OSError, ValueError):
        return None


def _write_store(entries: list[dict[str, Any]] | None) -> None:
    path = _store_path()
    with _lock:
        if entries is None:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 1, "conferences": entries}, indent=2),
                        encoding="utf-8")


def _reconcile(base: list[dict[str, Any]], stored: list[dict[str, Any]],
               all_names: set[str]) -> list[dict[str, Any]]:
    """Overlay stored edits on the save truth.

    Structure (rows, keys, in_game, limits, division rows) always comes from
    the save; user-editable fields and membership come from the store. Teams
    that vanished from the save are dropped; teams the store never saw stay in
    their save conference."""
    by_id = {e["id"]: e for e in stored}
    placed: set[str] = set()
    out: list[dict[str, Any]] = []
    for entry in base:
        s = by_id.get(entry["id"])
        if s is None:
            out.append(entry)
            placed.update(entry["teams"])
            continue
        merged = dict(entry)
        for key in ("name", "champ_game", "abbr", "logo", "description", "rivalries"):
            if s.get(key) is not None:
                merged[key] = s[key]
        teams = [t for t in s.get("teams", entry["teams"]) if t in all_names]
        merged["teams"] = teams
        if entry["divisions"]:
            divs = []
            stored_divs = {d.get("row"): d for d in s.get("divisions") or []}
            for d in entry["divisions"]:
                sd = stored_divs.get(d["row"])
                divs.append({
                    "row": d["row"],
                    "name": (sd or {}).get("name") or d["name"],
                    "teams": [t for t in (sd or {}).get("teams", d["teams"])
                              if t in teams],
                })
            # any member not in a stored division falls into the first one
            assigned = {t for d in divs for t in d["teams"]}
            divs[0]["teams"] += [t for t in teams if t not in assigned]
            merged["divisions"] = divs
        merged["rivalries"] = [r for r in merged.get("rivalries") or []
                               if r.get("a") in all_names and r.get("b") in all_names]
        out.append(merged)
        placed.update(teams)
    for s in stored:  # custom conferences (companion-only)
        if s.get("in_game") or s["id"] in {e["id"] for e in base}:
            continue
        teams = [t for t in s.get("teams", []) if t in all_names]
        out.append({**s, "row": None, "key": None, "in_game": False,
                    "independents": False, "divisions": s.get("divisions") or [],
                    "teams": teams, "limits": None})
        placed.update(teams)
    # teams claimed by an edit in one conference must leave their save home
    seen: set[str] = set()
    for e in out:
        e["teams"] = [t for t in e["teams"] if not (t in seen or seen.add(t))]
        for d in e.get("divisions") or []:
            d["teams"] = [t for t in d["teams"] if t in e["teams"]]
    # ORPHAN RESCUE: a team the save knows but NO entry claims goes back to
    # its save conference. A stored setup can otherwise strand teams forever:
    # an entry saved while an older build misparsed a conference as empty
    # (observed: a realigned save whose American division list is empty; the
    # store then held American with zero teams) keeps overriding the now
    # correctly parsed membership, and the teams vanish from every conference
    # while still appearing in the polls.
    home_of = {t: e["id"] for e in base for t in e["teams"]}
    by_id_out = {e["id"]: e for e in out}
    for t in sorted(all_names - seen):
        e = by_id_out.get(home_of.get(t))
        if e is None:
            continue
        e["teams"].append(t)
        if e.get("divisions"):
            e["divisions"][0]["teams"].append(t)
    return out


# --- validation ---------------------------------------------------------------

_DASHES = str.maketrans({"–": "-", "—": "-"})


def _clean(s: Any, cap: int, what: str, problems: list[str]) -> str:
    s = str(s or "").translate(_DASHES).strip()
    if not s:
        problems.append(f"{what} is required")
    try:
        s.encode("latin1")
    except UnicodeEncodeError:
        problems.append(f"{what} has characters the game cannot store")
    if len(s) > cap:
        problems.append(f"{what} is longer than {cap} characters")
    return s


def validate(entries: list[dict[str, Any]], all_names: set[str]) -> list[str]:
    problems: list[str] = []
    placed: dict[str, str] = {}
    for e in entries:
        label = e.get("name") or e.get("id") or "conference"
        in_game = bool(e.get("in_game"))
        name_cap = NAME_CAP if in_game else 40
        e["name"] = _clean(e.get("name"), name_cap, f"{label}: name", problems)
        if in_game and not e.get("independents"):
            e["champ_game"] = _clean(e.get("champ_game"), CHAMP_CAP,
                                     f"{label}: championship game", problems)
        teams = e.get("teams") or []
        for t in teams:
            if t not in all_names:
                problems.append(f"{label}: unknown team {t!r}")
            elif t in placed:
                problems.append(f"{label}: {t} is already in {placed[t]}")
            else:
                placed[t] = label
        limits = e.get("limits")
        if limits:
            if len(teams) < limits["min"]:
                problems.append(f"{label}: needs at least {limits['min']} teams (has {len(teams)})")
            if len(teams) > limits["max"]:
                problems.append(f"{label}: holds at most {limits['max']} teams (has {len(teams)})")
        if e.get("independents") and len(teams) > MAX_TEAMS:
            problems.append(f"{label}: the independents pool holds at most {MAX_TEAMS} teams")
        divs = e.get("divisions") or []
        if divs:
            union: list[str] = []
            for d in divs:
                d["name"] = _clean(d.get("name"), DIV_NAME_CAP,
                                   f"{label}: division name", problems)
                union += d.get("teams") or []
                if len(d.get("teams") or []) > MAX_TEAMS:
                    problems.append(f"{label}: division {d['name']} holds at most {MAX_TEAMS} teams")
            if sorted(union) != sorted(teams):
                problems.append(f"{label}: divisions must contain every member exactly once")
        for r in e.get("rivalries") or []:
            if r.get("a") not in teams or r.get("b") not in teams:
                problems.append(f"{label}: rivalries must pair two member teams")
    unplaced = all_names - set(placed)
    if unplaced:
        sample = ", ".join(sorted(unplaced)[:4])
        problems.append(f"every team needs a conference ({len(unplaced)} unassigned: {sample}...)")
    return problems


# --- public state -----------------------------------------------------------

def _gate(ctx: dict[str, Any]) -> dict[str, Any]:
    """Writes are allowed only when no regular-season schedule is in play."""
    if os.getenv("CFBMOD_CONFSETUP_FORCE", "").lower() in ("1", "true", "yes"):
        return {"ok": True, "reason": None, "phase": "forced", "week": None}
    from . import pipeline  # lazy: pipeline imports confsetup for the overlay
    weeks = [pipeline.current_pointer().get("week") or 0]
    m = re.search(r"WEEK(\d+)", ctx["path"].name, re.IGNORECASE)
    if m:
        weeks.append(int(m.group(1)))
    week = max(weeks)
    if week == 0:
        return {"ok": True, "reason": None, "phase": "preseason", "week": 0}
    return {"ok": False, "reason": GATE_REASON, "phase": "regular", "week": week}


def get_state() -> dict[str, Any]:
    ctx = _read_table()
    if ctx is None:
        return {"available": False, "writable": False, "apply_gate":
                {"ok": False, "reason": "No CFB 27 save was found.", "phase": None, "week": None},
                "teams": [], "conferences": [], "dirty": False, "gate_notes": []}
    if ctx.get("table") is None:
        # the save decoded but its conference structures did not parse; the
        # editor cannot show or edit alignment, but other pages (polls, the
        # playoff) still work off the same decoded payload
        return {"available": False, "writable": False, "apply_gate":
                {"ok": False, "reason": "This save's conference layout could not be read.",
                 "phase": None, "week": None},
                "teams": [], "conferences": [], "dirty": False,
                "gate_notes": ["The conference structures in this save did not parse."]}
    base = _base_conferences(ctx)
    all_names = {t for e in base for t in e["teams"]}
    stored = _load_store()
    entries = _reconcile(base, stored, all_names) if stored else base
    assignable = sorted(all_names)
    roster_by_name = {t.name: t for t in ctx["roster"]}
    return {
        "available": True,
        "writable": ctx["table"].writable_membership,
        "apply_gate": _gate(ctx),
        "teams": [_team_entry(roster_by_name[n]) for n in assignable],
        "conferences": entries,
        "dirty": stored is not None and entries != base,
        "gate_notes": ctx["table"].notes,
    }


def set_state(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Persist the edits AND apply them straight to the active dynasty's save
    in place: names/titles/division names any week, team moves in the
    offseason. The logo mod is a separate step (build_logo_mod) the caller runs
    next so the UI can show it as its own phase. Applying is best-effort so a
    write hiccup never loses the companion edits."""
    ctx = _read_table()
    if ctx is None:
        raise ValueError("No CFB 27 save was found.")
    if ctx.get("table") is None:
        raise ValueError("This save's conference layout could not be read.")
    base = _base_conferences(ctx)
    all_names = {t for e in base for t in e["teams"]}
    problems = validate(entries, all_names)
    if problems:
        raise ValueError("; ".join(problems[:6]))
    _write_store(entries)
    _overlay_cache.clear()

    apply_summary: dict[str, Any] = {"ok": False, "applied": [], "pending": []}
    try:
        apply_summary = apply_to_current_save()
    except Exception as exc:  # noqa: BLE001 - never fail the Save on a write issue
        apply_summary = {"ok": False, "applied": [], "pending": [],
                         "reason": f"changes saved, but writing to the game failed: {exc}"}

    state = get_state()
    state["last_apply"] = apply_summary
    state["has_custom_logos"] = any(_is_custom_logo(e.get("logo")) for e in entries)
    return state


def reset() -> dict[str, Any]:
    _write_store(None)
    _overlay_cache.clear()
    return get_state()


# --- the alignment overlay (what the rest of the companion consumes) ---------

_overlay_cache: dict[str, Any] = {}


def alignment_overlay() -> dict[str, dict[str, Any]]:
    """team full name -> {conference, division} for the CURRENT setup.

    Conference names are the editor's display names (canonicalized for
    untouched in-game conferences so existing logo/committee lookups keep
    working). Empty when no save/store is available."""
    store_p = _store_path()
    save_p = _save_file()
    key = (
        str(save_p), save_p.stat().st_mtime_ns if save_p and save_p.exists() else 0,
        str(store_p), store_p.stat().st_mtime_ns if store_p.exists() else 0,
    )
    if _overlay_cache.get("key") == key:
        return _overlay_cache["value"]
    out: dict[str, dict[str, Any]] = {}
    state = get_state()
    if state["available"]:
        for e in state["conferences"]:
            conf_name = _canonical(e["name"]) if e.get("in_game") else e["name"]
            if e.get("independents"):
                # the pool is "no conference" to the rest of the companion
                # (playoff auto-bids key off this label), whatever it is named
                conf_name = "FBS Independents"
            div_of = {}
            for d in e.get("divisions") or []:
                for t in d["teams"]:
                    div_of[t] = d["name"]
            for t in e["teams"]:
                out[t] = {"conference": conf_name, "division": div_of.get(t)}
    _overlay_cache["key"] = key
    _overlay_cache["value"] = out
    return out


def apply_overlay(dynasty: dict[str, Any]) -> dict[str, Any]:
    """Rewrite a dynasty dict's conference/division fields to the editor's
    setup (no-op when the user has not edited anything)."""
    if _load_store() is None:
        return dynasty
    over = alignment_overlay()
    if not over:
        return dynasty
    team = dynasty.get("team") or {}
    o = over.get(team.get("name"))
    if o:
        team["conference"] = o["conference"]
        team["division"] = o["division"]
    for row in dynasty.get("all_teams") or []:
        o = over.get(row.get("name"))
        if o:
            row["conference"] = o["conference"]
            row["division"] = o["division"]
    return dynasty


# conference save key -> the game's teamconferences logo-asset slug
_LOGO_SLUGS = {
    "ACC": "acc", "American": "american", "Big_12": "big12", "Big_Ten": "bigten",
    "C_USA": "cusa", "MAC": "mac", "MWC": "mwc", "Pac_12": "pac12",
    "SEC": "sec", "Sun_Belt": "sunbelt", "FBS_Independents": "fbs",
}


# A conference logo override can come from either a user upload or one of the
# game's own historic conference marks (extracted to game_assets). Both are
# "custom" for the purposes of display, the mod export, and the mod-tools panel.
_HISTORIC_URL_PREFIX = "/game-assets/conferences/historic/"


def _is_custom_logo(url: str | None) -> bool:
    url = url or ""
    return url.startswith("/uploads/") or url.startswith(_HISTORIC_URL_PREFIX)


def _upload_path(url: str) -> Path | None:
    """Resolve a logo URL (a user upload or an extracted historic conference
    mark) to its file on disk."""
    if not url:
        return None
    if url.startswith("/uploads/"):
        p = config.UPLOADS_DIR / url[len("/uploads/"):]
    elif url.startswith("/game-assets/"):
        p = config.DATA_DIR / "game_assets" / url[len("/game-assets/"):]
    else:
        return None
    return p if p.exists() else None


def _historic_label(tail: str) -> str:
    """Human label for a historic mark's tail, e.g. "1988_2008" -> "1988 to
    2008", "2023_present" -> "2023 to Present", "pac10_1" -> "Pac 10 1"."""
    if not tail:
        return "Classic"
    parts = tail.split("_")
    if (len(parts) == 2 and re.fullmatch(r"\d{4}", parts[0])
            and (re.fullmatch(r"\d{4}", parts[1]) or parts[1] == "present")):
        end = "Present" if parts[1] == "present" else parts[1]
        return f"{parts[0]} to {end}"
    special = {"pcc": "PCC", "present": "Present", "circle": "Circle"}
    words = []
    for p in parts:
        if p in special:
            words.append(special[p])
        elif re.fullmatch(r"pac\d+", p):
            words.append("Pac " + p[3:])
        else:
            words.append(p if p.isdigit() else p.capitalize())
    return " ".join(words)


def _extract_historic_logos(out_dir: Path) -> list[Path]:
    """Lazy-extract the historic conference marks from the install (used the
    first time the picker is opened on a machine whose art predates them)."""
    try:
        from . import app_settings
        from .assets.extract_art import extract_historic_conferences
        from .assets.frostbite.extract import ImageLibrary
        lib = ImageLibrary(str(app_settings.resolve_game_root()))
        extract_historic_conferences(lib, config.DATA_DIR / "game_assets")
    except Exception:  # noqa: BLE001 - install absent/unreadable; picker stays empty
        return []
    return sorted(out_dir.glob("*.png")) if out_dir.exists() else []


def historic_logos() -> dict[str, Any]:
    """The game's own classic conference marks (from its history tab), grouped
    by the editor's conference key so the identity picker can offer them.
    Extracts them from the install on first call. Available for the five
    conferences the game ships historic art for (Big 12, Big Ten, C-USA, Pac-12,
    SEC)."""
    out_dir = config.DATA_DIR / "game_assets" / "conferences" / "historic"
    files = sorted(out_dir.glob("*.png")) if out_dir.exists() else []
    if not files:
        files = _extract_historic_logos(out_dir)
    slug_to_key = {slug: key for key, slug in _LOGO_SLUGS.items()}
    logos: dict[str, list[dict[str, str]]] = {}
    for f in files:
        slug, _, tail = f.stem.partition("_")
        key = slug_to_key.get(slug)
        if key is None:
            continue
        logos.setdefault(key, []).append({
            "id": f.stem,
            "url": f"{_HISTORIC_URL_PREFIX}{f.name}",
            "label": _historic_label(tail),
        })
    for items in logos.values():
        items.sort(key=lambda x: x["label"])
    return {"available": bool(logos), "logos": logos}


def _collect_logo_edits(mod) -> tuple[list, list[str], list[str]]:
    """Every (asset, uploaded image) pair for conferences whose logo the user
    replaced, plus the named/skipped report lists shared by both exporters."""
    from .assets.frostbite import modbuild

    state = get_state()
    if not state["available"]:
        raise ValueError("No CFB 27 save was found.")
    edits: list = []
    named: list[str] = []
    skipped: list[str] = []
    for e in state["conferences"]:
        path = _upload_path(e.get("logo") or "")
        slug = _LOGO_SLUGS.get(e.get("key"))
        if path is None:
            continue
        if slug is None:
            skipped.append(f"{e['name']}: no game logo slot maps to this conference")
            continue
        variants = [f"teamconferences/assets/tcon_{slug}",
                    f"teamconferences/assets/tcon_{slug}white",
                    f"teamconferences/assets/tcon_{slug}3d"]
        added = 0
        for asset in variants:
            try:
                mod._resolve(asset)  # confirms the asset + a BC7 chunk exist
                edits.append(modbuild.LogoEdit(asset=asset, image_path=path))
                added += 1
            except Exception:  # noqa: BLE001 - variant absent or non-BC7; skip it
                continue
        if added:
            named.append(e["name"])
        else:
            skipped.append(f"{e['name']}: its game logo textures could not be replaced")

    if not edits:
        raise ValueError("No custom conference logos to build. Upload a logo for a "
                         "conference first, then build the mod.")
    return edits, named, skipped


class LogoModUnavailable(ValueError):
    """The texture-encode pipeline needed to build the logo mod is unavailable
    in this build (e.g. numpy or Pillow failed to import). It subclasses
    ValueError so the route reports it as a clean 400, and it is raised only
    after the conference edits have been persisted, so a broken pipeline skips
    the logo textures without losing any of the user's conference changes."""


def _require_asset_pipeline() -> None:
    """Import the texture-encode dependencies up front so a broken or partial
    pipeline fails with a clear, actionable message instead of leaking a raw
    traceback. This is what caught users out: a frozen build missing numpy's
    native dependency raised the misleading "you should not try to import numpy
    from its source directory" ImportError deep in the encode loop, which is
    neither a ValueError nor an OSError, so it escaped as a raw 500. Importing
    bc7enc pulls in numpy at module load, so this also catches native DLL-load
    failures, not just a missing package."""
    try:
        from PIL import Image  # noqa: F401 - presence check only
        from .assets.frostbite import bc7enc  # noqa: F401 - imports numpy at load
    except Exception as exc:  # noqa: BLE001 - any import or native-load failure
        _log.exception("logo mod: texture-encode pipeline unavailable")
        raise LogoModUnavailable(
            "Could not build the logo mod: this build is missing the image "
            "tools it needs to encode logo textures. Your conference names, "
            "abbreviations, and moves were still saved to the game; only the "
            "custom logos were skipped."
        ) from exc


def build_logo_mod(mod_root: str | Path | None = None) -> dict[str, Any]:
    """LEGACY: re-skin the logos into a ModData tree the game loads via
    `-dataPath`. Kept for manual/diagnostic use; the supported path is
    export_logo_fbmod + the MMC Mod Manager, which owns ModData itself."""
    from .assets.frostbite import modbuild

    try:
        mod = modbuild.ConferenceLogoMod(app_settings.resolve_game_root())
    except Exception as exc:  # noqa: BLE001 - install unreadable / not present
        raise ValueError(f"Could not read the CFB 27 install: {exc}") from exc
    edits, named, skipped = _collect_logo_edits(mod)
    _require_asset_pipeline()  # clean message if the encoder can't load

    root = Path(mod_root) if mod_root else (mod.fs.root / "ModData")
    try:
        report = mod.build(edits, root)
    except OSError as exc:
        raise ValueError(f"Could not write the mod ({exc}). If the game is in "
                         "Program Files, run Dynasty+ as administrator or pick a "
                         "writable mod folder.") from exc
    report["conferences"] = named
    report["skipped"] = skipped
    return report


FBMOD_NAME = "DynastyPlus Conference Logos.fbmod"


def export_logo_fbmod(out_path: str | Path | None = None) -> dict[str, Any]:
    """Export every custom conference logo as a Frosty `.fbmod` for the MMC
    Modding Tools (the community's Frosty fork for CFB 27). Unlike the legacy
    ModData build, this never touches the install: the MMC Mod Manager owns
    ModData and the launch. Each re-skinned texture ships the way the Frosty
    editor's own texture import does, as the unchanged ITexture RES plus the
    re-encoded BC7 chunk. Returns a report; raises ValueError when nothing is
    uploaded or the install cannot be read."""
    from .assets.frostbite import dbobject, fbmod, modbuild
    from .assets.frostbite import toc as fbtoc

    try:
        mod = modbuild.ConferenceLogoMod(app_settings.resolve_game_root())
    except Exception as exc:  # noqa: BLE001 - install unreadable / not present
        raise ValueError(f"Could not read the CFB 27 install: {exc}") from exc
    edits, named, skipped = _collect_logo_edits(mod)
    _require_asset_pipeline()  # clean message if the encoder can't load

    resources: list[Any] = []
    seen_res: set[int] = set()
    icon_source: Path | None = None
    for edit in edits:
        info, _ref, payload = mod.encode(edit)
        _info, res_entry, _bundle = mod.lib.texture_res(edit.asset)
        icon_source = icon_source or edit.image_path
        # the RES header is unchanged (same dims/format/mips), shipped anyway
        # to mirror a real Frosty texture import
        if res_entry.res_rid not in seen_res:
            seen_res.add(res_entry.res_rid)
            resources.append(fbmod.ResResource(
                name=edit.asset, data=mod.cas.read(res_entry.cas),
                res_type=res_entry.res_type, res_rid=res_entry.res_rid,
                res_meta=bytes(res_entry.res_meta or b"")))
        if info.mip_count <= 1:
            logical_offset, logical_size = 0, info.chunk_size
        else:  # Frosty's split encoding of dataSize into offset/size masks
            mask = 0
            for i in range(info.mip_count - info.first_mip):
                mask |= 0x03 << (i * 2)
            logical_offset = info.chunk_size & ~mask
            logical_size = info.chunk_size & mask
        resources.append(fbmod.ChunkResource(
            guid=info.chunk_guid, data=payload,
            logical_offset=logical_offset, logical_size=logical_size,
            first_mip=info.first_mip))

    icon = _fbmod_icon(icon_source)
    if icon:
        resources.append(fbmod.EmbeddedResource("Icon", icon))

    try:
        layout = dbobject.parse(fbtoc.read_payload(mod.fs.data / "layout.toc"))
        head = int(layout.get("head") or 0)
    except Exception:  # noqa: BLE001 - version stamp only, never fatal
        head = 0

    details = fbmod.ModDetails(
        title="Dynasty+ Conference Logos",
        description="Custom conference logos: " + ", ".join(named)
                    + ". Exported by Dynasty+. Offline play only.",
    )
    dest = Path(out_path) if out_path else (config.DATA_DIR / "mods" / FBMOD_NAME)
    report = fbmod.write_fbmod(dest, details, resources, game_version=head)
    report["conferences"] = named
    report["skipped"] = skipped
    return report


def _fbmod_icon(image_path: Path | None) -> bytes | None:
    """A small PNG icon for the mod manager's list (WPF renders png/jpg)."""
    if image_path is None:
        return None
    try:
        from io import BytesIO

        from PIL import Image
        img = Image.open(image_path).convert("RGBA")
        img.thumbnail((128, 128))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:  # noqa: BLE001 - icon is cosmetic, never fail the export
        return None


def conference_registry() -> dict[str, dict[str, Any]]:
    """Renamed/custom conferences for /api/conferences (logos + abbrs)."""
    state = get_state()
    if not state["available"]:
        return {}
    out = {}
    for e in state["conferences"]:
        name = _canonical(e["name"]) if e.get("in_game") else e["name"]
        known = confmeta.resolve(name)
        if known and known["name"] == name and not e.get("logo"):
            continue  # stock conference, nothing to add
        out[name] = {
            "name": name,
            "id": (known or {}).get("id"),
            "abbr": e.get("abbr") or name,
            "logo": e.get("logo") or (known or {}).get("logo"),
            "custom": not e.get("in_game"),
        }
    return out


# --- apply to the current save (in place) -------------------------------------

def _backup_once(path: Path) -> Path | None:
    """Preserve the pristine original of a save the first time Dynasty+ patches
    it, so a bad write can never lose the user's dynasty. Kept out of the saves
    folder so the game never lists it."""
    backups = config.DATA_DIR / "save_backups"
    dst = backups / f"{path.name}.original"
    if dst.exists():
        return dst
    try:
        backups.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(path.read_bytes())
        return dst
    except OSError:
        return None


def apply_to_current_save() -> dict[str, Any]:
    """Patch the active dynasty's CURRENT save in place with the setup.

    Conference names, championship titles, and division names are written every
    week (schedule-safe). Team moves and division membership changes only write
    in the preseason/offseason (they change the generated schedule); otherwise
    they are skipped and reported as pending. The original save is backed up
    once before the first write. Returns a summary (never raises for a no-op)."""
    ctx = _read_table()
    if ctx is None:
        raise ValueError("No CFB 27 save was found.")
    state = get_state()
    if not state["writable"]:
        return {"ok": False, "saved_to": None, "applied": [], "pending": [],
                "reason": "The save's conference tables could not be parsed confidently; "
                          "nothing was written to the game."}
    gate = _gate(ctx)

    table: savestruct.ConferenceTable = ctx["table"]
    rows_by_name: dict[str, int] = ctx["rows_by_name"]
    by_row = {c.row: c for c in table.conferences}
    payload = bytearray(ctx["payload"])
    applied: list[str] = []
    pending: list[str] = []

    conf_teams: dict[int, list[int]] = {}
    div_teams: dict[int, list[int]] = {}
    for e in state["conferences"]:
        conf = by_row.get(e.get("row"))
        if conf is None:
            continue
        desired = [rows_by_name[t] for t in e["teams"] if t in rows_by_name]
        if desired != conf.team_rows:
            conf_teams[conf.row] = desired
        if e.get("divisions"):
            for d in e["divisions"]:
                want = [rows_by_name[t] for t in d["teams"] if t in rows_by_name]
                if want != table.divisions[d["row"]].team_rows:
                    div_teams[d["row"]] = want
        elif conf.row in conf_teams:
            for dr in conf.division_rows:
                div_teams[dr] = conf_teams[conf.row]

        # names + championship titles + division names: schedule-safe, always write
        renames: dict[str, str] = {}
        if e["name"] != conf.display:
            renames["display"] = e["name"]
        if not e.get("independents") and e.get("champ_game") and e["champ_game"] != conf.champ_game:
            renames["champ_game"] = e["champ_game"]
        if renames:
            savestruct.set_conference_strings(payload, conf, **renames)
            applied.append(f"{e['name']} name" + (" and championship" if "champ_game" in renames else ""))
        for d in e.get("divisions") or []:
            div = table.divisions[d["row"]]
            if d["name"] != (div.name or conf.display):
                savestruct.set_division_strings(payload, div, name=d["name"], display=d["name"])
                applied.append(f"{e['name']} division name")

    # gate ONLY the schedule-affecting membership changes
    if (conf_teams or div_teams) and not gate["ok"]:
        conf_teams.clear()
        div_teams.clear()
        pending.append("Team and division moves apply in the preseason or offseason; "
                       + gate["reason"])

    if conf_teams or div_teams:
        for row in list(conf_teams):
            for dr in by_row[row].division_rows:
                div_teams.setdefault(dr, list(table.divisions[dr].team_rows))
        savestruct.set_memberships(payload, table, conf_teams, div_teams)
        applied.append("conference membership")

    if not applied:
        return {"ok": True, "saved_to": None, "applied": [], "pending": pending,
                "reason": "no in-game changes to write (names match the save)"}

    # verify the patch parses back before touching disk
    check = savestruct.parse(bytes(payload))
    for row, rows in conf_teams.items():
        got = next(c for c in check.conferences if c.row == row)
        if sorted(got.team_rows) != sorted(rows):
            raise RuntimeError("post-patch verification failed; the save was not modified")

    _backup_once(ctx["path"])
    out = container.encode(ctx["raw"], bytes(payload), saved_at=_dt.datetime.now())
    ctx["path"].write_bytes(out)  # IN PLACE: same file the game loads
    _table_cache.clear()
    _overlay_cache.clear()
    return {"ok": True, "saved_to": str(ctx["path"]), "applied": applied, "pending": pending}
