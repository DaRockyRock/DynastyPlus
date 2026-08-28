"""Nonplayoff bowl schedule editor for a custom postseason.

CFB 27 creates 32 ordinary bowl records plus six New Year's Six venue slots
inside its native CFP records. A smaller custom playoff may reserve only some
of those six marquee bowls. This module turns every remaining bowl into one
coherent, editable schedule while keeping playoff teams out of all of them.

The generated plan is frozen per dynasty and season under ``bowls/<year>.json``
so later rankings and completed bowl results never reshuffle future games.
Every disk write uses the same serialized, backup once path as the playoff,
poll, conference, and regular schedule editors.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from . import confsetup, dynasty_paths, playoff
from .saveparse import bowls as savebowls
from .saveparse import cfb27
from .saveparse import conferences as saveconfs
from .saveparse import container
from .saveparse import polls as savepolls
from .saveparse import results as saveresults
from .saveparse import schedule as savesched
from .saveparse import teams as saveteams

_VERSION = 1
_VISIBLE_STATUSES = {"selected", "in_progress", "complete"}
_EDITABLE_STATUSES = {"selected", "in_progress"}


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _plan_path(year: int) -> Path:
    return dynasty_paths.sub("bowls") / f"{int(year)}.json"


def _load_plan(year: int) -> dict[str, Any] | None:
    path = _plan_path(year)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("version") == _VERSION else None


def _save_plan(year: int, assignments: list[dict[str, int]], mode: str) -> None:
    path = _plan_path(year)
    payload = {
        "version": _VERSION,
        "year": int(year),
        "mode": "manual" if mode == "manual" else "auto",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "assignments": assignments,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _catalog_entry(name: str, internal: str = "") -> dict[str, Any]:
    keys = {_norm(name), _norm(internal)}
    for bowl in playoff.BOWLS:
        if keys & {_norm(bowl.get("key")), _norm(bowl.get("name")),
                   _norm(bowl.get("asset"))}:
            return bowl
    asset = _norm(internal) or _norm(name) or "default"
    return {"name": name, "venue": name, "city": "", "asset": asset}


def _reserved_records(state: dict[str, Any]) -> set[int]:
    out: set[int] = set()
    for values in (state.get("plan") or {}).values():
        for value in values or []:
            if isinstance(value, int):
                out.add(value)
    return out


def _reserved_bowl_names(bracket: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    by_key = {str(b.get("key")): b for b in playoff.BOWLS}
    for rnd in bracket.get("rounds") or []:
        for game in rnd.get("games") or []:
            bowl = (game.get("site") or {}).get("bowl") or {}
            catalog = by_key.get(str(bowl.get("key"))) or {}
            for value in (bowl.get("key"), bowl.get("name"), bowl.get("asset"),
                          catalog.get("name"), catalog.get("asset")):
                if value:
                    names.add(_norm(value))
    return names


def _conference_rows(table: saveconfs.ConferenceTable | None) -> dict[int, str]:
    if table is None:
        return {}
    out: dict[int, str] = {}
    for conf in table.conferences:
        if conf.blank:
            continue
        members = list(conf.team_rows)
        if not members:
            members = [row for div in conf.division_rows
                       for row in table.divisions[div].team_rows]
        for row in members:
            out[row] = conf.display
    return out


def _team_catalog(payload: bytes, roster: list[saveteams.Team],
                  table: saveconfs.ConferenceTable | None,
                  bracket: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        ranks = {entry.row: entry.rank for entry in savepolls.parse(payload)}
    except ValueError:
        ranks = {}
    try:
        records = saveresults.build_blocks(payload, user_row=None)["team_records"]
    except ValueError:
        records = {}
    conferences = _conference_rows(table)
    playoff_names = {str(seed.get("team")) for seed in bracket.get("seeds") or []
                     if seed.get("team")}
    out: list[dict[str, Any]] = []
    for row, team in enumerate(roster):
        if not team.name or team.name.upper().startswith("FCS "):
            continue
        ident = cfb27._identity(team.name)
        wins, losses = records.get(row, (0, 0))
        out.append({
            "row": row,
            "name": team.name,
            "school": team.school,
            "abbr": team.abbreviation,
            "conference": conferences.get(row) or ident.get("conference") or "Other",
            "espn_id": ident.get("espn_id"),
            "color": ident.get("color"),
            "alt_color": ident.get("alt_color"),
            "rank": int(ranks.get(row) or 0),
            "wins": int(wins),
            "losses": int(losses),
            "record": f"{wins}-{losses}",
            "bowl_eligible": wins >= 6,
            "playoff": team.name in playoff_names,
        })
    return out


def _slot_catalog(payload: bytes, bracket: dict[str, Any],
                  plan: dict[str, list[int | None]]) -> list[dict[str, Any]]:
    state = {"bracket": bracket, "plan": plan}
    reserved_records = _reserved_records(state)
    reserved_names = _reserved_bowl_names(bracket)
    table = savebowls.parse(payload)
    store = savesched.parse(payload)

    ordinary: list[dict[str, Any]] = []
    used_records = set(reserved_records)
    for game in store.games:
        if game.bowl_row is None or game.index in reserved_records:
            continue
        bowl = table.by_row(game.bowl_row)
        if bowl is None or bowl.is_cfp or not bowl.name or not bowl.internal:
            continue
        catalog = _catalog_entry(bowl.name, bowl.internal)
        if {_norm(bowl.name), _norm(bowl.internal), _norm(catalog.get("asset"))} \
                & reserved_names:
            continue
        ordinary.append({
            "record": game.index,
            "row": bowl.row,
            "name": bowl.name,
            "asset": catalog.get("asset") or "default",
            "venue": catalog.get("venue") or bowl.name,
            "city": catalog.get("city") or "",
            "ny6": False,
            "stadium_handle": bowl.stadium_handle,
            "away_row": game.away_row,
            "home_row": game.home_row,
            "official": bool(game.official),
            "current_week": False,
        })
        used_records.add(game.index)

    # A native NY6 game is a CFP QF or SF record whose venue handle identifies
    # Cotton, Fiesta, Orange, Peach, Rose, or Sugar. A small custom field leaves
    # some of those records unused. They remain safe complete game records and
    # become marquee nonplayoff bowls here.
    cfp_candidates: list[Any] = []
    for game in store.games:
        if game.index in used_records or game.bowl_row is None:
            continue
        bowl = table.by_row(game.bowl_row)
        label = _norm((bowl.name if bowl else "") + (bowl.internal if bowl else ""))
        if bowl is not None and ("quarterfinal" in label or "semifinal" in label):
            cfp_candidates.append(game)

    for pb in table.playoff_bowls:
        catalog = _catalog_entry(pb.name, pb.internal)
        if {_norm(pb.name), _norm(pb.internal), _norm(catalog.get("asset"))} \
                & reserved_names:
            continue
        exact = next((game for game in cfp_candidates
                      if game.index not in used_records
                      and game.venue_uid == pb.stadium_handle), None)
        game = exact or next((candidate for candidate in cfp_candidates
                              if candidate.index not in used_records), None)
        if game is None:
            continue
        used_records.add(game.index)
        ordinary.append({
            "record": game.index,
            "row": game.bowl_row,
            "name": pb.name,
            "asset": catalog.get("asset") or _norm(pb.name),
            "venue": catalog.get("venue") or pb.name,
            "city": catalog.get("city") or "",
            "ny6": True,
            "stadium_handle": pb.stadium_handle,
            "away_row": game.away_row,
            "home_row": game.home_row,
            "official": bool(game.official),
            "current_week": False,
        })

    slate = set(savesched.week_slate(payload))
    for slot in ordinary:
        slot["current_week"] = slot["record"] in slate
    return sorted(ordinary, key=lambda slot: (not slot["ny6"], slot["record"]))


def automatic_assignments(slots: list[dict[str, Any]],
                          teams: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Build a complete, deterministic schedule with no duplicate teams.

    Official games are fixed first. Unused NY6 games receive the strongest
    remaining bowl eligible teams. Ordinary bowls keep the game's pairing when
    both teams remain available, then every opening is filled by record and
    committee rank. All remaining FBS teams form a final completeness tier.
    """
    assignable = {int(team["row"]): team for team in teams if not team.get("playoff")}
    current_rows = {int(row) for slot in slots
                    for row in (slot.get("away_row"), slot.get("home_row"))
                    if isinstance(row, int) and row in assignable}

    def quality(row: int) -> tuple[Any, ...]:
        team = assignable[row]
        rank = int(team.get("rank") or 0)
        return (-int(team.get("wins") or 0), rank if rank > 0 else 999,
                int(team.get("losses") or 0), str(team.get("name") or ""))

    eligible = sorted((row for row, team in assignable.items()
                       if team.get("bowl_eligible") or row in current_rows), key=quality)
    fallback = sorted((row for row in assignable if row not in set(eligible)), key=quality)
    pool = eligible + fallback
    used: set[int] = set()
    out: dict[int, dict[str, int]] = {}

    # Completed games are immutable and own their teams before any new picks.
    for slot in slots:
        away, home = slot.get("away_row"), slot.get("home_row")
        if not slot.get("official"):
            continue
        if away not in assignable or home not in assignable or away == home:
            continue
        if away in used or home in used:
            continue
        out[int(slot["record"])] = {
            "record": int(slot["record"]), "away_row": int(away), "home_row": int(home)}
        used.update((int(away), int(home)))

    def take() -> int:
        row = next((candidate for candidate in pool if candidate not in used), None)
        if row is None:
            raise ValueError("not enough nonplayoff FBS teams to fill every bowl game")
        used.add(row)
        return row

    # NY6 gets first choice. A previously generated valid pairing stays put.
    for slot in [item for item in slots if item.get("ny6") and not item.get("official")]:
        away, home = slot.get("away_row"), slot.get("home_row")
        if away in assignable and home in assignable and away != home \
                and away not in used and home not in used:
            used.update((int(away), int(home)))
            pair = (int(away), int(home))
        else:
            pair = (take(), take())
        out[int(slot["record"])] = {
            "record": int(slot["record"]), "away_row": pair[0], "home_row": pair[1]}

    # Preserve ordinary game pairings wherever the NY6 promotions did not open
    # a hole. This retains the game's conference tie ins and regional flavor.
    open_slots: list[dict[str, Any]] = []
    for slot in [item for item in slots if not item.get("ny6") and not item.get("official")]:
        away, home = slot.get("away_row"), slot.get("home_row")
        if away in assignable and home in assignable and away != home \
                and away not in used and home not in used:
            used.update((int(away), int(home)))
            out[int(slot["record"])] = {
                "record": int(slot["record"]), "away_row": int(away), "home_row": int(home)}
        else:
            open_slots.append(slot)
    for slot in open_slots:
        out[int(slot["record"])] = {
            "record": int(slot["record"]), "away_row": take(), "home_row": take()}

    return [out[int(slot["record"])] for slot in slots]


