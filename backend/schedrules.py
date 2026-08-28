"""The custom schedule generator: Dynasty+'s regular-season scheduling editor.

An editor tool (ships in BOTH apps, routes ungated): the user sets scheduling
rules, per conference (number of conference games, protected conference
rivalries, optional fixed weeks and locations, division round robins) and
league-wide (up to MAX_NONCON_RIVALS protected non-conference rivals per team,
set symmetrically on both teams, with a week and a location each), and the
companion builds a complete regular season that satisfies them, or explains
exactly why no schedule can.

HOW IT WRITES. The save's SeasonGameStore is a fixed skeleton: one record per
game slot, each carrying its season week (Game.sched_week, decoded 2026-07-11)
and its kickoff day/time slot. The editor never creates, deletes, or moves
records between weeks: it re-points the team refs of existing regular-season
records (saveparse.schedule.set_matchup), so every generated schedule has
exactly the save's own per-week game counts, and every record keeps its week,
kickoff slot, and engine queue wiring. The user's own games stay in the user's
own records (only the opponent changes): the engine's play-your-game wiring is
record-based and the user's bye weeks are part of the save's calendar, so the
user's week pattern is a hard constraint, not a preference.

WHEN IT WRITES. Only while the season is untouched: the apply gate requires
zero official regular-season results in the target save (the preseason, before
any week has been advanced past). Weeks the engine has already locked and
pre-simmed in-session (typically the arrival week's slate) are PINNED: their
matchups are kept and count toward every rule budget, because a locked week's
participation is frozen by team and cannot be re-pointed safely (see
docs/cfb27-schedule-format.md). In the offseason the next season's schedule
does not exist yet, so the editor reports that and applies at the next
preseason instead.

FEASIBILITY. validate() runs the real math before anything is written:
per-conference parity and degree bounds (n teams playing k conference games
needs n*k even and k <= n-1), division round-robin arithmetic, protected
rivalry budgets, non-conference budget realizability (every protected pair
needs a free non-conference slot on BOTH teams), per-week capacity against
the save's own slot counts, fixed-week collisions, and the user's bye
pattern. Then it dry-runs the full generator. Every failure is reported with
a plain explanation and a concrete fix.

Persistence is per dynasty: schedule_rules.json (the rules) and
schedule_plan.json (the last generated plan, applied by apply_plan). The
original save is backed up once before the first write (shared with the
conference editor's backup).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import random
import threading
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import config, confsetup, dynasty_paths
from .saveparse import container, profile
from .saveparse import schedule as savesched

_lock = threading.Lock()

MAX_NONCON_RIVALS = 2       # protected non-conference rivals per team
REG_WEEKS = 15              # season week fields 0..14; shown as Week 1..15
RIVALRY_WEEK = 14           # display week of the last full regular-season week
LOCATIONS = ("rotate", "home_a", "home_b")

GATE_PLAYED = ("Games have already been played this season. The schedule can "
               "only be regenerated before any results are official, from a "
               "preseason save at the start of a season.")
GATE_OVER = ("This season is complete. The game builds next season's schedule "
             "during the new preseason; continue into it in CFB 27, save while "
             "still in the preseason once the schedule exists, then regenerate "
             "from that save.")
GATE_PREGEN = ("The game has not generated this season's schedule yet. In "
               "CFB 27, continue through the preseason until the Week 1 "
               "schedule appears, then save while STILL in the preseason and "
               "Scan again. A preseason save has no locked weeks, so the "
               "generator can rebuild every week, including Week 1.")


# --- reading the save skeleton ----------------------------------------------

def _ctx() -> dict[str, Any] | None:
    """The active dynasty's decoded save plus everything the editor needs.

    Rides confsetup._read_table (one decode per save mtime, shared with the
    conference and poll editors) and adds the parsed game store, the profile
    slot, and the save's own conference alignment."""
    base = confsetup._read_table()
    if base is None:
        return None
    ctx = dict(base)
    try:
        ctx["store"] = savesched.parse(ctx["payload"])
    except ValueError:
        return None
    ctx["slot"] = profile.slot_for(ctx["path"])
    # row -> conference display name, straight from the save's own tables (the
    # same alignment the engine schedules and ranks by). Conference rules are
    # unavailable when the conference tables cannot be parsed.
    conf_of: dict[int, str] = {}
    indep: set[str] = set()
    table = ctx.get("table")
    if table is not None:
        for conf in table.conferences:
            if conf.blank:
                continue
            rows = conf.team_rows or [r for dr in conf.division_rows
                                      for r in table.divisions[dr].team_rows]
            if conf.direct_division and not conf.champ_game:
                indep.add(conf.display)   # the Independents pool: no conference games
            for r in rows:
                conf_of[r] = conf.display
    ctx["conf_of"] = conf_of
    ctx["independent_pools"] = indep
    roster = ctx["roster"]
    ctx["fcs_rows"] = {i for i, t in enumerate(roster) if t.school.startswith("FCS")}
    return ctx


def _user_row(ctx: dict[str, Any]) -> int | None:
    """The user's team row: the profile slot when present, else the registry."""
    slot = ctx.get("slot")
    if slot is not None and 0 <= slot.team_row < len(ctx["roster"]):
        return slot.team_row
    current = dynasty_paths.current_id()
    if current:
        from . import dynasties
        reg = dynasties.get(current) or {}
        school = (reg.get("team") or {}).get("school") or reg.get("school")
        if school:
            for i, t in enumerate(ctx["roster"]):
                if t.school == school or t.name == school:
                    return i
    return None


def _skeleton(ctx: dict[str, Any]) -> dict[str, Any]:
    """The regular-season slot skeleton of the active save.

    slots: every scheduled, non-bowl record with its week; pinned weeks are
    the weeks the engine already locked (any result, official or pre-simmed,
    exists there): their matchups are kept verbatim."""
    store: savesched.GameStore = ctx["store"]
    slots = [g for g in store.games if g.scheduled and g.bowl_row is None]
    official = sum(1 for g in slots if g.official)
    pinned_weeks = sorted({g.sched_week for g in slots if g.has_result})
    by_week: dict[int, list[savesched.Game]] = defaultdict(list)
    for g in slots:
        by_week[g.sched_week].append(g)
    user = _user_row(ctx)
    user_weeks = sorted(g.sched_week for g in slots
                        if user is not None and user in (g.away_row, g.home_row))
    return {
        "slots": slots,
        "by_week": by_week,
        "official": official,
        "pinned_weeks": pinned_weeks,
        "user_row": user,
        "user_weeks": user_weeks,
    }


def _gate(ctx: dict[str, Any], skel: dict[str, Any]) -> dict[str, Any]:
    """Whether the plan may be written into this save right now.

    An open gate also reports HOW MUCH of the season is rebuildable:
    `full_reset` is True when no week is locked yet (a true preseason save),
    so the generator rebuilds every week including Week 1; when the engine
    has already locked the opening slate (a Week 1 arrival save), those weeks
    stay pinned and `note` tells the user a preseason save lifts that."""
    total = len(skel["slots"])
    # A new season's arrival autosave can predate the engine's schedule
    # generation (observed: a season 2 Week 1 save with 43 scheduled records
    # and the rest on the free chain). A real season is 800+ records; refuse
    # to treat a partial store as the season.
    if 0 < total < 300:
        return {"ok": False, "phase": "pregeneration", "reason": GATE_PREGEN}
    if total == 0:
        # An empty store is either a fresh season whose schedule the game has
        # not generated yet (dynasty creation and early preseason saves), or
        # the offseason after a completed one. The profile slot tells them
        # apart: a fresh season has no record and sits at week 0/1.
        slot = ctx.get("slot")
        fresh = (slot is not None and slot.wins == 0 and slot.losses == 0
                 and slot.week <= 1)
        if fresh:
            return {"ok": False, "phase": "pregeneration", "reason": GATE_PREGEN}
        return {"ok": False, "phase": "offseason", "reason": GATE_OVER}
    if skel["official"] >= total:
        return {"ok": False, "phase": "offseason", "reason": GATE_OVER}
    if skel["official"] > 0:
        return {"ok": False, "phase": "regular", "reason": GATE_PLAYED}
    if skel["user_row"] is None:
        return {"ok": False, "phase": "preseason",
                "reason": "Your program could not be identified in this save, "
                          "so your own games cannot be protected. Re-scan the "
                          "dynasty and try again."}
    gate: dict[str, Any] = {"ok": True, "phase": "preseason", "reason": None,
                            "full_reset": not skel["pinned_weeks"]}
    if skel["pinned_weeks"]:
        weeks_disp = ", ".join(str(w + 1) for w in skel["pinned_weeks"])
        plural = "s" if len(skel["pinned_weeks"]) > 1 else ""
        gate["note"] = (
            f"Week{plural} {weeks_disp} already locked in this save and will "
            "keep the game's own matchups. To rebuild the whole season, "
            "including Week 1, apply to a save made during the preseason "
            "(before the opening week is locked), then load that save in "
            "CFB 27.")
    return gate