def _fit_layout(slots: list[dict[str, Any]],
                teams: list[dict[str, Any]]) -> tuple[list[dict[str, Any]],
                                                       list[dict[str, Any]]]:
    """Limit real bowl games to the number of nonplayoff FBS teams available.

    A 96 or 128 team playoff cannot coexist with all 32 ordinary bowls without
    double-booking teams. Official valid games remain visible first, then every
    unused NY6 slot, then ordinary bowls in the game's authored order. Excess
    records are neutralized by the writer and intentionally stay off the tab.
    """
    allowed = {int(team["row"]) for team in teams if not team.get("playoff")}
    capacity = len(allowed) // 2
    if len(slots) <= capacity:
        return slots, []
    valid_official = [slot for slot in slots if slot.get("official")
                      and slot.get("away_row") in allowed
                      and slot.get("home_row") in allowed]
    priority = (valid_official
                + [slot for slot in slots if slot.get("ny6") and slot not in valid_official]
                + [slot for slot in slots if not slot.get("ny6") and slot not in valid_official])
    active = priority[:capacity]
    active_records = {int(slot["record"]) for slot in active}
    return active, [slot for slot in slots if int(slot["record"]) not in active_records]


def _normalize_assignments(raw: object) -> list[dict[str, int]]:
    if not isinstance(raw, list):
        raise ValueError("bowl assignments must be a list")
    out: list[dict[str, int]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each bowl assignment must be an object")
        try:
            out.append({"record": int(item["record"]),
                        "away_row": int(item["away_row"]),
                        "home_row": int(item["home_row"])})
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("each bowl needs a record, away team, and home team") from exc
    return out


def _validate(assignments: list[dict[str, int]], slots: list[dict[str, Any]],
              teams: list[dict[str, Any]]) -> None:
    by_record = {int(item["record"]): item for item in assignments}
    slot_records = {int(slot["record"]) for slot in slots}
    if set(by_record) != slot_records or len(assignments) != len(slot_records):
        raise ValueError("the bowl schedule must assign every visible bowl exactly once")
    allowed = {int(team["row"]) for team in teams if not team.get("playoff")}
    used: set[int] = set()
    for slot in slots:
        item = by_record[int(slot["record"])]
        away, home = item["away_row"], item["home_row"]
        if away not in allowed or home not in allowed:
            raise ValueError(f"{slot['name']} contains a playoff or unavailable team")
        if away == home:
            raise ValueError(f"{slot['name']} cannot assign the same team twice")
        for row in (away, home):
            if row in used:
                name = next((team["name"] for team in teams if team["row"] == row), str(row))
                raise ValueError(f"{name} is assigned to more than one postseason game")
            used.add(row)
        if slot.get("official") and (away, home) != \
                (slot.get("away_row"), slot.get("home_row")):
            raise ValueError(f"{slot['name']} is final and cannot be changed")


def _desired(slots: list[dict[str, Any]], teams: list[dict[str, Any]], year: int,
             requested: object = None, *, auto: bool = False) \
        -> tuple[list[dict[str, int]], str, bool]:
    generated = automatic_assignments(slots, teams)
    if requested is not None:
        desired = _normalize_assignments(requested)
        _validate(desired, slots, teams)
        return desired, "manual", False
    saved = None if auto else _load_plan(year)
    if saved is not None:
        try:
            desired = _normalize_assignments(saved.get("assignments"))
            _validate(desired, slots, teams)
            return desired, str(saved.get("mode") or "manual"), True
        except ValueError:
            pass
    _validate(generated, slots, teams)
    return generated, "auto", False


def _apply_payload(payload: bytearray, roster: list[saveteams.Team],
                   table: saveconfs.ConferenceTable | None,
                   state: dict[str, Any], *, requested: object = None,
                   auto: bool = False, report: list[str] | None = None) -> dict[str, Any]:
    bracket = state.get("bracket") or {}
    plan = state.get("plan") or {}
    year = int(state.get("year") or 0)
    all_slots = _slot_catalog(bytes(payload), bracket, plan)
    teams = _team_catalog(bytes(payload), roster, table, bracket)
    slots, inactive = _fit_layout(all_slots, teams)
    if not slots:
        raise ValueError("no editable nonplayoff bowl games were found in this save")
    desired, mode, from_saved = _desired(slots, teams, year, requested, auto=auto)
    by_record = {item["record"]: item for item in desired}
    store = savesched.parse(bytes(payload))
    slate = set(savesched.week_slate(bytes(payload)))
    log = report if report is not None else []
    changed = 0
    for slot in slots:
        item = by_record[int(slot["record"])]
        game = store.games[int(slot["record"])]
        pair = (item["away_row"], item["home_row"])
        if pair != (game.away_row, game.home_row):
            if game.official:
                raise ValueError(f"{slot['name']} is final and cannot be changed")
            if game.has_result or game.presimmed:
                log.extend(savesched.reset_locked_matchup_status(payload, game)
                           if game.index in slate
                           else savesched.clear_engine_state(payload, game))
            log.extend(savesched.set_matchup(
                payload, game, away_row=pair[0], home_row=pair[1]))
            log.append(f"{slot['name']}: bowl matchup assigned")
            changed += 1
        if slot.get("ny6") and game.venue_uid != slot.get("stadium_handle"):
            log.extend(savesched.set_venue(payload, game, slot.get("stadium_handle")))
            changed += 1
    # Records beyond this layout's real-team capacity cannot remain filled
    # with playoff teams. Keep them as harmless engine-valid placeholder bowls
    # using the same repeatable FCS rows the game's own schedule permits.
    fcs_rows = [row for row, team in enumerate(roster)
                if (team.name or "").upper().startswith("FCS ")]
    if len(fcs_rows) >= 2:
        fresh = savesched.parse(bytes(payload))
        for index, slot in enumerate(inactive):
            game = fresh.games[int(slot["record"])]
            if game.official:
                continue
            pair = (fcs_rows[(2 * index) % len(fcs_rows)],
                    fcs_rows[(2 * index + 1) % len(fcs_rows)])
            if pair == (game.away_row, game.home_row):
                continue
            if game.has_result or game.presimmed:
                log.extend(savesched.reset_locked_matchup_status(payload, game)
                           if game.index in slate
                           else savesched.clear_engine_state(payload, game))
            log.extend(savesched.set_matchup(
                payload, game, away_row=pair[0], home_row=pair[1]))
            log.append(f"{slot['name']}: inactive for this playoff field size")
            changed += 1
    # Parse the complete table after the patch before the caller can touch disk.
    savesched.parse(bytes(payload))
    return {"changed": changed, "assignments": desired, "mode": mode,
            "from_saved": from_saved, "slots": slots, "teams": teams,
            "inactive": inactive, "report": log}


def _state_payload(ctx: dict[str, Any], state: dict[str, Any],
                   requested: object = None, *, auto: bool = False) -> dict[str, Any]:
    payload = bytearray(ctx["payload"])
    result = _apply_payload(payload, ctx["roster"], ctx.get("table"), state,
                            requested=requested, auto=auto)
    assignments = result["assignments"]
    current = [{"record": int(slot["record"]),
                "away_row": int(slot["away_row"]) if slot.get("away_row") is not None else None,
                "home_row": int(slot["home_row"]) if slot.get("home_row") is not None else None}
               for slot in result["slots"]]
    by_row = {int(team["row"]): team for team in result["teams"]}
    by_assignment = {item["record"]: item for item in assignments}
    games = []
    for slot in result["slots"]:
        item = by_assignment[int(slot["record"])]
        games.append({**slot,
                      "away": by_row.get(item["away_row"]),
                      "home": by_row.get(item["home_row"])})
    auto_assign = automatic_assignments(result["slots"], result["teams"])
    applied = all(item.get("away_row") == desired.get("away_row")
                  and item.get("home_row") == desired.get("home_row")
                  for item, desired in zip(current, assignments)) and result["changed"] == 0
    return {
        "available": True,
        "year": int(state.get("year") or 0),
        "status": state.get("status"),
        "editable": state.get("status") in _EDITABLE_STATUSES,
        "mode": result["mode"],
        "applied": applied,
        "games": games,
        "assignments": assignments,
        "auto_assignments": auto_assign,
        "teams": [team for team in result["teams"] if not team.get("playoff")],
        "summary": {
            "bowls": len(games),
            "ny6": sum(1 for game in games if game.get("ny6")),
            "teams": len(games) * 2,
            "locked": sum(1 for game in games if game.get("official")),
            "inactive": len(result.get("inactive") or []),
        },
    }


def get_state(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state or state.get("status") not in _VISIBLE_STATUSES \
            or not state.get("bracket"):
        return {"available": False, "reason": "The postseason field is not set yet."}
    ctx = confsetup._read_table()
    if ctx is None:
        return {"available": False, "reason": "No readable dynasty save is selected."}
    try:
        return _state_payload(ctx, state)
    except ValueError as exc:
        return {"available": False, "reason": str(exc)}


def apply(assignments: object = None, *, auto: bool = False) -> dict[str, Any]:
    """Persist and write a complete bowl plan to the active dynasty save."""
    from . import playoff_live  # lazy, this module is also used by playoff_live
    with playoff_live._cross_process_lock():
        state = playoff_live._load_state()
        if state.get("status") not in _EDITABLE_STATUSES:
            raise ValueError("the postseason must be selected and unfinished before bowls can change")
        ctx = confsetup._read_table()
        if ctx is None:
            raise ValueError("no readable dynasty save is selected")
        payload = bytearray(ctx["payload"])
        result = _apply_payload(payload, ctx["roster"], ctx.get("table"), state,
                                requested=assignments, auto=auto)
        written = result["changed"] > 0
        if written:
            confsetup._backup_once(ctx["path"])
            encoded = container.encode(ctx["raw"], bytes(payload), saved_at=datetime.now())
            ctx["path"].write_bytes(encoded)
            confsetup._table_cache.clear()
        _save_plan(int(state["year"]), result["assignments"], result["mode"])
        fresh = confsetup._read_table()
        out = _state_payload(fresh or {**ctx, "payload": bytes(payload)}, state)
        out.update({"written": written, "changed": result["changed"],
                    "report": result["report"], "save": ctx["path"].name})
        return out


def apply_during_playoff(payload: bytearray, roster: list[saveteams.Team],
                         state: dict[str, Any], report: list[str], *,
                         table: saveconfs.ConferenceTable | None = None,
                         dry_run: bool = False) -> dict[str, Any]:
    """Reassert the frozen bowl plan inside a playoff save rewrite.

    The playoff runtime can rewind or replace a postseason base snapshot. This
    hook keeps manual bowl assignments and unused NY6 pairings attached to every
    rewritten world. The caller saves a newly generated plan only after the
    dynasty file itself was written successfully.
    """
    if state.get("status") not in _EDITABLE_STATUSES:
        return {"changed": 0, "assignments": None, "mode": "auto"}
    result = _apply_payload(payload, roster, table, state, report=report)
    if result["changed"] and not dry_run:
        # The caller still owns the game save write, so return the plan and let
        # it persist after that write succeeds.
        return result
    return result


def persist_generated(year: int, result: dict[str, Any]) -> None:
    if result.get("assignments"):
        _save_plan(year, result["assignments"], str(result.get("mode") or "auto"))