# --- the per-dynasty rules store ---------------------------------------------

def _rules_path() -> Path:
    return dynasty_paths.current_root() / "schedule_rules.json"


def _plan_path() -> Path:
    return dynasty_paths.current_root() / "schedule_plan.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _write_json(path: Path, data: dict[str, Any] | None) -> None:
    with _lock:
        if data is None:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _observed_conf_games(ctx: dict[str, Any], skel: dict[str, Any]) -> dict[str, Counter]:
    """conference -> Counter(per-team conference-game count) in the skeleton."""
    conf_of = ctx["conf_of"]
    per_team: Counter = Counter()
    for g in skel["slots"]:
        ca, ch = conf_of.get(g.away_row), conf_of.get(g.home_row)
        if ca and ca == ch and ca not in ctx["independent_pools"]:
            per_team[g.away_row] += 1
            per_team[g.home_row] += 1
    out: dict[str, Counter] = defaultdict(Counter)
    for row, n in per_team.items():
        out[conf_of[row]][n] += 1
    return out


def _default_conf_games(n_teams: int, observed: Counter) -> int:
    """A default conference-game count that is actually schedulable: the
    observed mode, nudged to keep n*k even and k <= n-1."""
    k = observed.most_common(1)[0][0] if observed else min(8, max(1, n_teams - 1))
    k = max(1, min(k, n_teams - 1))
    if (n_teams * k) % 2:
        for cand in (k - 1, k + 1):
            if 1 <= cand <= n_teams - 1 and (n_teams * cand) % 2 == 0:
                return cand
    return k


def _game_rivalries(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """The save's own named rivalry table as team-name pairs, for labeling
    protected games with their real names (Iron Bowl, Bayou Bucket Classic).
    Best-effort: an unparseable store just means no suggested names."""
    from .saveparse import rivalries as saverivalries
    roster = ctx["roster"]
    out = []
    try:
        rows = saverivalries.parse(ctx["payload"])
    except Exception:  # noqa: BLE001 - names are cosmetic, never break setup
        return out
    for r in rows:
        if r.a_row < len(roster) and r.b_row < len(roster):
            out.append({"a": roster[r.a_row].name, "b": roster[r.b_row].name,
                        "name": r.name})
    return out


def _rivalry_name_of(ctx: dict[str, Any]) -> dict[frozenset, str]:
    """pair of team full names -> the game's display name for that rivalry."""
    return {frozenset((r["a"], r["b"])): r["name"] for r in _game_rivalries(ctx)}


def _default_rules(ctx: dict[str, Any], skel: dict[str, Any]) -> dict[str, Any]:
    """Rules mirroring the save: per-conference counts from the skeleton,
    seeded conference rivalries (named from the game's own rivalry table
    when the pair is in it), no protected non-conference rivals."""
    table = ctx.get("table")
    roster = ctx["roster"]
    observed = _observed_conf_games(ctx, skel)
    names = _rivalry_name_of(ctx)
    conferences: dict[str, Any] = {}
    if table is not None:
        for conf in table.conferences:
            if conf.blank or conf.display in ctx["independent_pools"]:
                continue
            rows = conf.team_rows or [r for dr in conf.division_rows
                                      for r in table.divisions[dr].team_rows]
            members = {roster[r].name for r in rows if r < len(roster)}
            seeded = confsetup._default_rivalries(conf.name, members)
            conferences[conf.display] = {
                "games": _default_conf_games(len(members), observed.get(conf.display, Counter())),
                "rivalries": [{"a": r["a"], "b": r["b"], "week": None,
                               "location": "rotate", "primary": False,
                               "name": (_clean_riv_name(r.get("name"))
                                        or names.get(frozenset((r["a"], r["b"]))))}
                              for r in seeded],
                "round_robin_divisions": False,
            }
    return {"version": 1, "conferences": conferences, "nonconference": [], "shuffle": 0}


def _clean_riv_name(value: Any) -> str | None:
    """A protected rivalry's display label: user-editable, cosmetic, capped.
    Empty/whitespace collapses to None (the UI then suggests the game's own
    name for a known pair)."""
    if not isinstance(value, str):
        return None
    name = " ".join(value.split())[:60]
    return name or None


def _merge_rules(defaults: dict[str, Any], stored: dict[str, Any] | None,
                 all_names: set[str]) -> dict[str, Any]:
    """Overlay stored rules on the save-derived defaults. Conferences come
    from the save (a realigned or renamed conference keeps working); stored
    entries for conferences that no longer exist are dropped, and rivalry
    pairs referencing vanished teams are pruned."""
    if not stored:
        return defaults
    out = json.loads(json.dumps(defaults))
    for key, entry in (stored.get("conferences") or {}).items():
        if key not in out["conferences"] or not isinstance(entry, dict):
            continue
        base = out["conferences"][key]
        if isinstance(entry.get("games"), int):
            base["games"] = entry["games"]
        if isinstance(entry.get("round_robin_divisions"), bool):
            base["round_robin_divisions"] = entry["round_robin_divisions"]
        if isinstance(entry.get("rivalries"), list):
            base["rivalries"] = [
                {"a": r.get("a"), "b": r.get("b"),
                 "week": r.get("week") if isinstance(r.get("week"), int) else None,
                 "location": r.get("location") if r.get("location") in LOCATIONS else "rotate",
                 "primary": bool(r.get("primary")),
                 "name": _clean_riv_name(r.get("name"))}
                for r in entry["rivalries"]
                if isinstance(r, dict) and r.get("a") in all_names and r.get("b") in all_names
            ]
    nc = []
    for r in (stored.get("nonconference") or []):
        if not isinstance(r, dict) or r.get("a") not in all_names or r.get("b") not in all_names:
            continue
        nc.append({"a": r["a"], "b": r["b"],
                   "rank": 2 if r.get("rank") == 2 else 1,
                   "week": r.get("week") if isinstance(r.get("week"), int) else None,
                   "location": r.get("location") if r.get("location") in LOCATIONS else "rotate",
                   "name": _clean_riv_name(r.get("name"))})
    out["nonconference"] = nc
    out["shuffle"] = int(stored.get("shuffle") or 0)
    return out


def current_rules(ctx: dict[str, Any], skel: dict[str, Any]) -> dict[str, Any]:
    roster = ctx["roster"]
    all_names = {t.name for i, t in enumerate(roster) if i not in ctx["fcs_rows"]}
    return _merge_rules(_default_rules(ctx, skel), _load_json(_rules_path()), all_names)


# --- feasibility --------------------------------------------------------------

def _n(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _issue(code: str, message: str, fix: str | None = None, *,
           conference: str | None = None) -> dict[str, Any]:
    out = {"code": code, "message": message}
    if fix:
        out["fix"] = fix
    if conference:
        out["conference"] = conference
    return out


def _build_model(ctx: dict[str, Any], skel: dict[str, Any],
                 rules: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Everything the checks and the generator share, plus hard errors found
    while building it. Weeks are 0-based fields internally; rules carry
    display weeks (field + 1)."""
    errors: list[dict[str, Any]] = []
    roster = ctx["roster"]
    conf_of = ctx["conf_of"]
    fcs = ctx["fcs_rows"]
    row_of = {t.name: i for i, t in enumerate(roster)}
    slots = skel["slots"]
    pinned_weeks = set(skel["pinned_weeks"])

    # per-team totals and pinned commitments from the skeleton
    total: Counter = Counter()
    fcs_opp: dict[int, list[int]] = defaultdict(list)
    pinned_games: list[dict[str, Any]] = []
    pinned_conf: Counter = Counter()
    pinned_pairs: set[frozenset] = set()
    pinned_per_team: Counter = Counter()
    for g in slots:
        a, h = g.away_row, g.home_row
        for t, opp in ((a, h), (h, a)):
            if t in fcs:
                continue
            total[t] += 1
            if opp in fcs:
                fcs_opp[t].append(opp)
        if g.sched_week in pinned_weeks:
            pinned_games.append({"a": a, "h": h, "week": g.sched_week, "index": g.index})
            if a not in fcs and h not in fcs:
                pinned_pairs.add(frozenset((a, h)))
                if conf_of.get(a) and conf_of.get(a) == conf_of.get(h) \
                        and conf_of[a] not in ctx["independent_pools"]:
                    pinned_conf[a] += 1
                    pinned_conf[h] += 1
            for t in (a, h):
                if t not in fcs:
                    pinned_per_team[t] += 1

    # pinned FCS games consume that team's FCS budget
    pinned_fcs: Counter = Counter()
    for pg in pinned_games:
        for t, opp in ((pg["a"], pg["h"]), (pg["h"], pg["a"])):
            if t not in fcs and opp in fcs:
                pinned_fcs[t] += 1

    # conference membership by rules key
    members: dict[str, list[int]] = {}
    divisions: dict[str, list[list[int]]] = {}
    table = ctx.get("table")
    if table is not None:
        for conf in table.conferences:
            if conf.blank or conf.display in ctx["independent_pools"]:
                continue
            rows = conf.team_rows or [r for dr in conf.division_rows
                                      for r in table.divisions[dr].team_rows]
            members[conf.display] = [r for r in rows if r < len(roster)]
            divs = [[r for r in table.divisions[dr].team_rows if r < len(roster)]
                    for dr in conf.division_rows]
            divisions[conf.display] = [d for d in divs if d] if len(divs) > 1 else []

    k_of: dict[int, int] = {}   # per-team conference game target (0 for independents)
    for cname, rows in members.items():
        k = int((rules["conferences"].get(cname) or {}).get("games") or 0)
        for r in rows:
            k_of[r] = k

    # capacities: slots per week, minus the pinned weeks (kept verbatim)
    capacity = {w: len(gs) for w, gs in skel["by_week"].items() if w not in pinned_weeks}

    model = {
        "roster": roster, "row_of": row_of, "conf_of": conf_of, "fcs": fcs,
        "indep_pools": set(ctx["independent_pools"]),
        "members": members, "divisions": divisions, "k_of": k_of,
        "total": total, "fcs_opp": fcs_opp,
        "pinned_weeks": pinned_weeks, "pinned_games": pinned_games,
        "pinned_conf": pinned_conf, "pinned_fcs": pinned_fcs,
        "pinned_pairs": pinned_pairs, "pinned_per_team": pinned_per_team,
        "capacity": capacity,
        "user_row": skel["user_row"],
        "user_weeks": [w for w in skel["user_weeks"] if w not in pinned_weeks],
        "year": (ctx.get("slot").year if ctx.get("slot") else None) or 2026,
    }
    return model, errors


def _check_rules(ctx: dict[str, Any], skel: dict[str, Any],
                 rules: dict[str, Any]) -> tuple[list[dict], list[dict], dict]:
    """All static feasibility checks. Returns (errors, warnings, model)."""
    model, errors = _build_model(ctx, skel, rules)
    warnings: list[dict[str, Any]] = []
    roster = model["roster"]
    row_of = model["row_of"]
    conf_of = model["conf_of"]
    user = model["user_row"]

    fixed_by_team: dict[int, dict[int, str]] = defaultdict(dict)  # row -> week -> label
    fixed_per_week: Counter = Counter()
    primary_of: dict[int, str] = {}
    protected_nc: Counter = Counter()

    def check_fixed(row: int, week_field: int, label: str) -> None:
        if week_field in model["pinned_weeks"]:
            errors.append(_issue(
                "week_locked",
                f"{label} is set for Week {week_field + 1}, but the game has "
                "already locked that week in this save.",
                "Pick a later week, or apply from a save made before entering the season."))
            return
        if not 0 <= week_field < REG_WEEKS:
            errors.append(_issue("week_range", f"{label}: Week {week_field + 1} is "
                                 f"outside the regular season (Weeks 1 to {REG_WEEKS})."))
            return
        if week_field in fixed_by_team[row]:
            errors.append(_issue(
                "week_clash",
                f"{roster[row].school} has two protected games fixed in Week "
                f"{week_field + 1}: {fixed_by_team[row][week_field]} and {label}.",
                "Move one of them to a different week."))
        fixed_by_team[row][week_field] = label
        if user is not None and row == user and week_field not in model["user_weeks"]:
            playable = ", ".join(str(w + 1) for w in model["user_weeks"])
            errors.append(_issue(
                "user_bye",
                f"{label} is fixed for Week {week_field + 1}, but your team has "
                "no game slot that week in the save's calendar (that is one of "
                "your bye weeks).",
                f"Your schedulable weeks are: {playable}."))

    def resolve_pair(r: dict, where: str) -> tuple[int, int] | None:
        a, b = row_of.get(r.get("a")), row_of.get(r.get("b"))
        if a is None or b is None:
            errors.append(_issue("unknown_team", f"{where}: unknown team in "
                                 f"{r.get('a')!r} vs {r.get('b')!r}."))
            return None
        if a == b:
            errors.append(_issue("self_pair", f"{where}: a team cannot play itself."))
            return None
        return a, b

    # --- per conference ---
    for cname, rows in model["members"].items():
        entry = rules["conferences"].get(cname) or {}
        n = len(rows)
        k = int(entry.get("games") or 0)
        label = cname
        if not 1 <= k <= n - 1:
            errors.append(_issue(
                "conf_games_range",
                f"{label}: {k} conference games per team is impossible with "
                f"{n} teams (each team can play at most {n - 1} conference opponents).",
                f"Use a value between 1 and {n - 1}.", conference=cname))
            continue
        if (n * k) % 2:
            errors.append(_issue(
                "conf_games_parity",
                f"{label}: {n} teams each playing {k} conference games needs "
                f"{n * k} team-slots, an odd number, so some team would always "
                "be a game short.",
                f"With {n} teams, use an even number of conference games "
                f"(for example {k - 1 if k > 1 else k + 1}).", conference=cname))
        # protected conference rivalries
        deg: Counter = Counter()
        seen_pairs: set[frozenset] = set()
        for r in entry.get("rivalries") or []:
            pair = resolve_pair(r, f"{label} rivalry")
            if pair is None:
                continue
            a, b = pair
            if conf_of.get(a) != cname or conf_of.get(b) != cname:
                errors.append(_issue(
                    "rivalry_membership",
                    f"{label}: {roster[a].school} vs {roster[b].school} is "
                    "protected here, but both teams are not members of this conference.",
                    "Protect it as a non-conference rivalry instead.", conference=cname))
                continue
            fs = frozenset((a, b))
            if fs in seen_pairs:
                errors.append(_issue("rivalry_duplicate",
                                     f"{label}: {roster[a].school} vs "
                                     f"{roster[b].school} is protected twice.",
                                     conference=cname))
                continue
            seen_pairs.add(fs)
            deg[a] += 1
            deg[b] += 1
            lbl = f"{roster[a].school} vs {roster[b].school}"
            if r.get("primary"):
                for t in (a, b):
                    if t in primary_of:
                        errors.append(_issue(
                            "primary_clash",
                            f"{roster[t].school} has two primary rivals "
                            f"({primary_of[t]} and {lbl}); a team can only "
                            "have one primary rival.",
                            "Mark one of them as a regular protected rivalry."))
                    primary_of[t] = lbl
            week = r.get("week")
            if week is None and r.get("primary"):
                week = RIVALRY_WEEK
            if week is not None:
                for t in (a, b):
                    check_fixed(t, int(week) - 1, lbl)
                fixed_per_week[int(week) - 1] += 1
        for t, d in deg.items():
            eff = d + model["pinned_conf"].get(t, 0)
            if eff > k:
                errors.append(_issue(
                    "rivalry_overflow",
                    f"{label}: {roster[t].school} has {eff} protected or "
                    f"already-locked conference games but only {k} conference "
                    "games per team.",
                    f"Raise {label}'s conference games or drop a protected rivalry.",
                    conference=cname))
        # division round robin arithmetic
        if entry.get("round_robin_divisions") and model["divisions"].get(cname):
            divs = model["divisions"][cname]
            for d in divs:
                if len(d) - 1 > k:
                    errors.append(_issue(
                        "division_round_robin",
                        f"{label}: a full division round robin needs "
                        f"{len(d) - 1} games, more than the {k} conference "
                        "games per team.",
                        f"Raise conference games to at least {len(d) - 1} or "
                        "turn the division round robin off.", conference=cname))
            if len(divs) == 2:
                d1, d2 = len(divs[0]), len(divs[1])
                r1, r2 = k - (d1 - 1), k - (d2 - 1)
                if r1 >= 0 and r2 >= 0 and r1 * d1 != r2 * d2:
                    errors.append(_issue(
                        "division_crossover",
                        f"{label}: with divisions of {d1} and {d2} and a full "
                        f"division round robin, one side needs {r1} crossover "
                        f"games each and the other {r2}, which do not pair up "
                        f"({r1 * d1} against {r2 * d2}).",
                        "Change the conference game count, even out the "
                        "divisions, or turn the round robin off.", conference=cname))

    # --- non-conference rivals ---
    seen_nc: set[frozenset] = set()
    for r in rules.get("nonconference") or []:
        pair = resolve_pair(r, "Non-conference rivalry")
        if pair is None:
            continue
        a, b = pair
        lbl = f"{roster[a].school} vs {roster[b].school}"
        if conf_of.get(a) and conf_of.get(a) == conf_of.get(b) \
                and conf_of[a] not in ctx["independent_pools"]:
            errors.append(_issue(
                "nc_same_conference",
                f"{lbl} share a conference ({conf_of[a]}), so they cannot be "
                "non-conference rivals.",
                f"Protect the game inside {conf_of[a]}'s rules instead."))
            continue
        fs = frozenset((a, b))
        if fs in seen_nc:
            errors.append(_issue("nc_duplicate", f"{lbl} is protected twice."))
            continue
        seen_nc.add(fs)
        protected_nc[a] += 1
        protected_nc[b] += 1
        if r.get("rank") == 1:
            for t in (a, b):
                if t in primary_of:
                    errors.append(_issue(
                        "primary_clash",
                        f"{roster[t].school} has two primary rivals "
                        f"({primary_of[t]} and {lbl}); a team can only have one.",
                        "Make one of them the number 2 rival."))
                primary_of[t] = lbl
        week = r.get("week")
        if week is None and r.get("rank") == 1:
            week = RIVALRY_WEEK
        if week is not None:
            for t in (a, b):
                check_fixed(t, int(week) - 1, lbl)
            fixed_per_week[int(week) - 1] += 1
    for t, n in protected_nc.items():
        if n > MAX_NONCON_RIVALS:
            errors.append(_issue(
                "nc_cap",
                f"{roster[t].school} has {n} protected non-conference rivals; "
                f"the maximum is {MAX_NONCON_RIVALS}."))

    # --- budgets: total games = conference + FCS + non-conference ---
    conf_pool_deficit: dict[str, int] = {}
    nc_budget: dict[int, int] = {}
    for t, tot in model["total"].items():
        k = model["k_of"].get(t, 0)
        n_fcs = len(model["fcs_opp"].get(t, []))
        budget = tot - k - n_fcs
        nc_budget[t] = budget
        if budget < 0:
            errors.append(_issue(
                "budget_negative",
                f"{roster[t].school} plays {tot} games in this save's calendar "
                f"but the rules ask for {k} conference games plus "
                f"{_n(n_fcs, 'FCS game')}, which already exceeds that.",
                f"Lower {conf_of.get(t, 'the')} conference games."))
        elif protected_nc.get(t, 0) > budget:
            errors.append(_issue(
                "budget_rivals",
                f"{roster[t].school} has "
                f"{_n(protected_nc[t], 'protected non-conference rival')} but "
                f"only {_n(budget, 'non-conference slot')} ({tot} games, "
                f"{k} conference, {n_fcs} FCS).",
                f"Lower {conf_of.get(t, 'their')} conference games or drop a "
                "protected rival."))
    open_total = sum(v for v in nc_budget.values() if v > 0)
    if open_total % 2:
        warnings.append(_issue(
            "nc_parity",
            "The non-conference slots across all teams do not pair up evenly; "
            "one team will end a game short unless a conference count changes.",
            "Adjust one conference's game count by one."))
    # every conference's outward demand must be coverable by the rest of FBS
    for cname, rows in model["members"].items():
        inside = sum(max(0, nc_budget.get(t, 0) - protected_nc.get(t, 0)) for t in rows)
        outside = sum(max(0, nc_budget.get(t, 0) - protected_nc.get(t, 0))
                      for t in nc_budget if conf_of.get(t) != cname)
        if inside > outside:
            errors.append(_issue(
                "nc_pool",
                f"{cname} teams need {inside} non-conference games against "
                f"other leagues, but the rest of FBS only has {outside} open "
                "non-conference slots.",
                f"Raise {cname}'s conference games or lower another "
                "conference's.", conference=cname))
            conf_pool_deficit[cname] = inside - outside

    # --- weekly capacity ---
    for w, n in fixed_per_week.items():
        cap = model["capacity"].get(w, 0)
        if n > cap:
            errors.append(_issue(
                "week_capacity",
                f"Week {w + 1} has {_n(n, 'game')} fixed to it but the save's "
                f"calendar only has {_n(cap, 'game slot')} that week.",
                "Move some fixed games to other weeks."))
    for t, tot in model["total"].items():
        need = tot - model["pinned_per_team"].get(t, 0)
        avail = (len(model["user_weeks"]) if t == user
                 else len(model["capacity"]))
        if need > avail:
            errors.append(_issue(
                "team_weeks",
                f"{roster[t].school} needs {need} game weeks but only {avail} "
                "weeks are open in the save's calendar."))

    return errors, warnings, model


# --- generation ---------------------------------------------------------------

class _Infeasible(Exception):
    def __init__(self, issue: dict[str, Any]):
        super().__init__(issue["message"])
        self.issue = issue


def _pair_up(rng: random.Random, degrees: dict[int, int],
             allowed, forbidden: set[frozenset],
             what: str, namer=None) -> list[tuple[int, int]]:
    """Realize a degree sequence as a simple graph: every team t appears in
    exactly degrees[t] edges, no duplicate pairs, no forbidden pairs, and
    every pair passes allowed(a, b).

    Havel-Hakimi greedy (most-constrained team first, partners by remaining
    demand), which is exact for unconstrained graphical sequences and handles
    the dense edge cases (a full round robin has exactly one realization) that
    defeat random pairing. Randomized tie-breaks plus a 2-swap shuffle pass
    give schedule variety across seeds; restarts cover the rare greedy dead
    end. Raises _Infeasible naming the stuck team when no realization exists."""
    if sum(degrees.values()) % 2:
        raise _Infeasible(_issue(
            "pairing_parity",
            f"{what}: the game slots do not pair up evenly (an odd number of "
            "team-slots)."))
    stuck_team = None
    for _restart in range(60):
        rem = {t: d for t, d in degrees.items() if d > 0}
        adj: set[frozenset] = set(forbidden)
        edges: list[tuple[int, int]] = []
        ok = True
        while rem:
            # the team with the FEWEST remaining options relative to its need
            def pressure(t: int) -> tuple:
                opts = sum(1 for u in rem if u != t and rem[u] > 0
                           and frozenset((t, u)) not in adj and allowed(t, u))
                return (opts - rem[t], rng.random())
            t = min(rem, key=pressure)
            need = rem.pop(t)
            if need == 0:
                continue
            cands = [u for u in rem if rem[u] > 0
                     and frozenset((t, u)) not in adj and allowed(t, u)]
            if len(cands) < need:
                stuck_team = (t, need, len(cands))
                ok = False
                break
            cands.sort(key=lambda u: (-rem[u], rng.random()))
            for u in cands[:need]:
                edges.append((t, u))
                adj.add(frozenset((t, u)))
                rem[u] -= 1
        if ok:
            # shuffle pass: random 2-swaps for variety, constraints preserved
            for _ in range(len(edges) * 2):
                i, j = rng.randrange(len(edges)), rng.randrange(len(edges))
                if i == j:
                    continue
                (a, b), (c, d) = edges[i], edges[j]
                for na, nb, nc, nd in ((a, c, b, d), (a, d, c, b)):
                    if (na != nb and nc != nd
                            and frozenset((na, nb)) != frozenset((nc, nd))
                            and frozenset((na, nb)) not in adj and allowed(na, nb)
                            and frozenset((nc, nd)) not in adj and allowed(nc, nd)):
                        adj.discard(frozenset((a, b)))
                        adj.discard(frozenset((c, d)))
                        adj.add(frozenset((na, nb)))
                        adj.add(frozenset((nc, nd)))
                        edges[i], edges[j] = (na, nb), (nc, nd)
                        break
            return edges
    t, need, have = stuck_team
    who = namer(t) if namer else f"team {t}"
    raise _Infeasible(_issue(
        "pairing_stuck",
        f"{what}: {who} needs {need} more opponents but only {have} eligible "
        "teams still have open slots.",
        "Loosen a protected rivalry or adjust the conference game counts."))


def _conference_edges(rng: random.Random, model: dict[str, Any],
                      rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Every conference game as an unordered pair, honoring protected
    rivalries, division round robins, and the per-team count."""
    roster = model["roster"]
    row_of = model["row_of"]
    games: list[dict[str, Any]] = []
    for cname, rows in model["members"].items():
        entry = rules["conferences"].get(cname) or {}
        k = int(entry.get("games") or 0)
        div_of: dict[int, int] = {}
        for i, d in enumerate(model["divisions"].get(cname) or []):
            for t in d:
                div_of[t] = i
        fixed_pairs: set[frozenset] = set(model["pinned_pairs"])
        deg = {t: k - model["pinned_conf"].get(t, 0) for t in rows}
        # protected rivalries and division round robins are placed first
        for r in entry.get("rivalries") or []:
            a, b = row_of.get(r["a"]), row_of.get(r["b"])
            if a is None or b is None or frozenset((a, b)) in fixed_pairs:
                continue
            week = r.get("week")
            if week is None and r.get("primary"):
                week = RIVALRY_WEEK
            games.append({"a": a, "b": b, "conf": cname,
                          "week": (int(week) - 1) if week is not None else None,
                          "location": r.get("location") or "rotate",
                          "tag": "rivalry"})
            fixed_pairs.add(frozenset((a, b)))
            deg[a] -= 1
            deg[b] -= 1
        if entry.get("round_robin_divisions") and model["divisions"].get(cname):
            for d in model["divisions"][cname]:
                for i, a in enumerate(d):
                    for b in d[i + 1:]:
                        if frozenset((a, b)) in fixed_pairs:
                            continue
                        games.append({"a": a, "b": b, "conf": cname, "week": None,
                                      "location": None, "tag": "division"})
                        fixed_pairs.add(frozenset((a, b)))
                        deg[a] -= 1
                        deg[b] -= 1
        for t, d in deg.items():
            if d < 0:
                raise _Infeasible(_issue(
                    "conf_over", f"{cname}: {roster[t].school} is committed to "
                    f"more conference games than the {k} allowed."))
        crossover_only = bool(entry.get("round_robin_divisions")) and bool(div_of)

        def allowed(a: int, b: int, _div=div_of, _cross=crossover_only) -> bool:
            if _cross and _div.get(a) == _div.get(b):
                return False
            return True

        for a, b in _pair_up(rng, deg, allowed, fixed_pairs, f"{cname} schedule",
                             namer=lambda t: roster[t].school):
            games.append({"a": a, "b": b, "conf": cname, "week": None,
                          "location": None, "tag": "conference"})
    return games


def _nonconference_edges(rng: random.Random, model: dict[str, Any],
                         rules: dict[str, Any],
                         existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Protected non-conference rivals, kept FCS games, and cross-conference
    filler to bring every team to its calendar total."""
    roster = model["roster"]
    row_of = model["row_of"]
    conf_of = model["conf_of"]
    games: list[dict[str, Any]] = []
    used_pairs: set[frozenset] = set(model["pinned_pairs"])
    for g in existing:
        used_pairs.add(frozenset((g["a"], g["b"])))
    remaining = {}
    for t, tot in model["total"].items():
        remaining[t] = (tot - model["k_of"].get(t, 0)
                        - len(model["fcs_opp"].get(t, []))
                        - _pinned_nc(model, t))
    # protected rivals first
    for r in rules.get("nonconference") or []:
        a, b = row_of.get(r["a"]), row_of.get(r["b"])
        if a is None or b is None:
            continue
        if frozenset((a, b)) in used_pairs:
            remaining[a] = remaining.get(a, 0)  # pinned game already covers it
            continue
        week = r.get("week")
        if week is None and r.get("rank") == 1:
            week = RIVALRY_WEEK
        games.append({"a": a, "b": b, "conf": None,
                      "week": (int(week) - 1) if week is not None else None,
                      "location": r.get("location") or "rotate",
                      "tag": "rival", "rank": r.get("rank") or 1})
        used_pairs.add(frozenset((a, b)))
        remaining[a] = remaining.get(a, 1) - 1
        remaining[b] = remaining.get(b, 1) - 1
    # FCS games keep their original opponents (a placeholder row can repeat)
    for t, opps in model["fcs_opp"].items():
        keep = len(opps) - model["pinned_fcs"].get(t, 0)
        for opp in opps[:max(0, keep)]:
            games.append({"a": t, "b": opp, "conf": None, "week": None,
                          "location": "home_a", "tag": "fcs"})
    # cross-conference filler
    deg = {t: d for t, d in remaining.items() if d > 0}
    for t, d in remaining.items():
        if d < 0:
            raise _Infeasible(_issue(
                "budget_negative",
                f"{roster[t].school} is committed to more games than their "
                f"{model['total'][t]} calendar slots."))

    indep = model["indep_pools"]

    def allowed(a: int, b: int) -> bool:
        ca, cb = conf_of.get(a), conf_of.get(b)
        if ca and cb and ca == cb and ca not in indep:
            return False
        return True

    for a, b in _pair_up(rng, deg, allowed, used_pairs, "The non-conference slate",
                         namer=lambda t: roster[t].school):
        games.append({"a": a, "b": b, "conf": None, "week": None,
                      "location": None, "tag": "nonconference"})
    return games


def _pinned_nc(model: dict[str, Any], t: int) -> int:
    """Pinned games of t that are neither conference games nor FCS games."""
    n = 0
    for pg in model["pinned_games"]:
        if t not in (pg["a"], pg["h"]):
            continue
        opp = pg["h"] if pg["a"] == t else pg["a"]
        if opp in model["fcs"]:
            continue
        ca, cb = model["conf_of"].get(t), model["conf_of"].get(opp)
        if ca and ca == cb and ca not in model["indep_pools"]:
            continue
        n += 1
    return n


def _assign_weeks(rng: random.Random, model: dict[str, Any],
                  games: list[dict[str, Any]]) -> None:
    """Give every game a week: fixed weeks honored, the user's games on the
    user's own calendar weeks, at most one game per FBS team per week, and
    EXACTLY as many games per week as the save has slots (the skeleton is
    filled in place, so capacities are exact).

    Min-conflicts local search: fixed games consume their week's capacity up
    front; every flexible game starts on a random week drawn from the exact
    remaining capacity multiset, then conflicted games swap weeks pairwise
    (swaps keep every week's count exact) until no team plays twice in a week
    and the user's games sit on the user's own weeks. Restarts with fresh
    randomizations; raises _Infeasible naming the worst conflict when the
    search cannot converge."""
    fcs = model["fcs"]
    user = model["user_row"]
    user_weeks = set(model["user_weeks"])
    roster = model["roster"]

    fixed = [g for g in games if g.get("week") is not None]
    flex = [g for g in games if g.get("week") is None]
    capacity = dict(model["capacity"])
    for g in fixed:
        capacity[g["week"]] = capacity.get(g["week"], 0) - 1
        if capacity[g["week"]] < 0:
            raise _Infeasible(_issue(
                "week_capacity",
                f"Week {g['week'] + 1} has more fixed games than the save has "
                "slots there.",
                "Move a fixed game to another week."))

    base_occ: Counter = Counter()   # (team, week) -> games, from pinned + fixed
    for pg in model["pinned_games"]:
        for t in (pg["a"], pg["h"]):
            if t not in fcs:
                base_occ[(t, pg["week"])] += 1
    for g in fixed:
        for t in (g["a"], g["b"]):
            if t not in fcs:
                base_occ[(t, g["week"])] += 1

    pool = [w for w, c in capacity.items() for _ in range(c)]
    if len(pool) != len(flex):
        raise _Infeasible(_issue(
            "slot_mismatch",
            f"The rules produce {len(flex) + len(fixed)} games for "
            f"{len(pool) + len(fixed)} save slots; adjust a conference's game "
            "count so the totals line up."))

    HARD = 1000

    def gcost(g, w, occ) -> int:
        c = 0
        for t in (g["a"], g["b"]):
            if t not in fcs:
                c += occ[(t, w)]
        if user is not None and user in (g["a"], g["b"]) and w not in user_weeks:
            c += HARD
        return c

    worst: tuple | None = None
    for _restart in range(25):
        rng.shuffle(pool)
        occ = Counter(base_occ)
        for g, w in zip(flex, pool):
            g["_week"] = w
            for t in (g["a"], g["b"]):
                if t not in fcs:
                    occ[(t, w)] += 1

        def conflicted() -> list:
            out = []
            for g in flex:
                w = g["_week"]
                for t in (g["a"], g["b"]):
                    if t not in fcs and occ[(t, w)] > 1:
                        out.append(g)
                        break
                else:
                    if user is not None and user in (g["a"], g["b"]) and w not in user_weeks:
                        out.append(g)
            return out

        bad = conflicted()
        step_budget = min(40000, 300 + len(flex) * 50)
        for _step in range(step_budget):
            if not bad:
                break
            g = bad[rng.randrange(len(bad))]
            w1 = g["_week"]
            # lift g out of the occupancy so costs read cleanly
            for t in (g["a"], g["b"]):
                if t not in fcs:
                    occ[(t, w1)] -= 1
            cur = gcost(g, w1, occ)
            best_h, best_delta = None, 0
            for _try in range(40):
                h = flex[rng.randrange(len(flex))]
                if h is g:
                    continue
                w2 = h["_week"]
                if w2 == w1:
                    continue
                for t in (h["a"], h["b"]):
                    if t not in fcs:
                        occ[(t, w2)] -= 1
                delta = (gcost(g, w2, occ) + gcost(h, w1, occ)) \
                    - (cur + gcost(h, w2, occ))
                for t in (h["a"], h["b"]):
                    if t not in fcs:
                        occ[(t, w2)] += 1
                if delta < best_delta or (best_h is None and delta == 0
                                          and rng.random() < 0.2):
                    best_h, best_delta = h, delta
                    if delta < 0 and rng.random() < 0.7:
                        break
            if best_h is not None:
                w2 = best_h["_week"]
                for t in (best_h["a"], best_h["b"]):
                    if t not in fcs:
                        occ[(t, w2)] -= 1
                        occ[(t, w1)] += 1
                best_h["_week"] = w1
                g["_week"] = w2
                for t in (g["a"], g["b"]):
                    if t not in fcs:
                        occ[(t, w2)] += 1
            else:
                for t in (g["a"], g["b"]):
                    if t not in fcs:
                        occ[(t, w1)] += 1
            if _step % 200 == 199:
                bad = conflicted()
            elif best_h is not None:
                bad = conflicted() if len(bad) < 4 else bad
        bad = conflicted()
        if not bad:
            for g in fixed:
                g.pop("_week", None)
            for g in flex:
                g["week"] = g.pop("_week")
            return
        g = bad[0]
        a = roster[g["a"]].school if g["a"] < len(roster) else "?"
        b = roster[g["b"]].school if g["b"] < len(roster) else "?"
        worst = (a, b)
        for g2 in flex:
            g2.pop("_week", None)
    a, b = worst
    raise _Infeasible(_issue(
        "week_stuck",
        f"No week could be found for {a} vs {b}: every arrangement leaves a "
        "team playing twice in one week or a week over its slot count.",
        "Loosen a fixed week, or shuffle and regenerate."))


def _orient(rng: random.Random, model: dict[str, Any],
            games: list[dict[str, Any]]) -> None:
    """Decide home teams: rules first (rotate alternates by season year),
    FCS games at the FBS home, then balance everyone else."""
    fcs = model["fcs"]
    year = model["year"]
    home_ct: Counter = Counter()
    total_ct: Counter = Counter()
    for pg in model["pinned_games"]:
        if pg["h"] not in fcs:
            home_ct[pg["h"]] += 1
        for t in (pg["a"], pg["h"]):
            if t not in fcs:
                total_ct[t] += 1
    undecided = []
    for g in games:
        for t in (g["a"], g["b"]):
            if t not in fcs:
                total_ct[t] += 1
        loc = g.get("location")
        if g["tag"] == "fcs" or loc == "home_a":
            g["home"], g["away"] = g["a"], g["b"]
        elif loc == "home_b":
            g["home"], g["away"] = g["b"], g["a"]
        elif loc == "rotate":
            first, second = sorted((g["a"], g["b"]))
            g["home"] = first if year % 2 == 0 else second
            g["away"] = second if g["home"] == first else first
        else:
            undecided.append(g)
            continue
        if g["home"] not in fcs:
            home_ct[g["home"]] += 1
    rng.shuffle(undecided)
    for g in undecided:
        a, b = g["a"], g["b"]
        da = home_ct[a] - total_ct[a] / 2
        db = home_ct[b] - total_ct[b] / 2
        home = a if da < db or (da == db and rng.random() < 0.5) else b
        g["home"] = home
        g["away"] = b if home == a else a
        home_ct[home] += 1
    # repair pass: flip flexible games between over-homed and under-homed teams
    for _ in range(3):
        changed = False
        for g in undecided:
            h, aw = g["home"], g["away"]
            if home_ct[h] - 1 >= (total_ct[h] + 1) // 2 + 1 or \
               home_ct[aw] + 1 <= total_ct[aw] // 2 - 1:
                if home_ct[h] > home_ct[aw] + 1:
                    g["home"], g["away"] = aw, h
                    home_ct[h] -= 1
                    home_ct[aw] += 1
                    changed = True
        if not changed:
            break


def _map_records(model: dict[str, Any], skel: dict[str, Any],
                 games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach every generated game to a save record of its week. The user's
    game takes the user's own record; a matchup the engine already had that
    week keeps its record (and so its kickoff slot); the rest fill in a
    stable order."""
    user = model["user_row"]
    plan: list[dict[str, Any]] = []
    by_week: dict[int, list] = defaultdict(list)
    for g in games:
        by_week[g["week"]].append(g)
    for w, gs in sorted(by_week.items()):
        slots = [s for s in skel["by_week"][w]]
        if len(slots) != len(gs):
            raise _Infeasible(_issue(
                "slot_mismatch",
                f"Week {w + 1} produced {len(gs)} games for {len(slots)} save "
                "slots; this is a bug, regenerate with shuffle."))
        taken: set[int] = set()
        assigned: dict[int, dict] = {}

        def claim(slot, g) -> None:
            taken.add(slot.index)
            assigned[slot.index] = g

        # 1) the user's game keeps the user's record
        if user is not None:
            ug = next((g for g in gs if user in (g["home"], g["away"])), None)
            us = next((s for s in slots if user in (s.away_row, s.home_row)), None)
            if ug is not None and us is not None:
                claim(us, ug)
        # 2) unchanged matchups keep their record
        want = {frozenset((g["home"], g["away"])): g for g in gs}
        for s in slots:
            if s.index in taken:
                continue
            g = want.get(frozenset((s.home_row, s.away_row)))
            if g is not None and id(g) not in {id(x) for x in assigned.values()}:
                claim(s, g)
        # 3) the rest, deterministically
        rest_g = [g for g in gs if id(g) not in {id(x) for x in assigned.values()}]
        rest_s = [s for s in slots if s.index not in taken]
        rest_s.sort(key=lambda s: (s.kickoff_raw, s.index))
        rest_g.sort(key=lambda g: (g["home"], g["away"]))
        for s, g in zip(rest_s, rest_g):
            claim(s, g)
        for s in slots:
            g = assigned[s.index]
            plan.append({
                "index": s.index, "week": w,
                "home": g["home"], "away": g["away"],
                "tag": g["tag"],
                "changed": (s.home_row, s.away_row) != (g["home"], g["away"]),
            })
    return plan


def _rules_digest(rules: dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps(rules, sort_keys=True).encode()).hexdigest()[:16]


def generate(shuffle: bool = False) -> dict[str, Any]:
    """Validate, then build a full season plan and persist it for apply.
    Returns the preview (or the failure report)."""
    ctx = _ctx()
    if ctx is None:
        return {"available": False, "reason": "No CFB 27 save was found."}
    skel = _skeleton(ctx)
    rules = current_rules(ctx, skel)
    if shuffle:
        rules["shuffle"] = int(rules.get("shuffle") or 0) + 1
        stored = _load_json(_rules_path()) or {}
        stored["shuffle"] = rules["shuffle"]
        _write_json(_rules_path(), stored)
    errors, warnings, model = _check_rules(ctx, skel, rules)
    if errors:
        return {"available": True, "ok": False, "errors": errors,
                "warnings": warnings, "plan": None}
    slot = ctx.get("slot")
    seed_key = f"{dynasty_paths.current_id()}|{slot.season if slot else 0}|{rules['shuffle']}"
    rng = random.Random(int(hashlib.sha1(seed_key.encode()).hexdigest()[:12], 16))
    try:
        conf_games = _conference_edges(rng, model, rules)
        all_games = conf_games + _nonconference_edges(rng, model, rules, conf_games)
        _assign_weeks(rng, model, all_games)
        _orient(rng, model, all_games)
        plan = _map_records(model, skel, all_games)
    except _Infeasible as exc:
        return {"available": True, "ok": False, "errors": [exc.issue],
                "warnings": warnings, "plan": None}
    payload_plan = {
        "version": 1,
        "digest": _rules_digest(rules),
        "save_name": ctx["path"].name,
        "save_mtime": ctx["path"].stat().st_mtime_ns,
        "games": plan,
    }
    _write_json(_plan_path(), payload_plan)
    return {"available": True, "ok": True, "errors": [], "warnings": warnings,
            "plan": _preview(ctx, skel, plan)}


def _preview(ctx: dict[str, Any], skel: dict[str, Any],
             plan: list[dict[str, Any]]) -> dict[str, Any]:
    roster = ctx["roster"]
    user = skel["user_row"]
    fcs = ctx["fcs_rows"]

    def team(row: int) -> dict[str, Any]:
        t = roster[row]
        ident = {}
        try:
            from .saveparse import cfb27
            ident = cfb27._identity(t.name)
        except Exception:  # noqa: BLE001 - identity is cosmetic
            ident = {}
        return {"row": row, "school": t.school, "abbr": t.abbreviation,
                "espn_id": ident.get("espn_id"), "fcs": row in fcs}

    weeks: dict[int, list] = defaultdict(list)
    changed = 0
    for g in plan:
        weeks[g["week"]].append(g)
        changed += 1 if g["changed"] else 0
    pinned = []
    for w in skel["pinned_weeks"]:
        for s in skel["by_week"][w]:
            pinned.append({"week": w, "home": s.home_row, "away": s.away_row})
    out_weeks = []
    for w in sorted(set(list(weeks) + skel["pinned_weeks"])):
        games = []
        for g in sorted(weeks.get(w, []), key=lambda x: x["index"]):
            games.append({
                "home": team(g["home"]), "away": team(g["away"]),
                "tag": g["tag"], "changed": g["changed"],
                "user": user in (g["home"], g["away"]),
            })
        for p in (x for x in pinned if x["week"] == w):
            games.append({"home": team(p["home"]), "away": team(p["away"]),
                          "tag": "locked", "changed": False,
                          "user": user in (p["home"], p["away"])})
        out_weeks.append({"week": w + 1, "games": games,
                          "locked": w in skel["pinned_weeks"]})
    return {"weeks": out_weeks, "changed": changed,
            "total": len(plan) + len(pinned)}


# --- public state / save / apply ----------------------------------------------

def get_state() -> dict[str, Any]:
    ctx = _ctx()
    if ctx is None:
        return {"available": False, "writable": False,
                "reason": "No CFB 27 save was found.",
                "apply_gate": {"ok": False, "phase": None,
                               "reason": "No CFB 27 save was found."}}
    if ctx.get("table") is None:
        return {"available": False, "writable": False,
                "reason": "This save's conference layout could not be read, so "
                          "conference scheduling rules are unavailable.",
                "apply_gate": {"ok": False, "phase": None,
                               "reason": "This save's conference layout could not be read."}}
    skel = _skeleton(ctx)
    rules = current_rules(ctx, skel)
    errors, warnings, model = _check_rules(ctx, skel, rules)
    roster = ctx["roster"]
    observed = _observed_conf_games(ctx, skel)

    def team_entry(row: int) -> dict[str, Any]:
        t = roster[row]
        try:
            from .saveparse import cfb27
            ident = cfb27._identity(t.name)
        except Exception:  # noqa: BLE001
            ident = {}
        return {"row": row, "name": t.name, "school": t.school,
                "abbr": t.abbreviation, "espn_id": ident.get("espn_id"),
                "conference": ctx["conf_of"].get(row),
                "total_games": model["total"].get(row, 0),
                "fcs_games": len(model["fcs_opp"].get(row, []))}

    conferences = []
    for cname, rows in model["members"].items():
        entry = rules["conferences"].get(cname) or {}
        obs = observed.get(cname, Counter())
        conferences.append({
            "name": cname,
            "canonical": confsetup._canonical(cname),
            "teams": [team_entry(r) for r in sorted(rows, key=lambda r: roster[r].school)],
            "games": entry.get("games"),
            "observed_games": dict(sorted(obs.items())),
            "max_games": max(1, len(rows) - 1),
            "rivalries": entry.get("rivalries") or [],
            "round_robin_divisions": bool(entry.get("round_robin_divisions")),
            "divisions": [[roster[r].school for r in d]
                          for d in (model["divisions"].get(cname) or [])],
        })
    conferences.sort(key=lambda c: c["name"])
    independents = [team_entry(r) for r, c in ctx["conf_of"].items()
                    if c in ctx["independent_pools"] and r not in ctx["fcs_rows"]]
    independents.sort(key=lambda t: t["school"])

    plan = _load_json(_plan_path())
    plan_fresh = bool(
        plan and plan.get("digest") == _rules_digest(rules)
        and plan.get("save_name") == ctx["path"].name
        and plan.get("save_mtime") == ctx["path"].stat().st_mtime_ns)

    return {
        "available": True,
        "writable": True,
        "apply_gate": _gate(ctx, skel),
        "user_team": (team_entry(skel["user_row"]) if skel["user_row"] is not None else None),
        "user_weeks": [w + 1 for w in skel["user_weeks"]],
        "weeks": [{"week": w + 1, "slots": len(gs),
                   "locked": w in set(skel["pinned_weeks"])}
                  for w, gs in sorted(skel["by_week"].items())],
        "rivalry_week": RIVALRY_WEEK,
        "max_noncon_rivals": MAX_NONCON_RIVALS,
        "conferences": conferences,
        "independents": independents,
        "nonconference": rules.get("nonconference") or [],
        # the game's own named rivalry table (saveparse/rivalries.py), so the
        # editor can label a protected pair with its real name (Iron Bowl)
        # and offer it wherever the user protects a known pair
        "game_rivalries": _game_rivalries(ctx),
        "feasibility": {"ok": not errors, "errors": errors, "warnings": warnings},
        "plan_ready": plan_fresh,
        "plan_preview": (_preview(ctx, skel,
                                  plan["games"]) if plan_fresh else None),
    }


def set_rules(body: dict[str, Any]) -> dict[str, Any]:
    """Persist the rules draft (validated for shape; feasibility is reported,
    not enforced, so a user can save work in progress)."""
    ctx = _ctx()
    if ctx is None:
        raise ValueError("No CFB 27 save was found.")
    stored = {
        "version": 1,
        "conferences": {},
        "nonconference": [],
        "shuffle": int((_load_json(_rules_path()) or {}).get("shuffle") or 0),
    }
    for key, entry in (body.get("conferences") or {}).items():
        if not isinstance(entry, dict):
            continue
        out: dict[str, Any] = {}
        if isinstance(entry.get("games"), int):
            out["games"] = max(0, min(30, entry["games"]))
        out["round_robin_divisions"] = bool(entry.get("round_robin_divisions"))
        rivs = []
        for r in entry.get("rivalries") or []:
            if not isinstance(r, dict) or not r.get("a") or not r.get("b"):
                continue
            rivs.append({"a": str(r["a"]), "b": str(r["b"]),
                         "week": int(r["week"]) if isinstance(r.get("week"), int) else None,
                         "location": r.get("location") if r.get("location") in LOCATIONS else "rotate",
                         "primary": bool(r.get("primary")),
                         "name": _clean_riv_name(r.get("name"))})
        out["rivalries"] = rivs
        stored["conferences"][str(key)] = out
    for r in body.get("nonconference") or []:
        if not isinstance(r, dict) or not r.get("a") or not r.get("b"):
            continue
        stored["nonconference"].append({
            "a": str(r["a"]), "b": str(r["b"]),
            "rank": 2 if r.get("rank") == 2 else 1,
            "week": int(r["week"]) if isinstance(r.get("week"), int) else None,
            "location": r.get("location") if r.get("location") in LOCATIONS else "rotate",
            "name": _clean_riv_name(r.get("name"))})
    _write_json(_rules_path(), stored)
    _write_json(_plan_path(), None)   # rules changed: stale plan is dropped
    return get_state()


def reset() -> dict[str, Any]:
    _write_json(_rules_path(), None)
    _write_json(_plan_path(), None)
    return get_state()


def apply_plan() -> dict[str, Any]:
    """Write the generated plan into the active dynasty's save, in place.

    Refuses when the gate is closed, when no fresh plan exists, or when the
    save changed since the plan was generated. Verifies the patch by
    re-parsing before touching disk; the pristine original is backed up once
    (shared backup folder with the conference editor)."""
    ctx = _ctx()
    if ctx is None:
        raise ValueError("No CFB 27 save was found.")
    skel = _skeleton(ctx)
    gate = _gate(ctx, skel)
    if not gate["ok"]:
        raise ValueError(gate["reason"])
    plan = _load_json(_plan_path())
    if not plan:
        raise ValueError("No generated schedule to apply. Generate one first.")
    rules = current_rules(ctx, skel)
    if plan.get("digest") != _rules_digest(rules):
        raise ValueError("The rules changed since this schedule was generated. "
                         "Generate again, then apply.")
    if (plan.get("save_name") != ctx["path"].name
            or plan.get("save_mtime") != ctx["path"].stat().st_mtime_ns):
        raise ValueError("The save changed since this schedule was generated. "
                         "Generate again, then apply.")

    store: savesched.GameStore = ctx["store"]
    by_index = {g.index: g for g in store.games}
    payload = bytearray(ctx["payload"])
    changed = 0
    report: list[str] = []
    for g in plan["games"]:
        rec = by_index.get(g["index"])
        if rec is None or rec.bowl_row is not None or not rec.scheduled:
            raise ValueError(f"Plan record {g['index']} no longer matches the "
                             "save; generate again.")
        if (rec.home_row, rec.away_row) == (g["home"], g["away"]):
            continue
        if rec.has_result:
            raise ValueError(f"Record {g['index']} already has a result; "
                             "generate again from the current save.")
        report += savesched.set_matchup(payload, rec,
                                        away_row=g["away"], home_row=g["home"])
        changed += 1

    if changed == 0:
        return {"ok": True, "saved_to": None, "changed": 0,
                "reason": "The generated schedule already matches the save."}

    # verify: re-parse and spot-check every rewritten record
    check = savesched.parse(bytes(payload))
    check_by_index = {g.index: g for g in check.games}
    for g in plan["games"]:
        got = check_by_index[g["index"]]
        if (got.home_row, got.away_row) != (g["home"], g["away"]):
            raise RuntimeError("post-patch verification failed; the save was "
                               "not modified")

    confsetup._backup_once(ctx["path"])
    out = container.encode(ctx["raw"], bytes(payload), saved_at=_dt.datetime.now())
    ctx["path"].write_bytes(out)
    confsetup._table_cache.clear()
    _write_json(_plan_path(), None)
    return {"ok": True, "saved_to": str(ctx["path"]), "changed": changed,
            "report": report[:40]}
