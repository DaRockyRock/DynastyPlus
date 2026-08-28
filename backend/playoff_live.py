"""The custom playoff runtime: the live bracket over a REAL CFB 27 dynasty.

This module owns the season lifecycle of the user's custom playoff format
(backend/playoff.py) against the real save (backend/saveparse/schedule.py):

  projected    regular season / CCG week: the field the committee would pick
               today, from the save's own rankings, records, and rivalry
               results. Recomputed on every sync; nothing is written.
  selected     the conference championships are official: the field is frozen
               per the custom format, seeded, every playoff round is mapped
               onto the save's own postseason game records, and the first
               write pushes the matchups (and regenerated bowls) into the
               save so the GAME plays them.
  in_progress  rounds advance as their games go official in new autosaves;
               each week boundary re-writes the next round's matchups (the
               engine fills its own 12-team bracket at the boundary, so the
               companion always re-patches after an advance).
  complete     the championship is official: the champion and full bracket
               are appended to the dynasty's playoff history.

State lives at data/dynasties/<id>/playoff/live.json; finished seasons append
to playoff/history.json. All save writes go through the conference editor's
proven flow: backup-once, patch in place, verify by re-parse, re-encode.

Round -> save-record mapping: formats that fit the engine's stock postseason
slots (found through their BowlGame refs: first round rows 7-10, quarterfinals
12-15, semifinals 16-17, championship 11; the custom bracket's LAST round
takes the championship record, walking backwards) run in "stock" mode and ride
the game's own calendar. Bigger formats run in "cycle" mode: waves of matchups
are written onto the PRE-LOCK base-week snapshot (the arrival autosave taken
at selection) over the playoff week's slate (schedule.week_slate), the user
reloads and plays/sims the week, results are captured from autosaves, and the
world is rolled back to the base with the next wave until a champion is
crowned. See the round-cycling section below and
docs/custom-playoff-automation.md.
"""
from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from . import confsetup, dynasty_paths, pipeline, playoff
from .saveparse import bowls as savebowls
from .saveparse import container
from .saveparse import polls as savepolls
from .saveparse import schedule as savesched
from .saveparse import stadiums as savestadiums
from .saveparse import teams as saveteams

_lock = threading.Lock()

# stock slot capacity walking back from the title game: NCG, SF, QF, FR
_STOCK_ROUND_SLOTS = [1, 2, 4, 4]

# cycle-mode wave format: bumped when a written world's byte recipe changes
# in a way that requires rewriting an already-staged wave (2 = pre-lock base
# waves carry the SeasonGameRequest user-mark so the user's game is playable;
# 3 = the user's own engine-scheduled game is no longer blanked, which
# crashed the game on load; 4 = engine-native user games: the user's side is
# preserved on their engine record and the real ranking is restored;
# 5 = the bowl identity follows named bowl sites so those games no longer use
# a CFP-round identity away from its native venues; 6 = worlds written from a
# REBASED (post-lock) base
# carry detached, never-simmed CPU records and must be rewritten from the
# true pre-lock arrival base; 7 = a staged custom user game removes the user
# from every stale engine postseason record, so the original bowl/CFP game
# cannot override the custom request and leave the dynasty hub on a bye;
# 8 = a user whose engine-owned game is on a later bowl week is deferred and
# routed to that native game; 9 = every preliminary user game remains in the
# Bowl Week 1 cycle and ordinary-bowl users regain the native final-16 handoff;
# 10 = a custom-bye placeholder uses an unused FBS program, never an FCS team
# inside a native CFP record (the Penn State load-crash fix); 11 = the native
# handoff rebuilds ordinary bowls around only the active endgame field and
# never leaves a postseason request with one or both teams missing; 12 = a
# locked native-week rewrite uses the reference tool's HomeScheduled status,
# and a later round's real participants recover winners whose score fields an
# older write cleared; 13 = the first neutral-field repair; 14 = a playable
# ordinary-neutral user game keeps its selected stadium and keeps a native CFP
# bracket identity whose own venue is paired to that stadium, correcting format
# 13's accidental move to the home team's campus; 15 keeps that stadium and
# writes the home school's real field recipe into the stadium's dedicated
# field-only override; 16 = every native week pins the user's custom matchup
# to the SeasonGameRequest record Actions actually opens, even after a prior
# write moved the user's team to another quarterfinal record; 17 = a decided
# next round is staged before the prior week's advance; 18 = +52/+60 are
# treated as engine-issued AwayRequestId/HomeRequestId values, never copied
# between games, and an old half-issued week recovers through its prior
# boundary snapshot; 19 = a borrowed bowl candidate displaced by the user's
# pinned engine record is returned to ordinary-bowl regeneration, preventing
# a survivor from appearing twice in the handoff slate; 20 = every playable
# campus or plain-neutral cycle wave reserves one native CFP first-round
# identity on a sibling custom game, giving the user's organic record a safe
# swap partner instead of leaking its original bowl presentation; 21 replaces
# the ignored Stadium recipe string with CFB's native zero-venue plus temporary
# HomeTeam.Stadium relationship, and makes the better seed the neutral host;
# 22 freezes and reasserts the complete nonplayoff bowl schedule, including
# every NY6 venue the custom bracket leaves available)
_WAVE_FORMAT = 22

# the engine's own 12-team CFP first-round window by committee rank: ranks
# 5..12 play the first round, 1..4 get byes (verified against a real base)
_ENGINE_FIELD_RANKS = range(5, 13)


def _ccg_week(payload: bytes, store: savesched.GameStore) -> bool:
    """Whether the CURRENT week's slate holds the conference championships:
    the last pre-boundary week, i.e. the only window for the PREPARE write."""
    slate = savesched.week_slate(payload)
    if not slate:
        return False
    max_bowl = max((g.index for g in store.games if g.bowl_row is not None),
                   default=-1)
    return any(r > max_bowl and store.games[r].bowl_row is None for r in slate)


def _week_locked(payload: bytes, store: savesched.GameStore | None = None) -> bool:
    """Whether the engine has already LOCKED the current week in this world:
    any slate record pre-simmed, holding a result, or already official.

    Only a PRE-LOCK arrival world locks (and so pre-sims, or offers the user)
    its matchups on load; the engine never re-locks a week it already locked,
    so wave records cleared back to the scheduled-unplayed shape in a locked
    world come up DETACHED on load and are never simmed (the Notre Dame
    lesson, 2026-07-09). A locked world must therefore never become the
    cycle's base snapshot: waves written from it record nothing, forever."""
    if store is None:
        store = savesched.parse(payload)
    for r in savesched.week_slate(payload):
        if r < len(store.games):
            g = store.games[r]
            if g.presimmed or g.has_result or g.official:
                return True
    return False


def _apply_prepare(user_row: int, roster: list[saveteams.Team]) -> dict[str, Any]:
    """The championship-week PREPARE write for a user team the engine's
    postseason selection would snub: temporarily flip every regular-season
    loss so the boundary sees an undefeated team and puts it on CFB's own CFP
    path. An externally inserted user team can display and launch a native
    game while CFB silently discards its postgame result because the program's
    internal postseason cache was never built for that path. Only the engine's
    selection boundary creates the durable path without the reference tool's
    retire and rehire workaround.

    A planted committee rank is recomputed from results at the boundary, so
    the real scores are the only reliable lever. Every flipped score is saved
    in state and restored by the first playoff write. The distortion exists
    only long enough for CFB to select the user organically.
    """
    ctx = confsetup._read_table()
    if ctx is None:
        return {"written": False, "reason": "no readable save"}
    payload = bytearray(ctx["payload"])
    store = savesched.parse(bytes(payload))
    losses = [g for g in store.by_team(user_row)
              if g.loser_row == user_row and g.bowl_row is None]
    losses.sort(key=lambda g: g.result_slot or 0, reverse=True)  # latest first
    if not losses:
        return {"written": False, "reason": "record already undefeated"}
    flips, report = [], []
    for g in losses:
        flips.append({"game": g.index, "home": g.home_score, "away": g.away_score})
        report.extend(savesched.swap_result_scores(payload, g))
    if not flips:
        return {"written": False, "reason": "no flippable losses"}
    confsetup._backup_once(ctx["path"])
    out = container.encode(ctx["raw"], bytes(payload), saved_at=datetime.now())
    ctx["path"].write_bytes(out)
    confsetup._table_cache.clear()
    return {"written": True, "report": report, "flips": flips}


def _throwaway_row(roster: list[saveteams.Team], field_names: set[str],
                   *, used_rows: set[int] | None = None,
                   avoid_rows: set[int] | None = None) -> int | None:
    """An unused non-field opponent for a user-owned placeholder game.

    Prefer a real FBS program. CFB 27 accepts FCS teams in ordinary bowls, but
    placing one in a native CFP record crashed a fresh Penn State dynasty on
    load. The row must also be absent from every other postseason game in the
    written world so the placeholder cannot create a double booking. FCS is a
    last resort only when the save exposes no unused FBS row."""
    used = used_rows or set()
    avoid = avoid_rows or set()
    candidates = [
        (i, team) for i, team in enumerate(roster)
        if team.name not in field_names and i not in used and i not in avoid
    ]
    for i, team in candidates:
        if team.name and not team.name.upper().startswith("FCS "):
            return i
    for i, team in candidates:
        if team.name and team.name.upper().startswith("FCS "):
            return i
    return None


def _user_engine_target_week(payload: bytes, store: savesched.GameStore,
                             user_rows: set[int]) -> int | None:
    """The absolute BOWL WEEK number (1-4) the user's engine game lives in,
    for the 'advance to bowl week N' guidance. Derived from the stock CFP
    group its record belongs to: first round = week 1, quarterfinal = 2,
    semifinal = 3, championship = 4. None if the user's engine game is a bowl
    (bowls span weeks; no clean number)."""
    if not user_rows:
        return None
    slots = _postseason_slots(payload)
    week_of = {"first_round": 1, "quarterfinal": 2, "semifinal": 3, "championship": 4}
    for kind, week in week_of.items():
        for r in slots.get(kind) or []:
            g = store.games[r]
            if not g.official and (g.away_row in user_rows or g.home_row in user_rows):
                return week
    return None


def _user_engine_week(payload: bytes, store: savesched.GameStore,
                      user_rows: set[int]) -> str:
    """Where the user's engine-scheduled postseason game lives relative to
    the CURRENT week: "here" (in this week's slate: playable now), "later"
    (a future bowl week), or "none" (the engine gave them nothing). Format 9
    keeps this as diagnostic state only. Hybrid user games always stay in the
    Bowl Week 1 cycle and use the conditional in-game cache refresh when the
    dynasty hub does not immediately expose Play Game."""
    if not user_rows:
        return "none"
    pending = [g for g in store.games
               if g.bowl_row is not None and not g.official
               and (g.away_row in user_rows or g.home_row in user_rows)]
    if not pending:
        return "none"
    slate = set(savesched.week_slate(payload))
    return "here" if any(g.index in slate for g in pending) else "later"


def _user_has_native_cfp_path(payload: bytes, store: savesched.GameStore,
                              user_rows: set[int]) -> bool:
    """Whether CFB itself placed the user on one of its CFP records."""
    if not user_rows:
        return False
    stock = _postseason_slots(payload)
    records = {record for slots in stock.values() for record in slots}
    return any(
        record < len(store.games)
        and not store.games[record].official
        and ({store.games[record].away_row, store.games[record].home_row}
             & user_rows)
        for record in records
    )


def _unswap_dynasty_ranks(dynasty: dict[str, Any],
                          swap: dict[str, Any] | None) -> None:
    """Give the CUSTOM bracket the REAL ranking: while the save still carries
    the prepare swap, swap the two teams' rank values back inside the dynasty
    dict (once a wave write has restored the real ranks in the save, the dict
    is already honest and this is a no-op)."""
    if not swap:
        return
    rows = {swap.get("user"): None, swap.get("other"): None}
    for row in dynasty.get("all_teams") or []:
        if row.get("name") in rows:
            rows[row["name"]] = row
    a, b = rows.get(swap.get("user")), rows.get(swap.get("other"))
    if a is not None and b is not None \
            and a.get("rank") == swap.get("other_rank") \
            and b.get("rank") == swap.get("user_rank"):
        a["rank"], b["rank"] = b["rank"], a["rank"]


def _reseed_gate_games(bracket: dict[str, Any]) -> set[str]:
    """Reseed mode's wave priority: the user's next matchup re-pairs from ALL
    of the current round's survivors, so every unfinished game of the earliest
    unfinished round gates them (there is no fixed sibling subtree to walk)."""
    for rnd in bracket.get("rounds") or []:
        pending = {g["id"] for g in rnd["games"] if g.get("status") != "final"}
        if pending:
            return pending
    return set()


def _user_path_groups(bracket: dict[str, Any],
                      user_names: set[str]) -> tuple[set[str], set[str]]:
    """Split the user's unresolved path into immediate and later feeders.

    ``immediate`` is the unfinished subtree feeding an open winner slot in
    the user's CURRENT game. This is the important bye case: USC can already
    occupy R2G16 while its opponent still depends on R1G16. ``later`` holds
    sibling subtrees above that game on the route to the title.

    The distinction matters when a large first round exceeds the save's wave
    capacity. If every path game has one priority, an immediate feeder near
    the end of the round can lose all available records to distant branches,
    leaving the user on a phantom bye while the rest of the bracket advances.
    """
    feeds: dict[str, str] = {}
    games_by_id: dict[str, dict[str, Any]] = {}
    user_game = None
    for rnd in bracket.get("rounds") or []:
        for g in rnd["games"]:
            games_by_id[g["id"]] = g
            for s in g["slots"]:
                if s.get("game"):
                    feeds[s["game"]] = g["id"]
            if any(s.get("team") in user_names for s in g["slots"]):
                user_game = g  # the deepest round the user has reached
    if user_game is None:
        return set(), set()
    if user_game.get("winner") and user_game["winner"] not in user_names:
        return set(), set()  # eliminated: no path left to prioritize

    def subtree(gid: str, out: set[str]) -> None:
        g = games_by_id.get(gid)
        if g is None:
            return
        if g.get("status") != "final":
            out.add(gid)
        for s in g["slots"]:
            if s.get("game"):
                subtree(s["game"], out)

    immediate: set[str] = set()
    for slot in user_game["slots"]:
        if slot.get("game"):
            subtree(slot["game"], immediate)

    later: set[str] = set()
    cur = user_game["id"]
    while cur in feeds:
        nxt = feeds[cur]
        for s in games_by_id[nxt]["slots"]:
            if s.get("game") and s["game"] != cur:
                subtree(s["game"], later)
        cur = nxt
    return immediate, later


def _user_path_games(bracket: dict[str, Any], user_names: set[str]) -> set[str]:
    """All unfinished games whose results gate the user's route.

    Kept as the set-valued helper for diagnostics and callers that do not
    need ordering. The cycle assigner uses :func:`_user_path_groups` so the
    user's immediate opponent is always decided first.
    """
    immediate, later = _user_path_groups(bracket, user_names)
    return immediate | later


def _capture_user_result(state: dict[str, Any], store: savesched.GameStore,
                         payload: bytes, bracket: dict[str, Any],
                         plan: dict[str, list[int | None]],
                         user_names: set[str],
                         rows_by_name: dict[str, int]) -> None:
    """Snapshot the user's own played game the moment it is official in the
    save, so later rewinds can restore it verbatim (see schedule.write_record).
    Captures the user's DEEPEST final bracket game whenever the record that
    hosts it currently holds exactly that matchup with an official result. Runs
    every sync, so it tracks forward through the rounds and freezes on the game
    that ends the user's run."""
    user_rows = {rows_by_name[n] for n in user_names if n in rows_by_name}
    if not user_rows:
        return
    final_rec = None
    final_game = None
    for rnd in bracket.get("rounds") or []:
        recs = plan.get(str(rnd["round"])) or []
        for g, r in zip(rnd["games"], recs):
            if r is not None and g.get("status") == "final" \
                    and any(s.get("team") in user_names for s in g["slots"]):
                final_rec, final_game = r, g
    if final_rec is None or final_rec >= len(store.games):
        return
    g = store.games[final_rec]
    if not (g.official and g.has_result
            and (g.away_row in user_rows or g.home_row in user_rows)):
        return
    want = {rows_by_name.get(s.get("team"))
            for s in final_game["slots"] if s.get("team")}
    if {g.away_row, g.home_row} != want:
        return  # record no longer holds the user's actual matchup
    # The user's game reuses ONE reserved record across every cycled round, so
    # the idempotency guard must compare CONTENT, not the record index: a
    # record-index guard froze the FIRST final game forever and the pin then
    # restored round 1 over the game that actually ended the run.
    frozen = state.get("user_frozen") or {}
    cur_hex = savesched.read_record(payload, store, final_rec).hex()
    if frozen.get("record") == final_rec and frozen.get("hex") == cur_hex:
        return  # already captured this game
    state["user_frozen"] = {
        "record": final_rec,
        "hex": cur_hex,
    }


def _state_path() -> Path:
    return dynasty_paths.sub("playoff") / "live.json"


def _history_path() -> Path:
    return dynasty_paths.sub("playoff") / "history.json"


def _snapshot_path() -> Path:
    """The cycle BASE WEEK snapshot: a byte-exact copy of the save file taken
    when the custom playoff enters cycling. 'Rewinding' the dynasty = writing
    this snapshot back (with the next wave of matchups patched in), which
    rolls the entire world (week counter, scheduler, stats) back consistently
    without needing to know where the engine keeps its week state."""
    return dynasty_paths.sub("playoff") / "cycle_base.sav"


def _restore_snapshot_path() -> Path:
    """A safety copy of the ORIGINAL pre-lock arrival snapshot. The retired
    base rebase (2026-07-09, removed the same day: a post-lock base detaches
    CPU wave games) created these; the completion restore and recovery flows
    PREFER this file when present, since it is guaranteed to be the engine's
    own untouched arrival world. Nothing creates it anymore."""
    return dynasty_paths.sub("playoff") / "restore_base.sav"


def _native_boundary_snapshot_path() -> Path:
    """The last save staged immediately before a native week boundary.

    CFB owns the participant requests for a playable game. Keeping this exact
    pre-advance world lets recovery cross the boundary again if a game patch
    or an older Dynasty+ write left only one participant request allocated.
    """
    return dynasty_paths.sub("playoff") / "native_boundary_base.sav"


def _failed_boundary_snapshot_path() -> Path:
    """Safety copy of the malformed forward world before a rollback."""
    return dynasty_paths.sub("playoff") / "native_boundary_failed.sav"


def _load_state() -> dict[str, Any]:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(state: dict[str, Any]) -> None:
    _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def history() -> list[dict[str, Any]]:
    try:
        rows = json.loads(_history_path().read_text(encoding="utf-8"))
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


def _append_history(entry: dict[str, Any]) -> None:
    rows = history()
    rows = [r for r in rows if r.get("year") != entry.get("year")]
    rows.append(entry)
    rows.sort(key=lambda r: r.get("year") or 0, reverse=True)
    _history_path().write_text(json.dumps(rows, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# per-dynasty on/off switch (the custom playoff automation, opt-in)
#
# OFF is the default: CFB 27 runs its own native 12-team playoff and Dynasty+
# writes NOTHING to the bracket (no matchups, no rewinds, no "update dynasty
# file" prompt). Custom conference alignment and custom poll rankings still
# reach the save through their own write paths, so they seed the game's native
# bracket. Turning this ON hands the postseason to the format the user built
# (any field size), written into the save round by round. Same opt-in shape as
# the recruiting tool (backend/recruiting_fix.py): a patched save must be
# reloaded in CFB 27, so the user activates it deliberately.
# ---------------------------------------------------------------------------
_config_lock = threading.Lock()


def _config_path() -> Path:
    return dynasty_paths.sub("playoff") / "settings.json"


def _active_run_default() -> bool:
    """Before the user makes an explicit choice, keep an ALREADY-running custom
    bracket going (so shipping the opt-in default never strands a playoff that
    is mid-flight) while a fresh or idle dynasty defaults to OFF."""
    return _load_state().get("status") in ("selected", "in_progress")


def get_config() -> dict[str, Any]:
    """The per-dynasty custom-playoff automation config. `enabled` defaults to
    False (opt-in) unless the dynasty already has a custom bracket under way."""
    enabled = _active_run_default()
    try:
        raw = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = None
    if isinstance(raw, dict) and "enabled" in raw:
        enabled = bool(raw["enabled"])
    return {"enabled": enabled}


def is_enabled() -> bool:
    """Whether this dynasty drives its postseason through the custom bracket."""
    return bool(get_config().get("enabled"))


def set_config(body: dict[str, Any]) -> dict[str, Any]:
    with _config_lock:
        cfg = get_config()
        if "enabled" in body:
            cfg["enabled"] = bool(body["enabled"])
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


# ---------------------------------------------------------------------------
# save-side structure
# ---------------------------------------------------------------------------

def _postseason_slots(payload: bytes) -> dict[str, list[int]]:
    """The stock playoff game-record indices by round kind, via BowlGame refs.

    Returns {"first_round": [...], "quarterfinal": [...], "semifinal": [...],
    "championship": [...]} in record order.

    Classification is _cfp_round_rows (internal-name keyed): matching the
    display name of a NAMED bowl let a leftover wave relabel poison the slot
    map (observed: the Cure Bowl, relabeled 'National Championship' by an
    earlier build, classified as a stock championship record, so the custom
    title game was written onto a regular bowl and double-booked its teams)."""
    table = savebowls.parse(payload)
    kinds = {"first_round": [], "quarterfinal": [], "semifinal": [], "championship": []}
    kind_by_row = _cfp_round_rows(table)
    store = savesched.parse(payload)
    for g in store.games:
        kind = kind_by_row.get(g.bowl_row) if g.bowl_row is not None else None
        if kind:
            kinds[kind].append(g.index)
    return kinds


_ROUND_KINDS = ["championship", "semifinal", "quarterfinal", "first_round"]


def _round_kind_map(bracket: dict[str, Any]) -> dict[str, str]:
    """bracket round number -> stock slot kind, walking back from the title
    game (the LAST round takes the championship record, and so on). Rounds
    deeper than the stock postseason get no kind (they cycle in the anchor
    week instead)."""
    rounds = bracket.get("rounds") or []
    return {str(rnd["round"]): _ROUND_KINDS[i]
            for i, rnd in enumerate(reversed(rounds)) if i < len(_ROUND_KINDS)}


def shape_fits(bracket: dict[str, Any], slots: dict[str, list[int]]) -> bool:
    """Whether every round's game count fits its week's stock records."""
    rounds = bracket.get("rounds") or []
    if len(rounds) > len(_ROUND_KINDS):
        return False
    kinds = _round_kind_map(bracket)
    for rnd in rounds:
        if len(rnd["games"]) > len(slots.get(kinds[str(rnd["round"])]) or []):
            return False
    return True


def stock_mode_fits(bracket: dict[str, Any], slots: dict[str, list[int]]) -> bool:
    """Whether the bracket can ride the game's own postseason calendar.

    Stock mode maps rounds onto the engine's CFP records walking back from
    the title game, but the engine OWNS its bracket week to week: it fills
    each round's records from ITS OWN prior-round winners at every boundary
    and plays its own games in every week the custom format skips. That only
    lines up when the custom bracket has a round for EVERY stock week,
    starting at the first-round slate the selection arrives on. A shorter
    format (a 4- or 8-team bracket) merely fit the trailing slots: the user
    then played the engine's own 12-team CFP for the skipped weeks while the
    app's semifinal writes were rebuilt over at each boundary (reported:
    4-team run, the user's team never got its matchup and the bracket never
    advanced). Those formats run NATIVE instead (below), writing each round
    at its own week's pre-lock arrival.

    Every round must also FILL its stock week exactly. An underfilled round
    (a 10-team field with 6 byes has a 2-game first round against the
    engine's 4 first-round records) leaves the leftover records carrying the
    engine's OWN pairings, whose teams can double-book against the custom
    matchups in the same week (the freeze-on-advance condition). Native mode
    neutralizes unclaimed records with FCS filler at each week's arrival;
    stock mode has no such hygiene because the true 12-team shape claims
    every record. So stock is EXACTLY the game's own shape (4+4+2+1 games,
    reported 2026-07-15: a 10-team bracket mislabeled as the game's own
    12-team playoff); everything else of 16 or fewer runs native."""
    rounds = bracket.get("rounds") or []
    if len(rounds) != len(_ROUND_KINDS):
        return False
    kinds = _round_kind_map(bracket)
    return all(
        len(rnd["games"]) == len(slots.get(kinds[str(rnd["round"])]) or [])
        for rnd in rounds)


# extra first-round hosts for NATIVE mode: up to this many regular bowl
# records in bowl week 1's slate are borrowed as first-round games (the
# balla14 mechanism, 2026-07-13), so a 16-team bracket's 8-game opening
# round fits the calendar (4 stock first-round records + 4 borrowed bowls)
_NATIVE_FR_BORROW = 4


def native_mode_fits(bracket: dict[str, Any], slots: dict[str, list[int]]) -> bool:
    """Whether the bracket can ride the calendar FORWARD in native mode.

    Native mode (2026-07-13, the requested balla14-style flow) generalizes
    stock mode to every bracket of 16 or fewer teams: rounds map onto the
    stock postseason records walking back from the title game, and each
    round is written onto its OWN bowl week's pre-lock arrival autosave (the
    same write shape as a cycle wave, but moving forward with the calendar,
    never rewinding). Two extensions over stock:

      * a bracket SHORTER than the stock ladder (2/4/8 teams) starts on a
        later bowl week; the weeks before it are dead weeks the user simply
        advances through (the engine plays its own CFP games there, which
        do not count toward the custom bracket);
      * a first round of up to 8 games fits by BORROWING regular bowl
        records from bowl week 1's slate (_NATIVE_FR_BORROW), which the
        16-team shape needs.

    Because every round is written at its own week's arrival (after the
    engine's boundary has built that week) and picked up by a reload, the
    engine's own bracket rebuild never clobbers a live write, which is what
    sank the earlier calendar-tail design."""
    rounds = bracket.get("rounds") or []
    if not rounds:
        # The editor permits a one-team format. It is already complete when
        # selected and needs no save slots, but classifying it as cycle would
        # unnecessarily wait for an anchor and snapshot.
        return bool(bracket.get("champion")) and bracket.get("field_size") == 1
    if len(rounds) > len(_ROUND_KINDS):
        return False
    kinds = _round_kind_map(bracket)
    for rnd in rounds:
        kind = kinds[str(rnd["round"])]
        cap = len(slots.get(kind) or [])
        if kind == "first_round":
            cap += _NATIVE_FR_BORROW
        if len(rnd["games"]) > cap:
            return False
    return True


# the game's postseason record counts, constant across CFB27 saves (balla14
# 2026-07-13, confirmed here: 4 first-round + 4 quarterfinal + 2 semifinal +
# 1 championship). Used to classify a DRAFT format's in-game mode before a
# real save is loaded (the format editor's preview).
_DEFAULT_SLOT_COUNTS = {"first_round": 4, "quarterfinal": 4,
                        "semifinal": 2, "championship": 1}


def classify_mode(bracket: dict[str, Any],
                  slots: dict[str, list[int]] | None = None) -> str:
    """The in-game mode a bracket runs in: "stock" (the native 12-team shape,
    every round on the game's own CFP calendar), "native" (16 or fewer teams,
    the balla14-style forward calendar with borrowed first-round bowls, every
    game recorded in-game), or "hybrid" (more than 16 teams: the early rounds
    cycle at the anchor week, then the final <=16-team endgame hands off to
    native so its last four rounds play out on the real calendar, recorded
    in-game). `slots` defaults to the game's standard postseason record counts
    when no real save is loaded."""
    if slots is None:
        slots = {k: list(range(n)) for k, n in _DEFAULT_SLOT_COUNTS.items()}
    if stock_mode_fits(bracket, slots):
        return "stock"
    if native_mode_fits(bracket, slots):
        return "native"
    return "hybrid"


# per-round game-count caps for the native endgame, walking BACK from the
# title game: championship 1, semifinal 2, quarterfinal 4, first round
# 4 stock + up to _NATIVE_FR_BORROW borrowed bowls. A bracket's trailing
# rounds are always ...8, 4, 2, 1, so the native-fitting suffix is at most
# the last four rounds.
_NATIVE_TAIL_CAPS = [1, 2, 4, 4 + _NATIVE_FR_BORROW]


def native_tail_rounds(bracket: dict[str, Any]) -> set[str]:
    """The round keys of a bracket's native ENDGAME: the maximal trailing
    suffix of rounds whose game counts fit the game's own postseason (walking
    back from the title game against _NATIVE_TAIL_CAPS). For a bracket of 16
    or fewer teams this is every round; for a bigger one it is the final
    <=4 rounds (round of 16 through the championship), the part that hands off
    from the cycle to the game's real playoff. Always includes at least the
    championship."""
    rounds = bracket.get("rounds") or []
    tail: set[str] = set()
    for i, rnd in enumerate(reversed(rounds)):
        if i >= len(_NATIVE_TAIL_CAPS) or len(rnd["games"]) > _NATIVE_TAIL_CAPS[i]:
            break
        tail.add(str(rnd["round"]))
    return tail


def _native_ready_rounds(bracket: dict[str, Any], slots: dict[str, list[int]],
                         slate_now: set[int]) -> set[str]:
    """The unfinished bracket rounds whose save records are part of the
    CURRENT week's slate: the only rounds a native-mode write may touch. A
    future round is written only after the user advances to its week, so
    the engine's own boundary rebuild can never land on top of a live
    write (the failure that sank the earlier calendar-tail design)."""
    kind_of = _round_kind_map(bracket)
    out: set[str] = set()
    for rnd in bracket.get("rounds") or []:
        if all(g.get("status") == "final" for g in rnd["games"]):
            continue
        recs = slots.get(kind_of.get(str(rnd["round"]))) or []
        if any(r in slate_now for r in recs):
            out.add(str(rnd["round"]))
    return out


_NATIVE_KIND_ORDER = [
    "first_round", "quarterfinal", "semifinal", "championship"]


def _native_prestage_rounds(bracket: dict[str, Any],
                            slots: dict[str, list[int]],
                            slate_now: set[int]) -> set[str]:
    """Fully decided custom round that CFB will make current NEXT week.

    Participant requests are allocated at the week boundary, one per team.
    Therefore both teams must already be in every next-week record before the
    user advances. Writing the matchup after arrival is too late: a native bye
    record then owns only one participant request, so its game can launch but CFB
    discards the completed result. This mirrors the working 16-team reference
    tool, which writes its quarterfinals while Bowl Week 1 is still current.
    """
    current = next(
        (index for index, kind in enumerate(_NATIVE_KIND_ORDER)
         if any(record in slate_now for record in (slots.get(kind) or []))),
        None)
    if current is None or current + 1 >= len(_NATIVE_KIND_ORDER):
        return set()
    next_kind = _NATIVE_KIND_ORDER[current + 1]
    kinds = _round_kind_map(bracket)
    out: set[str] = set()
    for rnd in bracket.get("rounds") or []:
        key = str(rnd["round"])
        if kinds.get(key) != next_kind:
            continue
        unfinished = [game for game in rnd["games"]
                      if game.get("status") != "final"]
        if unfinished and all(
                all(slot.get("type") == "team"
                    for slot in game.get("slots") or [])
                for game in unfinished):
            out.add(key)
    return out


def _native_borrow(state: dict[str, Any], bracket: dict[str, Any],
                   slots: dict[str, list[int]], store: savesched.GameStore,
                   payload: bytes, user_rows: set[int], user_in_field: bool,
                   notes: list[str]) -> None:
    """Native mode's host-pool preparation, run every sync. Mutates `slots`
    (the sync-local copy) and persists borrow choices in state["borrowed"].

    1. Re-applies previously borrowed records (kind -> record list) so every
       sync, write, and bowl-regeneration pass agrees on them.
    2. The record holding the USER's own engine game this week is pulled
       from every host list: it hosts only the user's OWN custom game
       (pinned by _native_pin_user), never a CPU pairing, and when the user
       is outside the custom field it keeps their real engine game.
    3. At a week's PRE-LOCK arrival, a ready round short of hosts BORROWS
       bowl records from the week's own slate (a 16-team first round needs
       four: the balla14 mechanism; a round can also come up one short when
       the user's engine game occupies one of its stock records)."""
    kind_of = _round_kind_map(bracket)
    borrowed: dict[str, list[int]] = {k: list(v) for k, v in
                                      (state.get("borrowed") or {}).items()}
    for kind, recs in borrowed.items():
        if recs:
            slots[kind] = list(slots.get(kind) or []) + [
                r for r in recs if r not in (slots.get(kind) or [])]
    slate_now = set(savesched.week_slate(payload))
    user_recs = {g.index for g in store.games
                 if g.index in slate_now and not g.official
                 and ({g.away_row, g.home_row} & user_rows)}
    frozen_user_rec = (state.get("user_frozen") or {}).get("record")
    if isinstance(frozen_user_rec, int) and frozen_user_rec in slate_now:
        # A hybrid bridge reasons from the clean pre-lock BASE. If the user's
        # final cycle game used a dynamically borrowed record, that base still
        # shows its original CPU teams, so the team-row test above cannot see
        # that user_frozen will graft the real result back onto it. Reserve the
        # record by identity or a native CPU game is mapped there and then
        # overwritten by the freeze (96-team repro: one missing round-of-16
        # game cascaded into an empty-slate reset).
        user_recs.add(frozen_user_rec)
    # Work out which round owns this week's stock records BEFORE filtering
    # the user's engine record out of the generic host pools.  When the user
    # is still in the custom field, that record is exactly the one
    # _native_pin_user must reuse for their custom matchup.  Removing it here
    # first made the final round disappear from _native_ready_rounds, so the
    # pin could never put it back (observed at the hybrid championship
    # handoff: both finalists were decided, but plan[final] stayed None).
    ready_before_filter = _native_ready_rounds(bracket, slots, slate_now)
    user_host_kinds = {
        kind_of[key] for key in ready_before_filter if kind_of.get(key)
    } if user_in_field else set()
    plan = state.get("plan") or {}
    # Only unfinished native games reserve records in the reference world.
    # At a hybrid bridge the early cycle rounds are already final and the
    # write intentionally goes back to the clean arrival snapshot, where
    # their old record assignments are free bowl hosts again. Counting every
    # historical plan entry exhausted the 28-record slate for 64+ team
    # brackets, so only five of eight round-of-16 games were staged before
    # the calendar advanced.
    pinned = {
        rec
        for rnd in bracket.get("rounds") or []
        for game, rec in zip(rnd["games"], plan.get(str(rnd["round"])) or [])
        if rec is not None and game.get("status") != "final"
    }
    for kind in list(slots):
        slots[kind] = [r for r in slots[kind]
                       if r not in user_recs or r in pinned
                       or kind in user_host_kinds]
    if not slate_now or _week_locked(payload, store):
        return  # borrowing happens only at a week's pre-lock arrival
    ready = _native_ready_rounds(bracket, slots, slate_now)
    taken = {r for v in slots.values() for r in v} | pinned
    changed = False
    for rnd in bracket.get("rounds") or []:
        key = str(rnd["round"])
        if key not in ready:
            continue
        kind = kind_of.get(key)
        usable = [r for r in (slots.get(kind) or [])
                  if r in slate_now and r < len(store.games)
                  and not store.games[r].official]
        unfinished = sum(1 for g in rnd["games"] if g.get("status") != "final")
        # The user's own engine record is claimed by _native_pin_user before
        # positional assignment.  It may already be one of the stock hosts
        # (the final-round case fixed above), or it may be a separate bowl
        # record that the pin adds to this kind (the opening-round case).  In
        # the latter case reserve its capacity now so we do not borrow one
        # extra bowl and leave an unused, double-booked matchup behind.
        user_host_is_extra = (user_in_field and bool(user_recs)
                              and not any(r in usable for r in user_recs))
        need = unfinished - len(usable) - (1 if user_host_is_extra else 0)
        if need <= 0:
            continue
        cands = [g.index for g in store.games
                 if g.index in slate_now and g.index not in taken
                 and g.index not in user_recs
                 and g.bowl_row is not None and not g.official
                 and not g.has_result and not g.presimmed]
        # dead_records describes failures in the REWOUND cycle world. A hybrid
        # bridge starts from the clean pre-lock base and moves forward through
        # the native calendar, where those records are healthy again (the same
        # repro marked all four stock CFP records dead, then they simulated
        # normally in native mode). Carrying that quarantine across worlds
        # starves the eight-game opening round of borrowed bowl hosts.
        take = cands[:need]
        if take:
            borrowed.setdefault(kind, []).extend(take)
            slots[kind] = list(slots.get(kind) or []) + take
            taken |= set(take)
            changed = True
            try:
                btable = savebowls.parse(payload)
                names = []
                for r in take:
                    b = btable.by_row(store.games[r].bowl_row)
                    names.append(b.name if b else f"game {r}")
                notes.append(
                    f"{len(take)} extra {rnd['name']} game(s) are hosted by "
                    "these bowl slots this week: " + ", ".join(names)
                    + ". They are relabeled as playoff games in the schedule.")
            except Exception:  # noqa: BLE001 - naming is cosmetic
                pass
        if need > len(take):
            notes.append(
                f"Not enough open games this week to host every {rnd['name']} "
                "matchup; some games cannot be scheduled this round.")
    if changed:
        state["borrowed"] = borrowed


def _native_pin_user(bracket: dict[str, Any], plan: dict[str, list[int | None]],
                     slots: dict[str, list[int]], store: savesched.GameStore,
                     payload: bytes, user_names: set[str],
                     user_rows: set[int]) -> bool:
    """Native mode: the user's unfinished custom game is hosted on the slate
    record the engine's user-typed SeasonGameRequest actually opens. That row
    is more authoritative than the SeasonGame teams after a prior write: the
    SMU quarterfinal save contained SMU versus Michigan in record 928, but its
    locked Actions row still opened record 931 and therefore offered Texas
    Tech. Reusing the request record preserves the engine's organic play-game
    wiring. If a sibling already owns it, the two assignments swap so every
    game keeps a unique record. Returns whether the plan changed."""
    if not user_rows:
        return False
    slate_now = set(savesched.week_slate(payload))
    request_live = savesched.user_pending_game(payload)
    live = (request_live if request_live in slate_now
            and request_live is not None
            and request_live < len(store.games)
            and not store.games[request_live].official else None)
    if live is None:
        live = next((g.index for g in store.games
                     if g.index in slate_now and not g.official
                     and ({g.away_row, g.home_row} & user_rows)), None)
    if live is None:
        return False
    kinds = _round_kind_map(bracket)
    ready = _native_ready_rounds(bracket, slots, slate_now)
    for rnd in bracket.get("rounds") or []:
        key = str(rnd["round"])
        if key not in ready:
            continue
        recs = plan.setdefault(key, [None] * len(rnd["games"]))
        for gi, g in enumerate(rnd["games"]):
            if g.get("status") == "final" \
                    or not any(s.get("team") in user_names for s in g["slots"]) \
                    or not all(s.get("type") == "team" for s in g["slots"]):
                continue
            current = recs[gi]
            if current == live:
                return False
            owner = next((i for i, rec in enumerate(recs)
                          if rec == live and i != gi), None)
            if owner is not None:
                recs[owner] = current
            recs[gi] = live
            kind = kinds.get(key)
            if live not in (slots.get(kind) or []):
                slots[kind] = list(slots.get(kind) or []) + [live]
            return True
    return False


def _calendar_rounds(bracket: dict[str, Any],
                     caps: list[int] | None = None) -> set[str]:
    """The trailing bracket rounds that ride the game's own postseason
    calendar instead of the anchor-week waves: walking back from the title
    game, the championship (1 stock record, championship week), the
    semifinals (2, week 3), and the quarterfinals (4, week 2), as far as
    the round sizes fit. `caps` trims the ladder to the stock rounds that
    lie AFTER the anchor week (a cycle anchored at bowl week 2 can only
    hand off the semifinals and the championship). Everything bigger cycles
    in the anchor week; once those rounds finish, the user simply advances
    through the real bowl weeks and the title game lands on championship
    week with its own presentation."""
    rounds = bracket.get("rounds") or []
    if caps is None:
        caps = [1, 2, 4]
    out: set[str] = set()
    for i, rnd in enumerate(reversed(rounds)):
        if i < len(caps) and len(rnd["games"]) <= caps[i]:
            out.add(str(rnd["round"]))
        else:
            break
    return out


def _pin_user_tail(sub: dict[str, Any], plan: dict[str, list[int | None]],
                   slots: dict[str, list[int]], store: savesched.GameStore,
                   rows_by_name: dict[str, int], user_names: set[str],
                   bracket: dict[str, Any]) -> None:
    """Reactive record pin for the calendar tail.

    The engine advances a CFP-path user through ITS bracket week by week; each
    tail week the user's team sits in a specific stock CFP record (which the
    engine chose, and pre-simmed). For the round the user is CURRENTLY in, pin
    their bracket game onto THAT record - read live from the save, matched to
    the round's stock kind - instead of a positional slot. `_assign_records`
    then leaves that entry alone and, because the record is now in the round's
    `assigned` set, gives every sibling game a DIFFERENT record: the user's
    live game is reserved, so no CPU pairing can overwrite it (the bug that
    turned Indiana's quarterfinal into BYU vs Oklahoma), and the opponent
    rewrite lands on the game the user actually plays."""
    user_rows = {rows_by_name[n] for n in user_names if n in rows_by_name}
    if not user_rows:
        return
    kinds = _round_kind_map(bracket)
    for rnd in sub["rounds"]:
        key = str(rnd["round"])
        kind_recs = set(slots.get(kinds.get(key)) or [])
        # the CFP record of THIS round's kind that currently holds the user and
        # is not yet official (the engine's live placement for the user)
        live = next((g.index for g in store.games
                     if g.index in kind_recs and not g.official
                     and (g.away_row in user_rows or g.home_row in user_rows)), None)
        if live is None:
            continue
        recs = plan.setdefault(key, [None] * len(rnd["games"]))
        # do not double-book: if the user's live record is already used by
        # another (already-mapped) game this round, leave assignment to the
        # normal pass
        if live in recs:
            continue
        for gi, g in enumerate(rnd["games"]):
            if recs[gi] is None and g.get("status") != "final" \
                    and any(s.get("team") in user_names for s in g["slots"]) \
                    and all(s.get("type") == "team" for s in g["slots"]):
                recs[gi] = live
                break


def _assign_records(bracket: dict[str, Any], plan: dict[str, list[int | None]],
                    slots: dict[str, list[int]], store: savesched.GameStore,
                    rows_by_name: dict[str, int]) -> bool:
    """Progressively map bracket games onto save records.

    A game gets a record only once BOTH its teams are decided, preferring the
    record where the engine already scheduled that exact pair (either
    orientation) so bowl branding and pre-sims stay put; games the engine has
    not scheduled take the round's leftover records in order. Returns True
    when anything new was assigned. Order-blind matching matters: the engine
    lays out its own bracket in a different record order, and assigning by
    position would rewrite two records into the same matchup. Rounds deeper
    than the stock postseason carry no kind and are skipped (the cycle's
    anchor-week waves own them)."""
    kinds = _round_kind_map(bracket)
    changed = False
    for rnd in bracket.get("rounds") or []:
        key = str(rnd["round"])
        if key not in kinds:
            continue
        games = rnd["games"]
        assigned = plan.setdefault(key, [None] * len(games))
        available = [r for r in (slots.get(kinds[key]) or [])
                     if r not in assigned and not store.games[r].official]
        pair_of = {}
        for rec_idx in available:
            g = store.games[rec_idx]
            if g.away_row is not None and g.home_row is not None:
                pair_of.setdefault(frozenset((g.away_row, g.home_row)), rec_idx)
        # first pass: content matches
        for gi, game in enumerate(games):
            if assigned[gi] is not None:
                continue
            rows = frozenset(rows_by_name[s["team"]] for s in game["slots"]
                             if s.get("type") == "team" and s.get("team") in rows_by_name)
            if len(rows) == 2 and rows in pair_of:
                rec = pair_of.pop(rows)
                assigned[gi] = rec
                available.remove(rec)
                changed = True
        # second pass: decided games the engine has not scheduled
        for gi, game in enumerate(games):
            if assigned[gi] is not None or not available:
                continue
            if all(s.get("type") == "team" for s in game["slots"]):
                rec = available.pop(0)
                pair_of = {k: v for k, v in pair_of.items() if v != rec}
                assigned[gi] = rec
                changed = True
    return changed


# ---------------------------------------------------------------------------
# round cycling (formats bigger than the stock postseason)
# ---------------------------------------------------------------------------
# NCAA-14-mod style: when a format needs more games or rounds than the game's
# postseason calendar holds, the playoff week's game records are REUSED. Every
# wave is written onto the PRE-LOCK base snapshot (the arrival autosave taken
# at selection) and the result replaces the save file: the engine, loading a
# week it has not locked yet, locks the wave's matchups exactly as if it had
# scheduled them itself, allocating its own pending machinery, pre-simming the
# CPU games, and putting the USER's game on the dynasty home screen to play.
# (Patching a POST-lock save can only change what the schedule screens show:
# the lock's participation objects are frozen, so the engine still plays the
# OLD slate, and a user matchup added after the lock reads as a bye week,
# observed in-game 2026-07-08.) The app captures results from autosaves
# (pre-sims included, they are the only result a CPU wave game will ever
# have), then writes the next wave onto the base again; the user reloads the
# dynasty between waves. The save's own season record-keeping is knowingly
# sacrificed for cycled games; the app's bracket state and playoff history
# are the source of truth (see docs/custom-playoff-automation.md).

def _slate_pool(state: dict[str, Any], base_store: savesched.GameStore) -> list[int]:
    """Records that can host wave games: the base week's slate (the engine's
    own SeasonGameRequest queue, captured in the pre-lock snapshot). Because
    every wave rebuilds the world from the base, a record spent in the
    CURRENT save is reusable as soon as the game it hosted is finished; only
    records of unfinished mapped games are held (the assigner's in-use set).

    DEAD RECORDS are excluded: slate records the running game consistently
    declines to sim (aged to official-with-no-result on an advance, or its
    game re-created over the app's write). Without the quarantine they are a
    tar pit: the unmapped game is rescheduled onto the first free record,
    which is the same dead one, and because the user's opponent-path games
    are assigned first, the user's own chain is the part of the bracket that
    never finishes (observed 2026-07-10, 128-team run, records 369/385). If
    quarantine would empty the pool entirely (e.g. a post-lock base where
    NOTHING sims), it is ignored: the old spin is better than a deadlock."""
    dead = set(state.get("dead_records") or [])
    pool = []
    for r in state.get("slate_records") or []:
        if r < len(base_store.games):
            g = base_store.games[r]
            if g.bowl_row is not None and not g.official:
                pool.append(r)
    live = [r for r in pool if r not in dead]
    return live if live else pool


def _quarantine_dead_records(state: dict[str, Any], bracket: dict[str, Any],
                             plan: dict[str, list[int | None]],
                             store: savesched.GameStore,
                             roster: list[saveteams.Team],
                             misfires: dict[str, set[int]],
                             user_base_recs: set[int],
                             user_names: set[str],
                             pre_final: set[str],
                             notes: list[str]) -> None:
    """Retire slate records the running game will not play, so their games
    are rescheduled onto records that work (the dead-record tar pit,
    2026-07-10: the engine declined two slate records every load; the app
    kept remapping the user's path-priority games onto exactly those records
    and their subtree never finished). Three signals, weakest evidence gets
    the most strikes:

      * skipped: aged to official-with-no-result holding our matchup - the
        engine declined it outright. Quarantined as it is unmapped (in the
        fill loop, so the same sync's reassignment avoids it already).
      * clobbered: went official holding a matchup that is none of ours -
        the engine ran its own game there. Two strikes (one per sync).
      * silent: our written matchup still sits result-less on a sync where
        OTHER games demonstrably finished (fresh finals this pass = the
        engine ran this world). This is the only signal that needs no
        week-advance, so it is the one that catches the reported case (slate
        records carry pre-allocated request IDs, so even an aged
        skipped record reads has_result=True and the two unmap paths above
        never fire). Gating on FRESH finals means repeated polls of one
        world add no extra strikes. Three strikes; a game that finishes
        clears its record's strikes. The user's own game is exempt: it
        legitimately waits unofficial until they play and advance."""
    dead = set(state.get("dead_records") or [])
    clobber = dict(state.get("clobber_strikes") or {})
    silent = dict(state.get("silent_strikes") or {})
    before = set(dead)
    name_by_row = {i: t.name for i, t in enumerate(roster)}

    for rec in misfires.get("clobbered", set()) - user_base_recs:
        clobber[str(rec)] = clobber.get(str(rec), 0) + 1
        if clobber[str(rec)] >= 2:
            dead.add(rec)

    fresh = {g["id"] for rnd in bracket.get("rounds") or []
             for g in rnd["games"]
             if g.get("status") == "final"} - pre_final
    for rnd in bracket.get("rounds") or []:
        recs = plan.get(str(rnd["round"])) or []
        for gi, game in enumerate(rnd["games"]):
            rec = recs[gi] if gi < len(recs) else None
            if rec is None:
                continue
            if game.get("status") == "final":
                silent.pop(str(rec), None)
                continue
            if not fresh or rec in user_base_recs or rec in dead \
                    or any(s.get("team") in user_names for s in game["slots"]) \
                    or not all(s.get("type") == "team" for s in game["slots"]) \
                    or rec >= len(store.games):
                continue
            g = store.games[rec]
            if not _record_matches(g, game, name_by_row):
                continue  # wave not written/landed yet: no verdict either way
            silent[str(rec)] = silent.get(str(rec), 0) + 1
            if silent[str(rec)] >= 3:
                dead.add(rec)
                # unmap now so the next assignment relocates the game
                recs[gi] = None
                game.pop("record_index", None)

    if dead != before:
        notes.append(
            "CFB 27 is not simulating some of this week's game records; the "
            "affected matchups were moved to other records and will play on "
            "a following pass.")
        state["dead_records"] = sorted(dead)
    state["clobber_strikes"] = clobber
    state["silent_strikes"] = silent


def _cycle_active_round(bracket: dict[str, Any],
                        skip_rounds: set[str] | None = None) -> str | None:
    """Return the earliest unfinished round handled by cycle mode.

    A custom bracket is a dependency chain. Even when both teams in a later
    game are already known, that game must wait until every game in the
    earliest unfinished round is recorded. Otherwise the user's later game can
    consume a scarce host record and freeze the remaining games behind it.
    """
    skip_rounds = skip_rounds or set()
    for rnd in bracket.get("rounds") or []:
        key = str(rnd["round"])
        if key in skip_rounds:
            continue
        if any(game.get("status") != "final" for game in rnd["games"]):
            return key
    return None


def _enforce_cycle_round_gate(
        bracket: dict[str, Any], plan: dict[str, list[int | None]],
        skip_rounds: set[str] | None = None) -> list[str]:
    """Remove unfinished mappings that jumped ahead of the active round.

    This also repairs state written by older builds. Completed games remain
    untouched, including every captured winner and score from prior waves.
    """
    skip_rounds = skip_rounds or set()
    active = _cycle_active_round(bracket, skip_rounds)
    if active is None:
        return []
    active_seen = False
    removed = 0
    for rnd in bracket.get("rounds") or []:
        key = str(rnd["round"])
        if key in skip_rounds:
            continue
        if key == active:
            active_seen = True
            continue
        if not active_seen:
            continue
        assigned = plan.setdefault(key, [None] * len(rnd["games"]))
        for index, game in enumerate(rnd["games"]):
            if game.get("status") == "final" or index >= len(assigned) \
                    or assigned[index] is None:
                continue
            assigned[index] = None
            game.pop("record_index", None)
            game.pop("_disk", None)
            game.pop("_locked", None)
            game.pop("_advanced_inferred", None)
            removed += 1
    if not removed:
        return []
    return [
        f"Removed {removed} premature later-round matchup"
        f"{'s' if removed != 1 else ''}; the remaining Round {active} games "
        "will be completed first."
    ]


def _assign_records_cycle(bracket: dict[str, Any], plan: dict[str, list[int | None]],
                          pool: list[int], store: savesched.GameStore,
                          rows_by_name: dict[str, int],
                          priority_names: set[str] | None = None,
                          path_ids: set[str] | None = None,
                          immediate_path_ids: set[str] | None = None,
                          user_alive: bool = False,
                          skip_rounds: set[str] | None = None,
                          user_present: bool = True,
                          presentation_records: set[int] | None = None) -> bool:
    """Assign decided-but-unmapped bracket games to reusable records.

    A record is free when no unfinished bracket game currently maps to it.
    Only the earliest unfinished cycle round is eligible. Within that round,
    wave priority is the USER's own game first, then the immediate subtree that
    decides an open opponent slot in that game, then later sibling subtrees on
    the user's title path, then ordinary game order. This keeps a bye seed's
    direct feeder ahead of distant branches without allowing a ready game from
    the next round to strand unfinished games in the current one. Records whose
    base matchup involves the user carry the ENGINE's own user wiring: they host
    ONLY the user's game while the user is alive. Returns True when anything
    new was assigned."""
    priority_names = priority_names or set()
    path_ids = path_ids or set()
    immediate_path_ids = immediate_path_ids or set()
    skip_rounds = skip_rounds or set()
    presentation_records = presentation_records or set()
    active_round = _cycle_active_round(bracket, skip_rounds)
    if active_round is None:
        return False
    user_rows = {rows_by_name[n] for n in priority_names if n in rows_by_name}
    in_use: set[int] = set()
    for rnd in bracket.get("rounds") or []:
        recs = plan.get(str(rnd["round"])) or []
        for game, rec in zip(rnd["games"], recs):
            if rec is not None and game.get("status") != "final":
                in_use.add(rec)
    free = [r for r in pool if r not in in_use]
    presentation_owned = bool(in_use & presentation_records)
    user_recs = {r for r in free
                 if {store.games[r].away_row, store.games[r].home_row} & user_rows}
    pair_of: dict[frozenset, int] = {}
    for rec_idx in free:
        g = store.games[rec_idx]
        if g.away_row is not None and g.home_row is not None:
            pair_of.setdefault(frozenset((g.away_row, g.home_row)), rec_idx)

    # every assignable (decided, unmapped) game: user, user's path, the rest
    todo: list[tuple[int, int, int, str, dict[str, Any]]] = []
    for ri, rnd in enumerate(bracket.get("rounds") or []):
        key = str(rnd["round"])
        games = rnd["games"]
        assigned = plan.setdefault(key, [None] * len(games))
        if key in skip_rounds or key != active_round:
            continue
        for gi, game in enumerate(games):
            if assigned[gi] is not None or game.get("status") == "final":
                continue
            if not all(s.get("type") == "team" for s in game["slots"]):
                continue
            if any(s.get("team") in priority_names for s in game["slots"]):
                if not user_present:
                    # The user is eliminated or otherwise inactive, so their
                    # path is not assigned another playable record.
                    continue
                pri = 0
            elif game.get("id") in immediate_path_ids:
                pri = 1
            elif game.get("id") in path_ids:
                pri = 2
            else:
                pri = 3
            todo.append((pri, ri, gi, key, game))
    todo.sort(key=lambda t: (t[0], t[1], t[2]))

    changed = False
    # THE USER'S ENGINE RECORD IS SACRED: when the anchor week already has one,
    # it is the best host for the custom user game. No other game may take it;
    # overwriting it with a CPU
    # pairing destroyed the user's quarterfinal (observed: OSU rec 929 became
    # UTEP@Kansas). It is reserved for the user's OWN game only; while their
    # opponent is undecided it stays reserved and is FCS-filled at write time.
    # (The earlier "yield to path games" rule was for the abandoned rewind
    # design and is exactly what caused the overwrite.)
    def reserved(rec: int, pri: int) -> bool:
        return user_alive and rec in user_recs and pri != 0
    for pri, _ri, gi, key, game in todo:
        rows = frozenset(rows_by_name[s["team"]] for s in game["slots"]
                         if s.get("team") in rows_by_name)
        rec = None
        # A campus or plain-neutral user game needs a native CFP identity for
        # valid field art. The user must remain on their organic engine record
        # so CFB accepts the played result, and duplicating an identity freezes
        # advancement. Put one sibling custom game on a stock first-round
        # record instead. The presentation pass can then safely swap the two
        # identities because both owners belong to this same staged wave.
        if pri != 0 and not presentation_owned:
            rec = next((r for r in free if r in presentation_records
                        and not reserved(r, pri)), None)
        if rec is None:
            rec = pair_of.pop(rows, None) if len(rows) == 2 else None
        if rec is not None and reserved(rec, pri):
            rec = None
        if rec is None and pri == 0:
            # Prefer the record carrying the engine's own user wiring. When
            # CFB 27 put the user in a later ordinary bowl, no such record is
            # in Bowl Week 1 and the normal free-record path below hosts it.
            rec = next((r for r in free if r in user_recs), None)
        if rec is None:
            rec = next((r for r in free if not reserved(r, pri)), None)
            if rec is None:
                continue  # out of usable slots this wave
        free.remove(rec)
        if rec in presentation_records:
            presentation_owned = True
        user_recs.discard(rec)
        pair_of = {k: v for k, v in pair_of.items() if v != rec}
        plan[key][gi] = rec
        changed = True
    return changed


# ---------------------------------------------------------------------------
# bracket <-> results
# ---------------------------------------------------------------------------

def _record_matches(g: savesched.Game, game: dict[str, Any],
                    name_by_row: dict[int, str]) -> bool:
    """Whether a save record still holds the bracket game's matchup (guards
    against reading a reused record's NEW result into an OLD game)."""
    want = {s.get("team") for s in game["slots"] if s.get("type") == "team"}
    have = {name_by_row.get(g.away_row), name_by_row.get(g.home_row)}
    return len(want) == 2 and want == have


def _terminal_result_waiting(state: dict[str, Any],
                             store: savesched.GameStore,
                             roster: list[saveteams.Team]) -> bool:
    """Whether the completed calendar still has one championship to capture.

    CFB empties SeasonGameRequest as soon as the user advances past the
    national championship. The championship SeasonGame is already official
    at that point, but ``postseason_here`` is false because there is no next
    week slate. Treating that empty queue as a stale midseason rollback before
    `_fill_results` runs discards the entire live bracket on the third watcher
    poll. Only bypass the stale/projection gates when every earlier round is
    final and the mapped championship record itself proves the result exists.
    """
    if state.get("status") not in ("selected", "in_progress", "complete"):
        return False
    bracket = state.get("bracket") or {}
    if bracket.get("champion"):
        return True
    rounds = bracket.get("rounds") or []
    if not rounds:
        return False
    if any(game.get("status") != "final"
           for rnd in rounds[:-1] for game in rnd.get("games") or []):
        return False
    final_round = rounds[-1]
    games = final_round.get("games") or []
    if len(games) != 1 or games[0].get("status") == "final":
        return False
    plan = state.get("plan") or {}
    recs = plan.get(str(final_round.get("round"))) or []
    rec = recs[0] if recs else games[0].get("record_index")
    if rec is None or not isinstance(rec, int) or not 0 <= rec < len(store.games):
        return False
    game = store.games[rec]
    name_by_row = {i: team.name for i, team in enumerate(roster)}
    return bool(game.official and game.has_result and game.winner_row is not None
                and _record_matches(game, games[0], name_by_row))


def _fill_results(bracket: dict[str, Any], plan: dict[str, list[int]],
                  store: savesched.GameStore, roster: list[saveteams.Team],
                  *, allow_unofficial: bool = False,
                  unofficial_records: set[int] | None = None,
                  user_names: set[str] | None = None,
                  misfires: dict[str, set[int]] | None = None) -> None:
    """Copy results from the mapped save records into the bracket (winner +
    scores per game), then advance winners into feeder slots.

    Normally only OFFICIAL results count (no spoilers). In round-CYCLING mode
    (allow_unofficial) CPU games are advanced off the engine's pre-sim so the
    bracket can progress and the next round can be written. The USER's own
    games are the exception: they advance ONLY when official (the user has
    actually played and advanced the week), so a pre-sim never decides the
    user's game before they play it and their real result is never clobbered
    by a record reuse. Native mode passes the current slate as
    `unofficial_records`: CPU pre-sims count, while a user's unofficial result
    counts only when it is not an unpublished pre-sim. That lets Dynasty+
    discover the completed round and stage both participants into next week's
    records BEFORE the user advances and CFB allocates their participant requests.

    `misfires` collects the record indices of games this pass UNMAPPED
    because the engine never ran them: "skipped" (record aged to
    official-with-no-result: the engine declined the game outright) and
    "clobbered" (record went official holding a foreign matchup that is NOT
    one of the bracket's own finished games - a record reused for a new game
    that simply has not been written yet is routine, not a misfire). The
    caller quarantines repeat offenders so the rescheduled game lands on a
    record that actually works (the dead-record tar pit, observed 2026-07-10
    on a 128-team run)."""
    user_names = user_names or set()
    unofficial_records = unofficial_records or set()
    name_by_row = {i: t.name for i, t in enumerate(roster)}
    winners: dict[str, dict[str, Any]] = {}
    final_pairs = {frozenset(s.get("team") for s in g["slots"])
                   for rnd in bracket.get("rounds") or [] for g in rnd["games"]
                   if g.get("status") == "final"
                   and all(s.get("type") == "team" for s in g["slots"])}

    # a filled slot keeps its feeder game id (`game`) so the bracket UI can
    # still align games on their feeders and draw connectors; repair slots
    # filled by older builds that dropped it (the feeder is recoverable as
    # the unique previous-round game that team won; bye entrants match none)
    rounds = bracket.get("rounds") or []
    for ri in range(1, len(rounds)):
        won_by = {g.get("winner"): g["id"]
                  for g in rounds[ri - 1]["games"] if g.get("winner")}
        for game in rounds[ri]["games"]:
            for slot in game["slots"]:
                if slot.get("type") == "team" and not slot.get("game") \
                        and slot.get("team") in won_by:
                    slot["game"] = won_by[slot["team"]]

    def register(game):
        w = game.get("winner")
        if w:
            won = next((s for s in game["slots"] if s.get("team") == w), None)
            if won:
                winners[game["id"]] = {k: v for k, v in won.items()
                                       if k not in ("type", "game")}

    for rnd in bracket.get("rounds") or []:
        recs = plan.setdefault(str(rnd["round"]), [None] * len(rnd["games"]))
        for gi, game in enumerate(rnd["games"]):
            rec_idx = recs[gi] if gi < len(recs) else None
            # advance already-known winners into this game's TBD slots first
            # (keeping the feeder game id for bracket layout and connectors)
            for slot_i, slot in enumerate(game["slots"]):
                if slot.get("type") == "winner" and slot.get("game") in winners:
                    game["slots"][slot_i] = dict(winners[slot["game"]],
                                                 type="team", game=slot["game"])
            # An OFFICIAL result is locked; never re-read it. An unofficial
            # capture (a pre-sim or a game the user played but has not advanced
            # past) is re-read every sync AS LONG AS the record still holds the
            # matchup, so the user's real result replaces the engine's pre-sim.
            if game.get("_locked"):
                register(game)
                continue
            if rec_idx is None:
                continue
            game["record_index"] = rec_idx
            g = store.games[rec_idx]
            if not _record_matches(g, game, name_by_row):
                if game.get("status") != "final" and g.official:
                    # our write never made it into the save (the game clobbered
                    # it from memory, or a rewind rolled it away) and the record
                    # is now spent on a foreign matchup: unmap so the game gets
                    # a slot in the next wave instead of stalling forever
                    recs[gi] = None
                    game.pop("record_index", None)
                    if misfires is not None:
                        have = frozenset({name_by_row.get(g.away_row),
                                          name_by_row.get(g.home_row)})
                        if have not in final_pairs:
                            # the occupant is not one of OUR finished games:
                            # the engine ran its own game on this record
                            misfires.setdefault("clobbered", set()).add(rec_idx)
                    continue
                # otherwise the record was reused for a later-round game; keep
                # our last capture (do not read the new occupant's result)
                register(game)
                continue
            if g.official and not g.has_result and game.get("status") != "final":
                # the engine skipped this game entirely (a detached record
                # aged into official-with-no-result): the record is spent and
                # the game unplayed - unmap so the next wave reschedules it
                recs[gi] = None
                game.pop("record_index", None)
                if misfires is not None:
                    misfires.setdefault("skipped", set()).add(rec_idx)
                continue
            # the user's own game advances only when official; a CPU game may
            # advance off the engine pre-sim (unofficial) while cycling
            is_user_game = any(s.get("team") in user_names for s in game["slots"])
            native_unofficial = rec_idx in unofficial_records and (
                not is_user_game or not g.presimmed)
            usable = (g.official
                      or (allow_unofficial and not is_user_game)
                      or native_unofficial)
            if usable and g.has_result and g.winner_row is not None:
                game["_locked"] = bool(g.official)
                wname = name_by_row.get(g.winner_row)
                slot_names = [s.get("team") for s in game["slots"]]
                game["status"] = "final"
                # bracket slots are [top, bottom]; save is [away, home]
                a_slot = next((s for s in game["slots"] if s.get("team")
                               and name_by_row.get(g.away_row) == s.get("team")), None)
                h_slot = next((s for s in game["slots"] if s.get("team")
                               and name_by_row.get(g.home_row) == s.get("team")), None)
                scores = [None, None]
                for i, s in enumerate(game["slots"]):
                    if s is a_slot:
                        scores[i] = g.away_score
                    elif s is h_slot:
                        scores[i] = g.home_score
                game["scores"] = scores
                if wname and wname in slot_names:
                    game["winner"] = wname
                    won = next(s for s in game["slots"] if s.get("team") == wname)
                    winners[game["id"]] = {k: v for k, v in won.items()
                                           if k not in ("type", "game")}
    # champion
    last = (bracket.get("rounds") or [])[-1] if bracket.get("rounds") else None
    if last and last["games"] and last["games"][0].get("winner"):
        wname = last["games"][0]["winner"]
        won = next(s for s in last["games"][0]["slots"] if s.get("team") == wname)
        bracket["champion"] = {k: v for k, v in won.items() if k not in ("type", "game")}


def _recover_native_advancements(
        bracket: dict[str, Any], plan: dict[str, list[int]],
        store: savesched.GameStore, roster: list[saveteams.Team],
        slots: dict[str, list[int]], slate_now: set[int]) -> list[str]:
    """Recover real winners from the next native round's participants.

    Format 11 rewrote an already locked bowl week with the custom teams but
    reset too much of each record's result state. CFB 27 still resolved those
    games internally and advanced the winners into the next week, while the
    SeasonGame records exposed no readable score. Once the current request
    queue has moved to the next native round, exactly one participant from
    each prior custom pairing is authoritative proof of that game's winner.

    This never invents a result or score. It uses only the game's own next-round
    field, requires a unique contestant from the prior pairing, and runs only
    after the prior round's mapped records have left the current week.
    """
    rounds = bracket.get("rounds") or []
    if len(rounds) < 2 or not slate_now:
        return []
    kind_of = _round_kind_map(bracket)
    name_by_row = {i: team.name for i, team in enumerate(roster)}
    recovered: list[str] = []
    for index, rnd in enumerate(rounds[:-1]):
        key = str(rnd["round"])
        next_rnd = rounds[index + 1]
        next_kind = kind_of.get(str(next_rnd["round"]))
        next_records = [record for record in (slots.get(next_kind) or [])
                        if record < len(store.games)]
        if not next_records or not any(record in slate_now
                                       for record in next_records):
            continue
        mapped = [record for record in (plan.get(key) or [])
                  if record is not None]
        if mapped and any(record in slate_now for record in mapped):
            continue
        advanced = {
            name_by_row.get(row)
            for record in next_records
            for row in (store.games[record].away_row,
                        store.games[record].home_row)
            if row is not None
        } - {None}
        count = 0
        for game in rnd["games"]:
            if game.get("status") == "final" or not all(
                    slot.get("type") == "team"
                    for slot in game.get("slots") or []):
                continue
            contestants = {slot.get("team") for slot in game["slots"]
                           if slot.get("team")}
            winners = contestants & advanced
            if len(winners) != 1:
                continue
            game["winner"] = next(iter(winners))
            game["status"] = "final"
            game["scores"] = None
            game["_locked"] = True
            game["_advanced_inferred"] = True
            count += 1
        if count:
            round_label = rnd["name"][:-1] if rnd["name"].endswith("s") \
                else rnd["name"]
            recovered.append(
                f"Recovered {count} {round_label} winner"
                f"{'s' if count != 1 else ''} from CFB 27's "
                f"{next_rnd['name'].lower()} field. The game cleared the "
                "prior score links, so only the real advancing teams are "
                "available for those games.")
    return recovered


# ---------------------------------------------------------------------------
# writing the bracket into the save
# ---------------------------------------------------------------------------

def _bowl_stadium_handles(payload: bytes) -> dict[str, int]:
    """Map a bowl's name (lowercased) to its stadium uid handle, from the save's
    bowl catalog + CFP bowls. Lets a format's 'bowls' site (e.g. the Alamo Bowl)
    resolve to a real venue handle even when the record it lands on is a campus
    record (a CFP first-round slot), so a bowl-site game is not left at the home
    team's stadium."""
    from .saveparse import bowls as savebowls
    out: dict[str, int] = {}
    try:
        tbl = savebowls.parse(payload)
    except (ValueError, Exception):
        return out
    for b in tbl.bowls:
        h = getattr(b, "stadium_handle", None)
        if h and b.name:
            out.setdefault(b.name.strip().lower(), h)
    for pb in getattr(tbl, "playoff_bowls", []):
        h = getattr(pb, "stadium_handle", None)
        if h and pb.name:
            out.setdefault(pb.name.strip().lower(), h)
    return out


def _desired_venue(game: dict[str, Any], stadium_handles: list[int],
                   bowl_handles: dict[str, int] | None = None) -> int | None:
    """The venue the format demands for a game: a stadium handle for neutral,
    championship, or bowl sites, 0 to force the home team's campus, None = leave
    whatever the record has."""
    site = game.get("site") or {}
    stadium_idx = site.get("stadium")
    # A bowls-mode championship keeps site.type == "championship" so the
    # bracket and trophy presentation still identify it as the title game.
    # Resolve any explicit bowl object before the generic championship path;
    # otherwise a custom Rose/Orange/etc. title game silently stayed at the
    # stock championship stadium during the native handoff.
    if site.get("bowl") and bowl_handles:
        bowl = site.get("bowl") or {}
        handle = bowl_handles.get((bowl.get("name") or "").strip().lower())
        if handle:
            return handle
    if site.get("type") in ("neutral", "championship") and isinstance(stadium_idx, int) \
            and 0 <= stadium_idx < len(stadium_handles):
        return stadium_handles[stadium_idx]
    if site.get("type") == "bowl" and bowl_handles:
        # a bowls-mode round: resolve the specific bowl to its stadium handle so
        # the game plays at that bowl, not the record's default (which is the
        # home team's campus when the game landed on a CFP first-round slot).
        bowl = site.get("bowl") or {}
        handle = bowl_handles.get((bowl.get("name") or "").strip().lower())
        if handle:
            return handle
    if site.get("type") == "campus":
        return 0
    return None


def _cfp_round_rows(btable) -> dict[int, str]:
    """The BowlGame rows that are CFP-round identities, row -> stock kind.

    A row with a non-empty INTERNAL name is classified by that alone: the
    display slot gets relabeled by the wave writer, so a real bowl can carry
    a CFP-looking display name on a save mid-cycle (observed: the Cure Bowl
    relabeled 'National Championship'). The QF/SF/NCG rows ship with EMPTY
    internal names, so only those fall back to the display name."""
    out: dict[int, str] = {}
    for b in btable.bowls:
        n = (b.internal or b.name).lower().replace("_", "").replace(" ", "")
        if not b.internal and not b.name:
            continue  # the dead row
        if b.internal and "cfp" not in b.internal.lower() \
                and not any(k in b.internal.lower().replace("_", "")
                            for k in ("firstround", "quarterfinal",
                                      "semifinal", "championship")):
            continue  # a real bowl, whatever its display says
        if "conference" in n:
            continue
        if "firstround" in n:
            out[b.row] = "first_round"
        elif "quarterfinal" in n:
            out[b.row] = "quarterfinal"
        elif "semifinal" in n:
            out[b.row] = "semifinal"
        elif "championship" in n:
            out[b.row] = "championship"
    return out


def _venue_safe_for_record(bowl_row: int | None, venue: int | None,
                           cfp_rows: dict[int, str], ny6: set[int]) -> bool:
    """Whether writing `venue` onto a record with this bowl identity still
    renders a real field. FIELD ART KEYS OFF THE BOWL IDENTITY (+16), and a
    CFP-round identity only carries art for its NATIVE venues: the first round
    is campus-only, the quarterfinals/semifinals live at the New Year's Six
    stadiums (the engine resolves which bowl's art to use by matching +4
    against the PlayoffBowlsInfo stadium handles), and the title game's art
    travels with whatever venue is written. Anywhere else the engine has no
    art to compose and renders a blank orange field (observed in-game,
    2026-07-09). A real bowl's identity renders its art at any venue."""
    if not venue:
        return True  # campus / leave-as-is never breaks the art lookup
    kind = cfp_rows.get(bowl_row) if bowl_row is not None else None
    if kind is None or kind == "championship":
        return True
    return kind in ("quarterfinal", "semifinal") and venue in ny6


def _brand_rows(btable, kind_rows: list[int], kind: str,
                site: dict[str, Any], venue: int,
                ny6: set[int] | None = None) -> list[int]:
    """Bowl-identity candidates for the user's record, honoring the game's
    SITE. A campus game keeps the round's CFP branding (the in-game-verified
    native combo); a neutral- or bowl-sited game needs an identity whose art
    can render at that venue or the engine shows the blank orange field (see
    _venue_safe_for_record). Preference order: the named bowl of a bowls-mode
    site (real BowlGame rows only; the NY6 have none), then, for a bowl-mode
    QF/SF/NCG at a New Year's Six stadium, the round's own CFP identity (the
    engine's native combo, e.g. a quarterfinal at the Orange Bowl). Playable
    ordinary neutral-site user games keep a native CFP identity whose
    BowlGame venue is paired to the requested stadium by the field-branding
    pass. Named bowls keep their own identity. The Generic Bowl candidate below
    remains only for defensive callers. A neutral championship keeps the NCG
    identity because its art travels with the venue."""
    if not venue:
        return kind_rows
    real = [b for b in btable.bowls
            if not b.is_cfp and b.internal and b.stadium_handle
            and "generic" not in b.internal.lower()]
    name = ((site.get("bowl") or {}).get("name") or "").strip().lower()
    if name:
        by_name = [b.row for b in real
                   if name in (b.name.strip().lower(),
                               b.internal.replace("_", " ").strip().lower())]
        if by_name:
            return by_name
    site_type = site.get("type")
    if site_type == "neutral" and not site.get("bowl"):
        return kind_rows
    if site_type == "bowl" and venue in (ny6 or set()) \
            and kind in ("quarterfinal", "semifinal", "championship"):
        return kind_rows + [b.row for b in real]
    if kind == "championship":
        return kind_rows + [b.row for b in real]
    generic = btable.by_row(savebowls.GENERIC_ROW)
    if generic is not None:
        return [generic.row]
    # Defensive fallback for an unknown build without the decoded generic
    # identity. A real bowl still renders a field, even though its branding is
    # less accurate than the intended neutral-site presentation.
    return [b.row for b in real]


def _neutral_home_slots(game: dict[str, Any],
                        slots: list[dict[str, Any]]) \
        -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (home, away), making the better seed home at a plain neutral.

    Winner propagation preserves bracket branch order, not seed order. After
    an upset, slot zero can therefore contain the worse seed. That accidentally
    made the worse seed the field owner in later neutral rounds. Campus and
    named-bowl sites retain their authored bracket orientation.
    """
    home_slot, away_slot = slots[0], slots[1]
    site = game.get("site") or {}
    if site.get("type") != "neutral" or site.get("bowl"):
        return home_slot, away_slot

    def seed(slot: dict[str, Any]) -> int:
        for key in ("seed", "rank"):
            try:
                value = int(slot.get(key))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
        return 1_000_000

    if seed(away_slot) < seed(home_slot):
        home_slot, away_slot = away_slot, home_slot
    return home_slot, away_slot


def _use_home_team_field(game: dict[str, Any], away: int, home: int,
                         user_rows: set[int]) -> bool:
    """Whether a playable ordinary-neutral game needs team field art.

    CFB 27's unused Generic Bowl identity has no field-art package. Pairing it
    with a custom neutral stadium produced the orange placeholder surface in
    the SMU versus South Carolina test. Pairing a CFP identity and a save-level
    field-recipe string to the selected stadium was also ignored by the renderer
    in later SMU and Texas Tech tests. A user game with no named bowl therefore
    uses CFB's native campus-playoff relationship: SeasonGame has no stadium
    override, and the home team's temporary TeamStore stadium points at the
    selected physical venue. Named bowls keep their requested bowl field and
    presentation.
    """
    site = game.get("site") or {}
    return (site.get("type") == "neutral" and not site.get("bowl")
            and bool({away, home} & user_rows))


def _write_round(payload: bytearray, store: savesched.GameStore,
                 rnd: dict[str, Any], recs: list[int],
                 rows_by_name: dict[str, int],
                 stadium_handles: list[int],
                 report: list[str], *, pristine: bool = False,
                 user_rows: set[int] | None = None,
                 bowl_handles: dict[str, int] | None = None,
                 cfp_rows: dict[int, str] | None = None,
                 ny6: set[int] | None = None) -> list[int]:
    """Write one round's decided matchups into its mapped records. Returns
    the record indices written. Games with undecided slots or already-final
    results are skipped; records already official are never touched.

    `pristine` marks a PRE-LOCK target (the base-week snapshot): its records
    carry no engine result state to reset, and their trailing bytes hold the
    boundary's this-week markers, which a reset stamp would clobber (the
    engine could then skip locking the record). Only teams and venue are
    written there.

    THE USER'S SIDE IS PRESERVED ON IN-PLACE TARGETS ONLY: a locked week's
    participation is frozen by team and side, so on the engine's own live
    records the user stays on the side the boundary put them on (only the
    opponent slot changes, the Illinois-verified seam) and a displaced host's
    campus is pinned through an explicit stadium handle. A PRISTINE (pre-lock
    base) write instead honors the bracket's real orientation: the lock
    adopts the record wholesale on load, and the user request row is
    game-scoped, not side-scoped (set_user_pending), so the user can be the
    away team when the format says so, with the game presenting them as the
    visitor. The orientation actually written is persisted on the game
    (`_disk`) so the staged-wave check agrees with it."""
    user_rows = user_rows or set()
    written: list[int] = []
    for game, rec_idx in zip(rnd["games"], recs):
        if rec_idx is None or game.get("status") == "final":
            continue
        g = store.games[rec_idx]
        if g.official:
            continue
        slots = game["slots"]
        if len(slots) != 2 or any(s.get("type") != "team" for s in slots):
            continue
        # A plain neutral always gives the better seed the home identity. Slot
        # order alone is insufficient after an upset because feeder branches,
        # rather than seeds, determine which winner lands in each slot.
        home_slot, away_slot = _neutral_home_slots(game, slots)
        home = rows_by_name.get(home_slot.get("team"))
        away = rows_by_name.get(away_slot.get("team"))
        if home is None or away is None:
            continue
        selected_venue = _desired_venue(game, stadium_handles, bowl_handles)
        want_venue = selected_venue
        # IN-PLACE targets only: keep the user on the side the engine locked
        # them on (participation is frozen by the lock; the Illinois-verified
        # seam is opponent-only) and pin the custom host's campus through an
        # explicit stadium handle instead. PRISTINE (pre-lock base) writes
        # honor the bracket's real orientation: the lock adopts the record's
        # matchup wholesale on load, and preserving the user's side there
        # presented every away game as a home game (the user's band, sideline,
        # conference logo, and "at home" menu framing at the opponent's
        # stadium; reported on an NFL-style format, Florida at SMU).
        if not pristine and user_rows and ({away, home} & user_rows):
            side = ('away' if g.away_row in user_rows
                    else 'home' if g.home_row in user_rows else None)
            if side is not None and (side == 'home') != (home in user_rows):
                if want_venue == 0:
                    want_venue = savepolls.home_stadium_handle(bytes(payload), home) or 0
                away, home = home, away
        home_team_field = _use_home_team_field(game, away, home, user_rows)
        disk = game.setdefault("_disk", {})
        if home_team_field and selected_venue:
            # A previous build put a recipe string on the selected Stadium row,
            # but CFB ignored it and rendered the orange placeholder. Undo that
            # legacy override during migration, even while this game is open.
            old_recipe = disk.pop("field_recipe", None) or {}
            old_index = old_recipe.get("stadium")
            old_name = old_recipe.get("name")
            if old_index is not None and old_name:
                try:
                    if savestadiums.field_recipe_name(
                            bytes(payload), int(old_index)) == old_name \
                            and savestadiums.set_field_recipe(
                                payload, int(old_index),
                                old_recipe.get("original") or ""):
                        report.append(
                            f"stadium {old_index}: removed the obsolete field "
                            "recipe override")
                except (IndexError, UnicodeError, ValueError):
                    pass

            # Format 20 sometimes lost the metadata above during a dry-run
            # probe, leaving only the recipe string in the save. Clear any
            # such orphan directly from the selected stadium. The new native
            # relationship must resolve the field from HomeTeam, not from an
            # earlier game's stale Stadium override.
            selected_index = ({handle: index for index, handle
                               in enumerate(stadium_handles)}.get(selected_venue))
            if selected_index is not None:
                try:
                    orphan_recipe = savestadiums.field_recipe_name(
                        bytes(payload), selected_index)
                    if orphan_recipe and savestadiums.set_field_recipe(
                            payload, selected_index, ""):
                        report.append(
                            f"stadium {selected_index}: cleared orphaned legacy "
                            f"field recipe {orphan_recipe!r}")
                except (IndexError, UnicodeError, ValueError):
                    pass

            # This is the game's own working campus-playoff shape. A zero
            # SeasonGame venue resolves through HomeTeam.Stadium. Temporarily
            # point that team reference at the user's selected physical venue,
            # then restore it after the game becomes final.
            prior = disk.get("team_stadium") or {}
            try:
                current_home = savestadiums.team_home_handle(
                    bytes(payload), home)
                original_home = (
                    prior.get("original")
                    if prior.get("team") == home
                    and prior.get("selected") == selected_venue
                    and prior.get("original") is not None
                    else current_home
                )
                disk["team_stadium"] = {
                    "team": home,
                    "selected": selected_venue,
                    "original": original_home,
                }
                if savestadiums.set_team_home_handle(
                        payload, home, selected_venue):
                    report.append(
                        f"team {home}: temporary home stadium -> "
                        f"{selected_venue:#x} for native playoff field art")
                want_venue = 0
            except (IndexError, ValueError):
                # A malformed/nonstandard TeamStore is safer left at its
                # explicit selected venue than partially rewritten.
                disk.pop("team_stadium", None)
        # The presentation definition is updated after every matchup in the
        # wave is known, where a CFP identity can be swapped safely. Mark the
        # user record as write-worthy even when its teams and stadium already
        # match so a format migration can repair presentation alone.
        branding_changed = home_team_field
        # IN-PLACE targets are the ENGINE's own records (stock mode / the
        # calendar tail): a CFP-round identity there cannot be repointed
        # safely (a duplicated identity freezes the engine on advance), so
        # when the format's site would leave that identity with no field art
        # (the blank orange field), the venue write is refused and the record
        # keeps a native venue instead. If a PREVIOUS build already broke the
        # record's venue, it is repaired to a native one. Pristine (base-wave)
        # writes are exempt: there the identity follows the site instead
        # (_brand_rows). A campus write (0) is left alone, it is the format's
        # explicit intent and campus fields carry their own art.
        effective_bowl_row = None if home_team_field else g.bowl_row
        if not pristine and want_venue and cfp_rows is not None and \
                not _venue_safe_for_record(effective_bowl_row, want_venue,
                                           cfp_rows, ny6 or set()):
            kind_r = (cfp_rows.get(effective_bowl_row) or "").replace("_", " ")
            if _venue_safe_for_record(effective_bowl_row, g.venue_uid or 0,
                                      cfp_rows, ny6 or set()):
                want_venue = None  # record already native: leave it
            elif kind_r in ("quarterfinal", "semifinal") and ny6:
                want_venue = sorted(ny6)[0]  # repair a previously-broken write
            else:
                want_venue = 0  # first round: campus is its only native venue
            report.append(f"game {rec_idx}: kept a native venue (a {kind_r} "
                          "record has no field art for the requested site)")
        # Preserve presentation metadata recorded by the field-branding pass.
        # A dry-run probe also walks this writer against a temporary payload.
        # Replacing ``_disk`` here erased ``bowl_row`` and ``field_recipe``
        # from the REAL live bracket even though the probe never wrote the
        # save. The next poll then treated the neutral field as unstaged and
        # produced an endless Update/Load loop. Teams and venue are refreshed;
        # presentation keys survive until an actual branding pass updates them.
        disk.update({"away": away, "home": home, "venue": want_venue})
        matchup_ok = (g.away_row, g.home_row) == (away, home)
        venue_ok = want_venue is None or (g.venue_uid or 0) == want_venue
        # A WAVE GAME MUST READ AS RESULT-LESS WHEN written. The reset differs
        # by target:
        #   pristine (base RELOAD): reproduce the engine's own pre-lock
        #     arrival state - ZERO the pending refs (clear_engine_state), the
        #     shape verified to pre-sim fresh on load (Kentucky base). Keeping
        #     the refs on a fresh reload is the untested path.
        #   in-place (native calendar): match the working reference tool
        #     exactly. Set HomeScheduled and clear only IsSimmed and
        #     HasBeenPublished, preserving every result/pending object for the
        #     engine to reuse when it resolves the replacement matchup.
        stale = g.has_result or g.presimmed
        if matchup_ok and venue_ok and not stale:
            # A format-11 record can already hold the correct teams but carry
            # AwayScheduled, the status that produced a detached no-result
            # game. Repair that status even when no stale result remains.
            if not pristine and not g.official \
                    and payload[g.offset + 84] & 0xF0 != 0x60:
                report.extend(savesched.reset_locked_matchup_status(payload, g))
                written.append(rec_idx)
            elif branding_changed:
                written.append(rec_idx)
            continue
        if stale:
            if pristine:
                report.extend(savesched.clear_engine_state(payload, g))
            else:
                report.extend(savesched.reset_locked_matchup_status(payload, g))
        elif not pristine:
            report.extend(savesched.reset_locked_matchup_status(payload, g))
        if not matchup_ok:
            report.extend(savesched.set_matchup(payload, g, away_row=away, home_row=home))
        if want_venue is not None and not venue_ok:
            report.extend(savesched.set_venue(payload, g, want_venue or None))
        written.append(rec_idx)
    return written


def _wave_staged(payload: bytes, bracket: dict[str, Any],
                 plan: dict[str, list[int | None]],
                 store: savesched.GameStore, rows_by_name: dict[str, int],
                 stadium_handles: list[int],
                 skip_rounds: set[str] | None = None,
                 bowl_handles: dict[str, int] | None = None,
                 user_rows: set[int] | None = None,
                 bowl_table: savebowls.BowlTable | None = None) -> bool:
    """Whether the CURRENT save already carries every unfinished mapped wave
    game (right matchup, right venue, record not spent). True means the user
    is mid-wave and the world must not be disturbed; False means a base
    rewrite is due (a new wave was assigned, a record went official, or the
    engine clobbered a write)."""
    user_rows = user_rows or set()
    cfp_rows = _cfp_round_rows(bowl_table) if bowl_table else {}
    for rnd in bracket.get("rounds") or []:
        if skip_rounds and str(rnd["round"]) in skip_rounds:
            continue  # calendar rounds are probed by the tail's dry run
        recs = plan.get(str(rnd["round"])) or []
        for game, rec in zip(rnd["games"], recs):
            if rec is None or game.get("status") == "final":
                continue
            slots = game["slots"]
            if len(slots) != 2 or any(s.get("type") != "team" for s in slots):
                continue
            if rec >= len(store.games):
                return False
            g = store.games[rec]
            if g.official:
                return False
            disk = game.get("_disk")
            if disk:
                # the orientation/venue the writer actually chose (the user's
                # engine side may be preserved against bracket order)
                if (g.away_row, g.home_row) != (disk.get("away"), disk.get("home")):
                    return False
                want_venue = disk.get("venue")
                if want_venue is not None and (g.venue_uid or 0) != want_venue:
                    return False
            else:
                home = rows_by_name.get(slots[0].get("team"))
                away = rows_by_name.get(slots[1].get("team"))
                if (g.away_row, g.home_row) != (away, home):
                    return False
                want_venue = _desired_venue(game, stadium_handles, bowl_handles)
                if want_venue is not None and (g.venue_uid or 0) != want_venue:
                    return False
            if _use_home_team_field(
                    game,
                    g.away_row if g.away_row is not None else -1,
                    g.home_row if g.home_row is not None else -1,
                    user_rows):
                team_stadium = (disk or {}).get("team_stadium") or {}
                team_row = team_stadium.get("team")
                selected = team_stadium.get("selected")
                if team_row is None or not selected:
                    # Format 20 and older used the Stadium field-recipe string.
                    # It parses correctly but CFB ignores it when rendering.
                    return False
                if g.home_row != team_row or (g.venue_uid or 0) != 0:
                    return False
                try:
                    if savestadiums.team_home_handle(payload, int(team_row)) \
                            != selected:
                        return False
                except (IndexError, ValueError):
                    return False
                bowl = (bowl_table.by_row(g.bowl_row)
                        if bowl_table is not None and g.bowl_row is not None
                        else None)
                expected_bowl = (disk or {}).get("bowl_row")
                if expected_bowl is not None and g.bowl_row != expected_bowl:
                    return False
                # A native home-playoff field has no explicit stadium on either
                # the SeasonGame or its CFP BowlGame presentation identity.
                # The selected physical venue is reached through Team.Stadium.
                if g.bowl_row not in cfp_rows or bowl is None \
                        or bowl.stadium_handle:
                    return False
    return True


def _regenerate_bowls(payload: bytearray, store: savesched.GameStore,
                      roster: list[saveteams.Team],
                      field_names: set[str], report: list[str],
                      keep_records: set[int] | None = None) -> int:
    """Fix the 32 bowls around a custom field: teams the custom playoff took
    are swapped out of their bowls; teams the ENGINE's own playoff took (but
    the custom field did not) fill those openings, then the best remaining
    bowl-eligible teams. Only unofficial bowls are touched.

    With a SMALLER field than the game's, the freed engine-playoff teams get
    the bowl slots; with a LARGER field, bowls lose double-booked teams to
    the substitutes bench. Either way no team plays twice in the postseason.

    `keep_records` exempts bowl records that HOST custom playoff games
    (native mode's borrowed first-round bowls): their field-team matchups
    are the bracket's own writes, not double-bookings to swap away.
    """
    name_of = {i: t.name for i, t in enumerate(roster)}
    row_of = {t.name: i for i, t in enumerate(roster)}
    slots = _postseason_slots(bytes(payload))
    engine_playoff_rows = {t for i in slots["first_round"] + slots["quarterfinal"]
                           for t in (store.games[i].away_row, store.games[i].home_row)
                           if t is not None}
    field_rows = {row_of[n] for n in field_names if n in row_of}

    bowl_games = [g for g in store.games
                  if g.bowl_row is not None and g.index not in (keep_records or set())
                  and g.index not in {i for v in slots.values() for i in v}]
    booked = {t for g in bowl_games for t in (g.away_row, g.home_row) if t is not None}
    # During a pre-boundary NEXT-round stage, this week's engine CFP games are
    # still live. A freed engine-playoff team is not a valid bowl substitute
    # when it already appears elsewhere in the current request slate. The old
    # bench admitted exactly that shape (Indiana in record 924 and bowl 394),
    # freezing small native brackets before their custom round arrived.
    slate = set(savesched.week_slate(bytes(payload)))
    live_slate_rows = {
        row for record in slate if record < len(store.games)
        for row in (store.games[record].away_row, store.games[record].home_row)
        if row is not None
    }

    # the bench: engine-playoff teams our field freed, then the best remaining
    # bowl-eligible (6+ official wins) unbooked teams, best rank first
    from .saveparse import polls as savepolls
    from .saveparse import results as saveresults
    rank_of = {t.row: t.rank for t in savepolls.parse(bytes(payload))}
    bench = sorted((r for r in engine_playoff_rows
                    if r not in field_rows and r not in booked
                    and r not in live_slate_rows),
                   key=lambda r: rank_of.get(r, 999))
    records = saveresults.build_blocks(bytes(payload), user_row=None)["team_records"]
    extras = sorted(
        (r for r, (w, _l) in records.items()
         if w >= 6 and r not in field_rows and r not in booked
         and r not in engine_playoff_rows and r not in live_slate_rows
         and r < len(roster)),
        key=lambda r: rank_of.get(r, 999))
    bench.extend(extras)

    # A large custom field can consume more bowl teams than the official
    # six-win pool can replace. The reference 16-team tool fills the remaining
    # openings with unused real FBS programs. CFB 27 tolerates that complete
    # pairing; it does not tolerate a request record whose away or home side
    # is blank. Add every still-unused FBS row as the final substitute tier.
    bench_set = set(bench)
    fallbacks = sorted(
        (r for r, team in enumerate(roster)
         if team.name and not team.name.upper().startswith("FCS ")
         and r not in field_rows and r not in booked
         and r not in engine_playoff_rows and r not in live_slate_rows
         and r not in bench_set),
        key=lambda r: rank_of.get(r, 999))
    bench.extend(fallbacks)

    changed = 0
    for g in bowl_games:
        if g.official:
            continue
        away, home = g.away_row, g.home_row
        new_away, new_home = away, home
        if away in field_rows and bench:
            new_away = bench.pop(0)
        if home in field_rows and bench:
            new_home = bench.pop(0)
        if (new_away, new_home) == (away, home):
            continue
        if g.has_result or g.presimmed:
            report.extend(
                savesched.reset_locked_matchup_status(payload, g)
                if g.index in slate
                else savesched.clear_engine_state(payload, g))
        report.extend(savesched.set_matchup(
            payload, g, away_row=new_away, home_row=new_home))
        for r_old, r_new in ((away, new_away), (home, new_home)):
            if r_old != r_new:
                report.append(
                    f"bowl game {g.index}: {name_of.get(r_old, '?')} -> "
                    f"{name_of.get(r_new) or '?'} (custom playoff field)")
        changed += 1
    return changed


# bracket round name -> the in-game game label (matching the game's own CFP
# labels; extra rounds a huge bracket adds get a "CFP <name>" label).
_ROUND_LABELS = {
    "First Round": "CFP First Round",
    "Quarterfinals": "CFP Quarterfinal",
    "Semifinals": "CFP Semifinal",
    "National Championship": "National Championship",
}


def _round_label(round_name: str) -> str:
    if round_name in _ROUND_LABELS:
        return _ROUND_LABELS[round_name]
    return f"CFP {round_name}"[:savebowls.NAME_CAP]


# ---------------------------------------------------------------------------
# the walkthrough guide (the bracket page's step-by-step boxes)
# ---------------------------------------------------------------------------

def _build_guide(*, status: str, mode: str | None,
                 bracket: dict[str, Any] | None,
                 plan: dict[str, list[int | None]] | None,
                 store: savesched.GameStore | None,
                 user_names: set[str],
                 needs_write: bool, awaiting_reload: bool,
                 slate_len: int | None,
                 at_ccg: bool = False, prepare_due: bool = False,
                 prepared: bool = False, user_native: bool = True,
                 anchor_pending: bool = False,
                 calendar_rounds: set[str] | None = None,
                 tail_ready_rounds: set[str] | None = None,
                 user_present: bool = True,
                 target_week: int | None = None,
                 restore_pending: bool = False,
                 engrave_state: str | None = None,
                 anchor_locked: bool = False,
                 native_rounds: set[str] | None = None,
                 boundary_recovery: dict[str, Any] | None = None,
                 legacy_native_cache_recovery: bool = False) -> dict[str, Any]:
    """The step-by-step walkthrough the bracket page renders above the
    bracket: one box per phase (reach the playoff, each round, completion),
    each with ordered steps and a cursor at the user's current step, derived
    entirely from the live sync state so it tracks the save in real time."""
    user = next(iter(user_names), None)
    phases: list[dict[str, Any]] = []
    projected = status in (None, "projected") or not bracket or not bracket.get("rounds")
    # the championship-week record adjustment only exists for a team the
    # engine would otherwise snub; a team already in the engine's field (a
    # top-12 or strong-record seed) needs NOTHING at championship week and
    # goes straight to advancing into bowl week. Only surface the prepare
    # step when it is actually due or already done, so a strong seed is
    # never left staring at an update task with no button.
    prepare_shown = prepare_due or prepared
    steps: list[dict[str, Any]] = [
        {"id": "season", "label": "Finish the season in CFB 27",
         "detail": "Play or sim to conference championship week.",
         "state": "done" if (at_ccg or not projected) else "current"},
    ]
    if prepare_shown:
        steps.append({
            "id": "prepare", "label": "Championship week: update the dynasty file",
            "detail": "BEFORE advancing past the conference championships, exit "
                      "to the game's main menu and press Update Dynasty File. "
                      "Your team's record is briefly adjusted so the game gives "
                      "you a postseason matchup (restored once the playoff "
                      "starts), which is what makes your playoff games playable.",
            "state": "done" if (prepared or not projected) else "current"})
    if not projected:
        arrive_state = "done"
    elif prepare_shown:
        arrive_state = "current" if prepared else "todo"
    else:
        # no adjustment needed: at championship week, advancing is the move
        arrive_state = "current" if at_ccg else "todo"
    steps.append({
        "id": "arrive", "label": "Advance into bowl week, then exit",
        "detail": (("Reload the dynasty so the game picks up the update, then "
                    if prepare_shown else "In CFB 27, ")
                   + "advance past the conference championships and exit to the "
                     "main menu. The app freezes your field and sets up the "
                     "first round automatically."),
        "state": arrive_state})
    phases.append({
        "key": "selection", "title": "Reach the playoff",
        "state": "current" if projected else "done",
        "steps": steps,
    })
    guide = {"mode": mode, "status": status, "phases": phases, "v": 4}
    if projected:
        return guide

    if boundary_recovery:
        blocked = bool(boundary_recovery.get("blocked"))
        phases.append({
            "key": "boundary-recovery",
            "title": ("A prior-week save is required" if blocked
                      else "Rebuild this bowl week safely"),
            "state": "current",
            "steps": [{
                "id": "recover",
                "label": ("Do not replay this matchup" if blocked
                          else "Load, advance one bowl week, then exit"),
                "detail": (
                    "CFB created only one of the two participant requests, so "
                    "a played result cannot save. Dynasty+ could not find the "
                    "immediately preceding week needed to rebuild it safely."
                    if blocked else
                    "Dynasty+ restored the prior bowl week with all completed "
                    "playoff results intact and staged both teams for this "
                    "round. Load the dynasty, advance exactly one bowl week, "
                    "then exit to the main menu and press Update Dynasty File. "
                    "Do not replay the matchup until the app confirms the new "
                    "week has both participant requests."),
                "state": "current",
            }],
        })
        return guide

    if anchor_pending and anchor_locked:
        # the current week was already locked and simmed by the engine before
        # the playoff could schedule into it (the user loaded into the week
        # before the app first synced): a wave written here would never sim,
        # so the only way forward is a fresh, not-yet-locked week
        phases.append({
            "key": "anchor",
            "title": "Move to a fresh bowl week",
            "state": "current",
            "steps": [{
                "id": "advance",
                "label": "Play or sim this week, then advance and exit",
                "detail": "CFB 27 locked and simmed this week's games before "
                          "the playoff could schedule into it, so this week "
                          "cannot host the bracket. In CFB 27, play or sim "
                          "the week as normal, advance to the next bowl week, "
                          "then exit to the main menu. The playoff sets up "
                          "there automatically.",
                "state": "current"}],
        })
    elif anchor_pending:
        phases.append({
            "key": "anchor",
            "title": (f"Advance to bowl week {target_week}" if target_week
                      else "Reach your matchup week"),
            "state": "current",
            "steps": [{
                "id": "advance",
                "label": (f"Advance to bowl week {target_week}" if target_week
                          else "Advance to the week of your game"),
                "detail": ("You have a first-round bye. In CFB 27, advance to "
                           + (f"bowl week {target_week}" if target_week
                              else "the bowl week that holds your first game")
                           + ", then exit to the main menu. The playoff anchors "
                             "there and your games begin."),
                "state": "current"}],
        })

    rounds = bracket["rounds"]
    current_ri = next((i for i, rnd in enumerate(rounds)
                       if any(g.get("status") != "final" for g in rnd["games"])), None)
    champion = bracket.get("champion")
    user_in_bracket = any(s.get("team") in user_names
                          for s in bracket.get("seeds") or [])
    user_out_since: int | None = None  # round index the user was eliminated in
    for ri, rnd in enumerate(rounds):
        games = rnd["games"]
        finals = sum(1 for g in games if g.get("status") == "final")
        if current_ri is None or champion:
            ph_state = "done"
        elif anchor_pending:
            ph_state = "done" if ri < (current_ri or 0) else "upcoming"
        else:
            ph_state = ("done" if ri < current_ri
                        else "current" if ri == current_ri else "upcoming")

        # the user's place in this round
        ug = next((g for g in games
                   if any(s.get("team") == user for s in g["slots"])), None)
        user_line = None
        user_pending = False
        if user_out_since is not None:
            pass  # eliminated earlier; the round is CPU-only for the user
        elif ug is not None:
            opp = next((s.get("team") for s in ug["slots"]
                        if s.get("type") == "team" and s.get("team") != user), None)
            if ug.get("status") == "final":
                won = ug.get("winner") == user
                score = ug.get("scores")
                tail = ""
                if score and None not in score:
                    tail = f" {max(score)}-{min(score)}" if won else f" {min(score)}-{max(score)}"
                user_line = (f"You beat {opp}{tail}" if won else f"Your run ended against {opp}{tail}")
                if not won:
                    user_out_since = ri
            else:
                user_pending = True
                if not user_present:
                    user_line = ((f"Your game: vs {opp}, " if opp
                                  else "Your game comes ")
                                 + "after you advance to its week; finish the "
                                   "passes here first")
                else:
                    user_line = (f"Your game: vs {opp}" if opp
                                 else "Your game: opponent to be decided")
        elif user is not None and user_in_bracket and user_out_since is None:
            # only a user actually IN the field waits on an opponent; a
            # spectator (not seeded) must not be told they "sit this pass out"
            if ri > 0:
                user_line = ("Waiting on your next opponent: you sit this pass "
                             "out; load, exit to the menu, and update again"
                             if ph_state == "current" else
                             "Your spot depends on an earlier result")
            elif ph_state == "current":
                # A first-round bye seed can show the non-field placeholder
                # the cycle writes to hold their native user record. Explain
                # that it is not a bracket game and must not be played.
                user_line = ("You have a first-round bye. Your dynasty may show "
                             "a temporary matchup against a non-playoff team "
                             "this pass. Do not play it. It only holds your "
                             "native game record while the opening round runs, "
                             "and your real opponent replaces it after the next "
                             "update.")

        # the round's step list (cycle mode: the wave loop; calendar rounds
        # ride the game's own bowl weeks instead).
        multi = bool(slate_len) and len(games) > slate_len
        has_user = user_pending and ph_state != "done" and user_present
        on_calendar = str(rnd["round"]) in (calendar_rounds or set())
        # a hybrid bracket's endgame rounds (its final <=16-team run) use the
        # native forward-calendar steps; its earlier rounds use the cycle
        # steps. A pure native bracket is native for every round.
        is_native_round = mode == "native" or str(rnd["round"]) in (native_rounds or set())
        if is_native_round:
            native_here = str(rnd["round"]) in (tail_ready_rounds or set())
            steps = [
                {"id": "advance",
                 "label": "Advance to this round's bowl week",
                 "detail": "Every round plays on the game's own calendar. "
                           "When the prior round finishes, Dynasty+ stages "
                           "this matchup before the advance so CFB can build "
                           "a complete playable game at the week boundary."},
                {"id": "update",
                 "label": ("Update the dynasty file on arrival"
                           if native_here
                           else "Update the dynasty file before advancing"),
                 "detail": ("Exit to the main menu and press Update Dynasty "
                            "File before loading this bowl week."
                            if native_here else
                            "After the prior round is finished, exit to the "
                            "main menu and press Update Dynasty File before "
                            "advancing. Dynasty+ puts both teams into CFB's "
                            "next-round records before participant requests are "
                            "allocated.")},
                {"id": "load",
                 "label": "Load your dynasty",
                 "detail": (("Your correct matchup is scheduled. Open the "
                              "Actions tab and choose Play Game."
                              if has_user else
                              "Play or sim the week as normal.")
                            if native_here else
                            "Reload the same dynasty so CFB has the staged next "
                            "round in memory, then advance to its bowl week. "
                            "The Play Game action appears after that advance.")},
            ]
            if has_user:
                opp_txt = f" vs {opp}" if ug is not None and opp else ""
                steps.append({"id": "play",
                              "label": f"Play your game{opp_txt}",
                              "detail": "It appears as Play Game on the "
                                        "Actions tab. When it finishes, exit "
                                        "the dynasty to the main menu. Do not "
                                        "advance the bowl week yet."})
            steps.append({
                "id": "finish",
                 "label": "Update, reload, then advance",
                 "detail": ("After your game, exit to the main menu and update "
                            "the dynasty file. Reload the dynasty, then advance "
                            "the bowl week. This lets Dynasty+ stage the next "
                            "matchups before CFB allocates participant requests."
                           if has_user else
                           "Once the games are simulated, exit to the main menu "
                           "and update. Reload the dynasty, then advance so the "
                           "next round is built with both teams already set.")})
        elif mode == "cycle" and on_calendar:
            steps = [
                {"id": "advance",
                 "label": "Advance to the next bowl week",
                 "detail": "This round plays on the game's own calendar "
                           "(quarterfinals on bowl week 2, semifinals on week "
                           "3, the championship on championship week)."},
                {"id": "update",
                 "label": "Update the dynasty file when prompted",
                 "detail": "After arriving at the week, exit to the main menu "
                           "and press Update; the app sets this round's "
                           "matchups (the game refills these slots on its own "
                           "at every advance, so the update comes after)."},
                {"id": "load",
                 "label": "Load your dynasty",
                 "detail": ("Your correct matchup is scheduled. Open the "
                            "Actions tab and choose Play Game."
                            if has_user else
                            "Play or sim the week as normal.")},
            ]
            if has_user:
                opp_txt = f" vs {opp}" if ug is not None and opp else ""
                steps.append({"id": "play",
                              "label": f"Play your game{opp_txt}",
                              "detail": "It appears as Play Game on the Actions "
                                        "tab, like any other week."})
        elif mode == "cycle":
            steps = [
                {"id": "update",
                 "label": "Update the dynasty file",
                 "detail": "In CFB 27, exit the dynasty to the game's main menu, "
                           "then press the Update Dynasty File button below."},
                {"id": "load",
                 "label": "Load your dynasty",
                 "detail": ("Your correct matchup is scheduled. Open the "
                            "Actions tab and choose Play Game."
                            if has_user and user_native else
                            "The games are scheduled into the bowl week; load in, "
                            "then exit straight back to the main menu and the "
                            "simmed results are recorded automatically.")},
            ]
            if has_user and not user_native:
                steps.append({"id": "finish",
                              "label": "Advance the week, then exit",
                              "detail": "Your matchup is in the schedule but the game "
                                        "cannot offer it for play this season (the "
                                        "championship-week update step was missed, so "
                                        "the game never scheduled you itself). It is "
                                        "simmed when you advance; the result is "
                                        "recorded like every other game."})
            elif has_user:
                opp_txt = f" vs {opp}" if ug is not None and opp else ""
                steps.append({"id": "play",
                              "label": f"Play your game{opp_txt}",
                              "detail": "It appears as Play Game on the Actions tab, "
                                        "like any other week."})
                steps.append({"id": "finish",
                              "label": "Advance the week, then exit",
                              "detail": "After your game, advance to the next week and "
                                        "exit to the main menu so your result and the "
                                        "simmed games are recorded."})
            if multi:
                steps.append({"id": "repeat",
                              "label": "Repeat until the round is recorded",
                              "detail": f"A bowl week holds about {slate_len} games, so "
                                        "this round takes several passes; the app rolls "
                                        "the week back and asks you to update again "
                                        "each time."})
        else:
            steps = [
                {"id": "update",
                 "label": "Update the dynasty file when prompted",
                 "detail": "After every advance, exit to the main menu and press "
                           "Update Dynasty File when the banner appears."},
                {"id": "play",
                 "label": "Play or sim the round in game",
                 "detail": "The round rides the game's own postseason calendar."},
            ]

        if legacy_native_cache_recovery and ph_state == "current" and has_user:
            steps = [
                {"id": "refresh",
                 "label": "One-time recovery for this existing save",
                 "detail": "This dynasty entered a native CFP record before the "
                           "route guard was installed. In CFB 27, transfer Dynasty "
                           "Owner to another team, retire and immediately rehire "
                           "the coach at your playoff team, then transfer Dynasty "
                           "Owner back. Protect a user-created coach before its "
                           "first retirement. This refreshes CFB's hidden "
                           "postseason route."},
                {"id": "play",
                 "label": f"Replay your game{f' vs {opp}' if opp else ''}",
                 "detail": "Load the same dynasty and use its single Play Game "
                           "action. Do not update the file again before playing. "
                           "A persisted result proves the route is repaired, and "
                           "later rounds continue normally."},
            ]

        # the cursor: which step the user is on right now (current round only)
        cursor = None
        if ph_state == "current":
            if legacy_native_cache_recovery and has_user:
                cursor = "refresh"
            elif needs_write:
                cursor = "update"
            elif awaiting_reload:
                cursor = "load"
            elif has_user and plan is not None and store is not None:
                recs = plan.get(str(rnd["round"])) or []
                rec = next((r for g_, r in zip(games, recs) if g_ is ug), None)
                gr = store.games[rec] if rec is not None and rec < len(store.games) else None
                if is_native_round:
                    # native rounds move forward with the calendar: the game
                    # is playable only once its week is the current slate;
                    # before that the move is to advance to it (never "play"
                    # on a week the game is not on)
                    if str(rnd["round"]) not in (tail_ready_rounds or set()):
                        cursor = "advance"
                    elif gr is not None and gr.has_result and not gr.official:
                        cursor = "finish"
                    else:
                        cursor = "play"
                elif on_calendar:
                    # a calendar round is playable only once the user has
                    # ADVANCED to its bowl week (its records are the current
                    # slate); before that the cursor is the advance step, so the
                    # guide never says "play" on a week the game is not on.
                    cursor = ("play" if str(rnd["round"]) in (tail_ready_rounds or set())
                              else "advance")
                elif not user_native:
                    cursor = "finish"
                elif gr is not None and gr.has_result and not gr.official:
                    cursor = "finish"
                else:
                    cursor = "play"
            elif is_native_round:
                # With no user game, loading pre-sims every mapped CPU game.
                # Once those results exist, the move is to advance the week,
                # not to keep loading the same dynasty in a loop.
                ready_here = str(rnd["round"]) in (tail_ready_rounds or set())
                recs = (plan or {}).get(str(rnd["round"])) or []
                live_records = [rec for game, rec in zip(games, recs)
                                if game.get("status") != "final"
                                and rec is not None and rec < len(store.games)] \
                    if store is not None else []
                cpu_done = bool(live_records) and all(
                    store.games[rec].has_result for rec in live_records)
                cursor = ("finish" if ready_here and cpu_done
                          else "load" if ready_here else "advance")
            else:
                cursor = "advance" if on_calendar else "load"
        seen_cursor = False
        for s in steps:
            if ph_state == "done":
                s["state"] = "done"
            elif ph_state == "upcoming" or cursor is None:
                s["state"] = "todo"
            elif s["id"] == cursor:
                s["state"] = "current"
                seen_cursor = True
            else:
                s["state"] = "done" if not seen_cursor else "todo"

        phases.append({
            "key": f"round-{rnd['round']}", "title": rnd.get("name") or f"Round {rnd['round']}",
            "state": ph_state,
            "progress": f"{finals} of {len(games)} recorded",
            "user_line": user_line,
            "steps": steps,
        })

    if champion:
        # The completion phase walks the SAVE back to health, in order: the
        # clean-postseason restore (skipping it can freeze the game on the
        # next advance), the cosmetic remaining bowl weeks, then the optional
        # engrave that writes the user's real playoff games onto their season
        # schedule. Presenting "continue as normal" while the restore was
        # still pending told the user to do exactly the thing that freezes
        # the engine (review finding, 2026-07-09).
        steps_c: list[dict[str, Any]] = [{
            "id": "done",
            "label": f"{champion.get('team')} wins the championship",
            "detail": "The full bracket, every matchup and score, is saved "
                      "in Playoff History below.",
            "state": "done"}]
        if restore_pending:
            steps_c.append({
                "id": "update",
                "label": "Update the dynasty file",
                "detail": "Exit to CFB 27's main menu and press Update Dynasty "
                          "File. This hands the game back its own postseason so "
                          "the remaining bowl weeks advance cleanly; skipping it "
                          "can freeze the game on the next advance.",
                "state": "current"})
            steps_c.append({
                "id": "load",
                "label": "Reload and finish the season",
                "detail": "Reload your dynasty, then play or sim the remaining "
                          "bowl weeks. Those games are cosmetic; your playoff "
                          "lives in Playoff History.",
                "state": "todo"})
        elif engrave_state == "advance":
            steps_c.append({
                "id": "advance",
                "label": "Finish the remaining bowl weeks",
                "detail": "Play or sim to the end of the postseason in CFB 27 "
                          "(these games are cosmetic). One more update afterward "
                          "puts your real playoff games on your season schedule.",
                "state": "current"})
        elif engrave_state == "ready":
            steps_c.append({
                "id": "engrave",
                "label": "Update to record your playoff run",
                "detail": "Exit to the main menu and press Update Dynasty File "
                          "once more: your real playoff matchups, sites, and "
                          "scores are written onto your team's season schedule "
                          "in place of the cosmetic results.",
                "state": "current"})
        else:
            steps_c.append({
                "id": "continue",
                "label": "Continue the dynasty as normal",
                "detail": ("Your playoff run is in Playoff History"
                           + (" and on your season schedule"
                              if engrave_state == "done" else "")
                           + ". Advance to the offseason whenever you are ready."),
                "state": "current"})
        phases.append({
            "key": "complete", "title": "Playoff complete", "state": "current",
            "steps": steps_c,
        })
    return guide


def _apply_user_fix(rec: int, user_rows: set[int]) -> dict[str, Any]:
    """The wave's SECOND write step: fill the user request row's RequestId
    in place on the CURRENT (post-lock) save, making the user's
    game playable from the dynasty hub (schedule.fill_user_pending_slot).
    A one-word patch; the world is otherwise left untouched."""
    ctx = confsetup._read_table()
    if ctx is None:
        return {"written": False, "reason": "no readable save"}
    payload = bytearray(ctx["payload"])
    report = savesched.fill_user_pending_slot(
        payload, rec, user_team_rows=user_rows)
    if not report:
        return {"written": False, "reason": "nothing to fix"}
    savesched.parse(bytes(payload))
    confsetup._backup_once(ctx["path"])
    out = container.encode(ctx["raw"], bytes(payload), saved_at=datetime.now())
    ctx["path"].write_bytes(out)
    confsetup._table_cache.clear()
    return {"written": True, "games": 0, "report": report, "save": ctx["path"].name}


def _apply_duplicate_user_request_fix(
        rec: int, user_rows: set[int]) -> dict[str, Any]:
    """Remove a second Actions entry without touching the playable game."""
    ctx = confsetup._read_table()
    if ctx is None:
        return {"written": False, "reason": "no readable save"}
    payload = bytearray(ctx["payload"])
    report = savesched.repair_duplicate_user_pending(
        payload, rec, user_team_rows=user_rows)
    if not report:
        return {"written": False, "reason": "nothing to fix"}
    savesched.parse(bytes(payload))
    confsetup._backup_once(ctx["path"])
    out = container.encode(ctx["raw"], bytes(payload), saved_at=datetime.now())
    ctx["path"].write_bytes(out)
    confsetup._table_cache.clear()
    return {"written": True, "games": 0, "report": report,
            "save": ctx["path"].name}


def _capture_native_boundary_snapshot(records: list[int]) -> bool:
    """Keep the fully staged world that CFB is about to advance from."""
    ctx = confsetup._read_table()
    if ctx is None or not records:
        return False
    payload = ctx["payload"]
    store = savesched.parse(payload)
    if not all(record < len(store.games)
               and store.games[record].scheduled for record in records):
        return False
    path = _native_boundary_snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ctx["raw"])
    return True


def _native_boundary_recovery_base(
        state: dict[str, Any], current_payload: bytes,
        current_store: savesched.GameStore, target_records: list[int],
        prior_records: set[int]) -> dict[str, Any] | None:
    """Build a safe prior-week world for a half-issued native game.

    AwayRequestId and HomeRequestId are identities backed by objects CFB
    creates at the week boundary. They cannot be transplanted from cosmetic
    bowls. Recovery therefore restores the immediately preceding week, keeps
    every already-completed game from that week, and lets the normal native
    writer stage both participants before CFB advances again.

    The dedicated boundary snapshot is authoritative for new runs. The older
    one-time save backup is a compatibility fallback for dynasties created
    before boundary snapshots existed, but only when its slate contains the
    immediately preceding custom round.
    """
    ctx = confsetup._read_table()
    if ctx is None or not target_records:
        return None
    current_slate = set(savesched.week_slate(current_payload))
    target_set = set(target_records)
    if not target_set <= current_slate:
        return None

    candidates: list[Path] = []
    for path in (_native_boundary_snapshot_path(), _snapshot_path(),
                 _restore_snapshot_path()):
        if path.exists() and path not in candidates:
            candidates.append(path)
    backup = confsetup._backup_once(ctx["path"])
    if backup is not None and backup.exists() and backup not in candidates:
        candidates.append(backup)

    for path in candidates:
        try:
            base_raw = path.read_bytes()
            base_payload = container.decode(base_raw).payload
            base_store = savesched.parse(base_payload)
            base_slate = set(savesched.week_slate(base_payload))
        except (OSError, ValueError):
            continue
        if not base_slate or target_set & base_slate:
            continue
        if prior_records and not prior_records <= base_slate:
            continue

        # Preserve the exact completed games from the prior week. This keeps
        # the user's real played result and every captured custom matchup while
        # returning only the calendar/scheduler to the boundary it must cross.
        patched = bytearray(base_payload)
        copied = []
        for record in sorted(base_slate):
            if record >= len(current_store.games) \
                    or record >= len(base_store.games):
                continue
            current_game = current_store.games[record]
            if not (current_game.official and current_game.has_result):
                continue
            data = savesched.read_record(
                current_payload, current_store, record)
            savesched.write_record(patched, base_store, record, data)
            copied.append(record)

        # The malformed current world remains available for forensic recovery;
        # never make the boundary rollback the only surviving copy.
        failed = _failed_boundary_snapshot_path()
        failed.parent.mkdir(parents=True, exist_ok=True)
        if not failed.exists():
            failed.write_bytes(ctx["raw"])

        recovery_raw = container.encode(
            base_raw, bytes(patched), saved_at=datetime.now())
        return {
            "raw": recovery_raw,
            "source": path.name,
            "slate": sorted(base_slate),
            "copied": copied,
        }
    return None


def _restore_base_to_save() -> dict[str, Any]:
    """Hand the game back its OWN clean postseason at completion.

    Cycling fills the save's bowl/CFP records with custom matchups, relabeled
    bowls, and DOUBLE-BOOKED teams (a team placed in a custom game while still
    in its engine-original bowl); the engine FREEZES trying to advance past
    that. Writing the pre-lock BASE snapshot back over the save restores the
    engine's untouched bowls and CFP exactly as it scheduled them, so the user
    can play or sim the rest of the postseason normally. The custom results are
    already archived in Playoff History; the save is knowingly returned to its
    pre-playoff arrival state (the recorded run is the app's, not the save's).
    Only valid for a pure-cycle playoff that stayed at the anchor week; a
    calendar-tail run advanced through the real weeks and is left alone.

    Prefers the ORIGINAL arrival snapshot (restore_base.sav) when one exists
    (left by the retired base rebase): it is guaranteed pristine, while a
    swapped cycle base could carry custom matchups, the very poison this
    restore cures."""
    snap = _restore_snapshot_path()
    if not snap.exists():
        snap = _snapshot_path()
    if not snap.exists():
        return {"written": False, "reason": "no base snapshot"}
    ctx = confsetup._read_table()
    if ctx is None:
        return {"written": False, "reason": "no readable save"}
    base_raw = snap.read_bytes()
    try:
        payload = container.decode(base_raw).payload
        savesched.parse(payload)  # sanity: the base must still parse
    except (OSError, ValueError):
        return {"written": False, "reason": "unreadable base snapshot"}
    confsetup._backup_once(ctx["path"])
    out = container.encode(base_raw, payload, saved_at=datetime.now())
    ctx["path"].write_bytes(out)
    confsetup._table_cache.clear()
    return {"written": True, "save": ctx["path"].name}


def _user_final_games(bracket: dict[str, Any],
                      user_names: set[str]) -> list[dict[str, Any]]:
    """The user's completed bracket games with captured scores, in round
    order (the run's chronology)."""
    out = []
    for rnd in bracket.get("rounds") or []:
        for g in rnd["games"]:
            if g.get("status") == "final" and g.get("scores") \
                    and any(s.get("team") in user_names for s in g["slots"]):
                out.append(g)
    return out


def _engrave_targets(store: savesched.GameStore,
                     user_rows: set[int]) -> list[savesched.Game]:
    """The user's OFFICIAL postseason records, chronological (request-ID
    order): the cosmetic games the engine simmed for them after the
    completion restore. These are the only slots the season's schedule page
    can show the user's playoff run on."""
    recs = [g for g in store.games
            if g.bowl_row is not None and g.official and g.has_result
            and (g.away_row in user_rows or g.home_row in user_rows)]
    recs.sort(key=lambda g: g.result_slot if g.result_slot is not None
              else 1 << 30)
    return recs


def _engrave_ready(store: savesched.GameStore, user_rows: set[int]) -> bool:
    """Whether the user has advanced past their last cosmetic postseason
    game (no scheduled, unofficial postseason record still holds them)."""
    return not any(
        g.bowl_row is not None and g.scheduled and not g.official
        and (g.away_row in user_rows or g.home_row in user_rows)
        for g in store.games)


def _engrave_user_games(bracket: dict[str, Any],
                        user_names: set[str]) -> dict[str, Any]:
    """Write the user's REAL playoff games over the cosmetic engine results
    on their own OFFICIAL postseason records.

    Runs after the completion restore and after the user has advanced through
    the remaining (cosmetic) bowl weeks, so the season's schedule page shows
    the custom run instead of the engine's throwaway sims. The save can hold
    at most as many games as the engine gave the user cosmetic postseason
    records (their bowl, or their CFP path: 1 to 4), so the LAST games of the
    run are recorded and the finale always lands on the latest record. ONLY
    records already containing the user are touched: an in-place rewrite of
    teams/venue/scores on an official record past every postseason boundary
    cannot double-book a CFP bracket slot or detach a pending game. Known
    cosmetic limit: the box score keeps the cosmetic game's stats (the save
    has no stats for games it never simmed)."""
    ctx = confsetup._read_table()
    if ctx is None:
        return {"written": False, "reason": "no readable save"}
    payload = bytearray(ctx["payload"])
    store = savesched.parse(bytes(payload))
    roster: list[saveteams.Team] = ctx["roster"]
    rows_by_name = {t.name: i for i, t in enumerate(roster)}
    name_of = {i: t.name for i, t in enumerate(roster)}
    user_rows = {rows_by_name[n] for n in user_names if n in rows_by_name}
    targets = _engrave_targets(store, user_rows)
    games = _user_final_games(bracket, user_names)
    if not targets or not games:
        return {"written": False, "reason": "nothing to engrave"}
    handles = savestadiums.stadium_table(bytes(payload))
    bowl_handles = _bowl_stadium_handles(bytes(payload))
    report: list[str] = []
    written = 0
    for g_rec, game in zip(targets, games[-len(targets):]):
        slots = game["slots"]
        if len(slots) != 2 or any(s.get("type") != "team" for s in slots):
            continue
        score_of = {s.get("team"): (game.get("scores") or [None, None])[i]
                    for i, s in enumerate(slots)}
        # prefer the orientation the wave actually wrote (the user's engine
        # side was preserved there); fall back to bracket order (slot0 hosts)
        disk = game.get("_disk") or {}
        home = disk.get("home")
        away = disk.get("away")
        if home is None or away is None:
            home = rows_by_name.get(slots[0].get("team"))
            away = rows_by_name.get(slots[1].get("team"))
        if home is None or away is None or home == away:
            continue
        hs = score_of.get(name_of.get(home))
        as_ = score_of.get(name_of.get(away))
        if hs is None or as_ is None:
            continue
        report.extend(savesched.set_matchup(payload, g_rec,
                                            away_row=away, home_row=home))
        want = disk.get("venue")
        if want is None:
            want = _desired_venue(game, handles, bowl_handles)
        if want is not None:
            report.extend(savesched.set_venue(payload, g_rec, want or None))
        report.extend(savesched.set_result_scores(payload, g_rec,
                                                  home=int(hs), away=int(as_)))
        written += 1
    if not written:
        return {"written": False, "reason": "no games engraved", "report": report}
    savesched.parse(bytes(payload))  # sanity: the store must still parse
    confsetup._backup_once(ctx["path"])
    out = container.encode(ctx["raw"], bytes(payload), saved_at=datetime.now())
    ctx["path"].write_bytes(out)
    confsetup._table_cache.clear()
    return {"written": True, "games": written, "report": report}


def _apply_to_save(bracket: dict[str, Any], plan: dict[str, list[int]],
                   *, regen_bowls: bool = True,
                   base_raw: bytes | None = None,
                   user_rows: set[int] | None = None,
                   dry_run: bool = False,
                   pristine: bool = False,
                   rank_swap: dict[str, Any] | None = None,
                   result_flips: list[dict[str, Any]] | None = None,
                   user_freeze: dict[str, Any] | None = None,
                   only_rounds: set[str] | None = None,
                   keep_records: set[int] | None = None,
                   neutralize: set[int] | None = None,
                   blank_records: set[int] | None = None,
                   bowl_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Push every decided, not-yet-official matchup into the save file.

    With `base_raw`, the patch is applied to THAT container (the base-week
    snapshot) instead of the file's current content, and the result replaces
    the save file: this is the WAVE WRITE, rolling the whole dynasty back to
    the (pre-lock) base week with the wave's matchups in place so the engine
    locks them itself on load (`pristine`; see _write_round)."""
    ctx = confsetup._read_table()
    if ctx is None:
        return {"written": False, "reason": "no readable save"}
    if base_raw is not None:
        ctx = dict(ctx, raw=base_raw, payload=container.decode(base_raw).payload)
    payload = bytearray(ctx["payload"])
    store = savesched.parse(bytes(payload))
    roster: list[saveteams.Team] = ctx["roster"]
    rows_by_name = {t.name: i for i, t in enumerate(roster)}
    handles = savestadiums.stadium_table(bytes(payload))
    bowl_handles = _bowl_stadium_handles(bytes(payload))
    try:
        btable0 = savebowls.parse(bytes(payload))
        cfp_round_rows = _cfp_round_rows(btable0)
        ny6_handles = {pb.stadium_handle
                       for pb in btable0.playoff_bowls if pb.stadium_handle}
    except Exception:
        cfp_round_rows, ny6_handles = {}, set()
    report: list[str] = []
    # Plain-neutral presentation overrides are intentionally temporary. Once
    # the user's game is final, restore the team's real home stadium and the
    # CFP BowlGame identity's native stadium before staging the next round.
    # Legacy field-recipe overrides are restored here too.
    presentation_restores = 0
    for old_round in bracket.get("rounds") or []:
        for old_game in old_round.get("games") or []:
            if old_game.get("status") != "final":
                continue
            old_disk = old_game.get("_disk") or {}
            team_spec = old_disk.get("team_stadium") or {}
            team_row = team_spec.get("team")
            selected = team_spec.get("selected")
            original = team_spec.get("original")
            if team_row is not None and selected and original is not None:
                try:
                    current = savestadiums.team_home_handle(
                        bytes(payload), int(team_row))
                    if current == selected and savestadiums.set_team_home_handle(
                            payload, int(team_row), int(original)):
                        report.append(
                            f"team {team_row}: restored its home stadium after "
                            "the completed playoff game")
                        presentation_restores += 1
                except (IndexError, ValueError):
                    pass

            bowl_spec = old_disk.get("bowl_stadium") or {}
            bowl_row = bowl_spec.get("row")
            bowl_selected = bowl_spec.get("selected")
            bowl_original = bowl_spec.get("original")
            if bowl_row is not None and bowl_original is not None:
                try:
                    restore_table = savebowls.parse(bytes(payload))
                    restore_bowl = restore_table.by_row(int(bowl_row))
                    if restore_bowl is not None \
                            and restore_bowl.stadium_handle == (bowl_selected or 0) \
                            and savebowls.set_stadium_handle(
                                payload, restore_bowl, int(bowl_original)):
                        report.append(
                            f"bowl identity {bowl_row}: restored its native "
                            "stadium after the completed playoff game")
                        presentation_restores += 1
                except (ValueError, TypeError):
                    pass

            spec = old_disk.get("field_recipe") or {}
            stadium_index = spec.get("stadium")
            recipe = spec.get("name")
            if stadium_index is None or not recipe:
                continue
            try:
                current = savestadiums.field_recipe_name(
                    bytes(payload), int(stadium_index))
                if current == recipe and savestadiums.set_field_recipe(
                        payload, int(stadium_index), spec.get("original") or ""):
                    report.append(
                        f"stadium {stadium_index}: restored its field recipe "
                        "after the completed playoff game")
                    presentation_restores += 1
            except (IndexError, UnicodeError, ValueError):
                continue
    records: list[int] = []
    round_of_record: dict[int, dict[str, Any]] = {}
    for rnd in bracket.get("rounds") or []:
        if only_rounds is not None and str(rnd["round"]) not in only_rounds:
            continue
        recs = plan.get(str(rnd["round"])) or []
        written = _write_round(payload, store, rnd, recs, rows_by_name, handles,
                               report, pristine=pristine, user_rows=user_rows,
                               bowl_handles=bowl_handles,
                               cfp_rows=cfp_round_rows, ny6=ny6_handles)
        records.extend(written)
        for rec in written:
            round_of_record[rec] = rnd
        # Identity swaps may use any custom-mapped game in this write as the
        # partner, including one whose teams already happened to match and did
        # not need a SeasonGame rewrite.
        for game, rec in zip(rnd["games"], recs):
            if rec is not None and game.get("status") != "final":
                round_of_record[rec] = rnd
    total = len(records) + presentation_restores
    # NEUTRALIZE the engine's leftover playoff pairings (native mode): a
    # ready round's stock record that no custom game claimed still holds the
    # matchup the engine's own bracket built there. Left alone it double-
    # books teams that play a custom game elsewhere this week (a frozen
    # engine on advance), so it is refilled with an FCS placeholder pairing,
    # a plainly-junk sim game no real team is booked into.
    if neutralize:
        fcs_rows = [i for i, t in enumerate(roster)
                    if (t.name or "").upper().startswith("FCS ")]
        if len(fcs_rows) >= 2:
            fresh_n = savesched.parse(bytes(payload))
            for ni, rec in enumerate(sorted(neutralize)):
                if rec >= len(fresh_n.games):
                    continue
                # rotate through the placeholder rows so no FCS row is
                # double-booked within one week's records
                pair = (fcs_rows[(2 * ni) % len(fcs_rows)],
                        fcs_rows[(2 * ni + 1) % len(fcs_rows)])
                g_n = fresh_n.games[rec]
                if g_n.official or (g_n.away_row, g_n.home_row) == pair:
                    continue
                if g_n.has_result or g_n.presimmed:
                    report.extend(
                        savesched.clear_engine_state(payload, g_n) if pristine
                        else savesched.reset_locked_matchup_status(payload, g_n))
                report.extend(savesched.set_matchup(
                    payload, g_n, away_row=pair[0], home_row=pair[1]))
                report.append(f"game {rec}: engine's leftover playoff pairing "
                              "neutralized (FCS filler)")
                total += 1
    # BLANK future-round stock records the engine pre-filled with a field
    # team (native mode): the engine pencils its top seeds into their bye
    # rounds (e.g. the top 4 sit in the quarterfinal records at bowl week 1
    # arrival), but those teams play EARLIER in the custom bracket, so a team
    # would be booked in both its custom game and the engine's future record
    # (a freeze on advance). Clearing them to TBD holds until the engine
    # rebuilds that round at its own boundary, where the app then writes the
    # custom matchup over it. Only records NOT hosting a game this write.
    if blank_records:
        fresh_b = savesched.parse(bytes(payload))
        for rec in sorted(blank_records):
            if rec >= len(fresh_b.games):
                continue
            g_b = fresh_b.games[rec]
            if g_b.official or not (g_b.away_row is not None
                                    or g_b.home_row is not None):
                continue
            if g_b.has_result or g_b.presimmed:
                report.extend(savesched.clear_engine_state(payload, g_b))
            report.extend(savesched.set_matchup(payload, g_b,
                                                away_row=None, home_row=None))
            report.append(f"game {rec}: engine's pre-penciled bye seed cleared "
                          "to TBD (plays earlier in the custom bracket)")
            total += 1
    # Only teams playing in the rounds staged by THIS write must be removed
    # from ordinary bowls. At a 96-team hybrid handoff, using all 96 original
    # seeds exhausted the substitute bench and wrote partial Bowl Week 1
    # requests. The final-16 handoff needs to protect only its 16 survivors.
    field_names = {s.get("team") for s in bracket.get("seeds") or []
                   if s.get("team")}
    active_names = {
        slot.get("team")
        for rnd in bracket.get("rounds") or []
        if only_rounds is None or str(rnd["round"]) in only_rounds
        for game, rec in zip(rnd["games"], plan.get(str(rnd["round"])) or [])
        if rec is not None and game.get("status") != "final"
        for slot in game.get("slots") or []
        if slot.get("team")
    }
    if regen_bowls and active_names:
        total += _regenerate_bowls(payload, store, roster, active_names, report,
                                   keep_records=keep_records)
    # A capture-only probe must include the separate bowl editor's frozen plan
    # when deciding whether the Update Dynasty File action is needed. The real
    # write reasserts it later, after every playoff presentation and user-route
    # patch, so the bowl schedule is the final authority on nonplayoff records.
    if dry_run and regen_bowls and bowl_state:
        from . import bowl_editor
        bowl_ctx = {**bowl_state, "bracket": bracket, "plan": plan}
        bowl_probe = bowl_editor.apply_during_playoff(
            payload, roster, bowl_ctx, report, dry_run=True)
        total += int(bowl_probe.get("changed") or 0)
    if dry_run:
        # probe only: report whether an apply would change the save
        return {"written": False, "would_write": total > 0, "games": total,
                "report": report}
    # FIELD BRANDING for the user's game: the field art keys off the bowl
    # IDENTITY (the +16 BowlGame ref), not the display name, so the user's
    # first-round game rendered its original bowl's branding (Armed Forces
    # Bowl, observed in-game). The identity must also AGREE with the game's
    # venue: a CFP-round identity has no field art away from its native
    # venues and renders a blank orange field (observed in-game, 2026-07-09,
    # neutral- and bowl-sited games). The unused Generic Bowl identity also has
    # no field art (SMU versus South Carolina, 2026-07-14). An ordinary neutral
    # user game therefore uses the game's native home-playoff shape: both the
    # SeasonGame and its CFP BowlGame identity have zero stadium overrides,
    # while HomeTeam.Stadium temporarily points at the selected physical venue.
    # This preserves the venue model but enters through the same field path as
    # a stock CFP campus game. A named bowl keeps its own identity, stadium,
    # field, and presentation. When the desired CFP identity belongs to
    # another wave record, pristine writes swap the identities so no duplicate
    # can freeze the engine.
    if user_rows:
        fresh0 = savesched.parse(bytes(payload))
        user_rec0 = next((r for r in round_of_record
                          if r < len(fresh0.games)
                          and (fresh0.games[r].away_row in user_rows
                               or fresh0.games[r].home_row in user_rows)), None)
        rnds = bracket.get("rounds") or []
        rnd0 = round_of_record.get(user_rec0) if user_rec0 is not None else None
        if rnd0 is not None and rnd0 in rnds:
            kind = _ROUND_KINDS[min(len(rnds) - 1 - rnds.index(rnd0), 3)]
            btable = savebowls.parse(bytes(payload))
            kind_rows = [r for r, k in _cfp_round_rows(btable).items()
                         if k == kind]
            # the venue this wave actually gave the user's game (falling back
            # to what the record itself carries): the identity follows it
            recs0 = plan.get(str(rnd0["round"])) or []
            ugame = next((g for g, r in zip(rnd0["games"], recs0)
                          if r == user_rec0), None)
            site0 = (ugame or {}).get("site") or {}
            venue0 = ((ugame or {}).get("_disk") or {}).get("venue")
            if venue0 is None and ugame is not None:
                venue0 = _desired_venue(ugame, handles, bowl_handles)
            if venue0 is None:
                venue0 = fresh0.games[user_rec0].venue_uid or 0
            cur_row = fresh0.games[user_rec0].bowl_row
            home_team_field = _use_home_team_field(
                ugame or {},
                (fresh0.games[user_rec0].away_row
                 if fresh0.games[user_rec0].away_row is not None else -1),
                (fresh0.games[user_rec0].home_row
                 if fresh0.games[user_rec0].home_row is not None else -1),
                user_rows)
            desired = _brand_rows(btable, kind_rows, kind, site0, venue0,
                                  ny6_handles)
            branded_row = cur_row
            if pristine and desired and cur_row not in desired:
                # NEVER duplicate a bowl identity owned by a record the engine
                # keeps (one NOT written this wave). Taking a row that the
                # engine's own bracket already uses gives two records the same
                # slot and FREEZES the game on the next advance (observed: a
                # bowl team's Armed Forces Bowl repointed to CFP first-round
                # row 7, colliding with engine rec 924). Only repoint onto a
                # row a CUSTOM-mapped record owns (a safe swap) or one no
                # record uses at all; otherwise leave the user's bowl identity
                # alone (their field art is cosmetic, a freeze is not).
                used = {fresh0.games[r].bowl_row for r in range(len(fresh0.games))
                        if fresh0.games[r].bowl_row is not None}
                owners = {fresh0.games[r].bowl_row: r for r in round_of_record
                          if r != user_rec0 and r < len(fresh0.games)}
                target = next((row for row in desired if row in owners),
                              next((row for row in desired if row not in used), None))
                if target is not None:
                    partner = owners.get(target)
                    report.extend(savesched.set_bowl_ref(
                        payload, fresh0.games[user_rec0], target))
                    if partner is not None:
                        report.extend(savesched.set_bowl_ref(
                            payload, fresh0.games[partner], cur_row))
                    tb = btable.by_row(target)
                    report.append(f"game {user_rec0}: field branding -> "
                                  f"{(tb.name if tb else str(target))!r} "
                                  f"({kind.replace('_', ' ')})")
                    branded_row = target
            if home_team_field and branded_row in kind_rows:
                branded = btable.by_row(branded_row)
                if branded is not None:
                    disk0 = (ugame or {}).setdefault("_disk", {})
                    # Every stock CFP BowlGame row has no fixed stadium. Its
                    # SeasonGame carries NY6/title venues when applicable.
                    # Format 20 may have left a custom handle here, so the
                    # authoritative original is zero rather than that legacy
                    # value observed during migration.
                    original_bowl = 0
                    disk0["bowl_stadium"] = {
                        "row": branded_row,
                        "selected": 0,
                        "original": original_bowl,
                    }
                    if savebowls.set_stadium_handle(payload, branded, None):
                        report.append(
                            f"game {user_rec0}: CFP presentation uses the "
                            "native home-playoff field path")
            if home_team_field and ugame is not None:
                ugame.setdefault("_disk", {})["bowl_row"] = branded_row
    # relabel every bowl record hosting a playoff game this wave so the
    # game's schedule shows the round ("CFP First Round", "CFP Second Round",
    # ...) instead of the leftover bowl name ("Frisco Bowl"). Covers ALL
    # mapped unfinished games, including ones whose matchup did not need a
    # rewrite (an engine pairing that coincided with the bracket's), so no
    # wave game ever shows the wrong name. Stock CFP records already carry
    # their label; set_display_name is a no-op then.
    for rnd in bracket.get("rounds") or []:
        if only_rounds is not None and str(rnd["round"]) not in only_rounds:
            continue
        recs = plan.get(str(rnd["round"])) or []
        for gi, game in enumerate(rnd["games"]):
            rec = recs[gi] if gi < len(recs) else None
            if rec is not None and game.get("status") != "final":
                round_of_record[rec] = rnd
    btable = savebowls.parse(bytes(payload))
    fresh_rows = savesched.parse(bytes(payload))  # bowl refs may have moved
    for rec, rnd in round_of_record.items():
        bowl_row = fresh_rows.games[rec].bowl_row if rec < len(fresh_rows.games) else None
        bowl = btable.by_row(bowl_row) if bowl_row is not None else None
        if bowl and savebowls.set_display_name(payload, bowl, _round_label(rnd["name"])):
            report.append(f"game {rec}: relabeled {bowl.name!r} -> {_round_label(rnd['name'])!r}")
    # The engine's OWN pairing for the user (its bracket/bowl matchup) is
    # never BLANKED: nulling the teams of the user's own scheduled game
    # crashed the game on load (Missouri run, 2026-07-08; the engine keeps
    # its own references to the user's next game). Once a custom user game is
    # staged, however, leaving the user in that old record is not cosmetic:
    # CFB 27 can keep the original bowl/CFP game as the program's postseason
    # destination and show the correctly marked custom game as a bye (USC,
    # 96-team run, 2026-07-14). The safe shape is a scheduled throwaway: keep
    # the old record and its opponent, but replace only the user's side with
    # an unused non-field placeholder, preferring FBS because FCS inside a CFP
    # record crashes the game. The engine's references
    # still point at a valid two-team game, while the user exists in exactly
    # one postseason record, the custom one.
    #
    # THE USER MARK (pre-lock worlds only): the lock pre-sims every queued
    # game whose request pair is CPU-typed, even one holding the user's team
    # (the user then reads as on a bye and their game is decided by the sim),
    # so the record hosting the user's wave game must be marked in the queue
    # and any stale user marking downgraded. Left alone when the user is not
    # in the custom field (their engine-scheduled game keeps its own mark).
    if pristine and user_rows is not None:
        fresh = savesched.parse(bytes(payload))
        user_rec = None
        for rec in round_of_record:
            g = fresh.games[rec]
            if g.away_row in user_rows or g.home_row in user_rows:
                user_rec = rec
                break
        if user_rec is None and user_rows:
            # BYE ROUND: no custom game maps to the user this wave, but their
            # engine game record is in the anchor slate. Keep the user there
            # but replace the opponent with an unused, non-field FBS program,
            # so it is a game to sim and no real playoff team is double-booked.
            # Never put FCS in a native CFP record: that exact shape crashed a
            # fresh Penn State dynasty on load. This is not a bracket game and
            # its result is ignored.
            slate = set(savesched.week_slate(bytes(payload)))
            field_names = {s.get("team") for s in bracket.get("seeds") or []}
            user_slate_rec = next(
                (g.index for g in fresh.games
                 if g.index in slate and g.bowl_row is not None and not g.official
                 and (g.away_row in user_rows or g.home_row in user_rows)), None)
            used = {row for game in fresh.games if game.bowl_row is not None
                    for row in (game.away_row, game.home_row)
                    if row is not None}
            filler = _throwaway_row(
                roster, field_names, used_rows=used, avoid_rows=user_rows)
            if user_slate_rec is not None and filler is not None:
                g = fresh.games[user_slate_rec]
                opp_side = "away" if g.home_row in user_rows else "home"
                report.extend(savesched.set_matchup(
                    payload, g, **{f"{opp_side}_row": filler}))
                report.append(
                    f"game {user_slate_rec}: non-field FBS throwaway (bye round)")
                user_rec = user_slate_rec
        if user_rec is not None and user_rows:
            # Remove every OTHER unofficial postseason occurrence of the
            # user. Prefer unused FBS rows, with FCS only as a last resort for
            # ordinary-bowl saves that expose no free FBS program.
            fresh = savesched.parse(bytes(payload))
            field_rows = {rows_by_name[name] for name in field_names
                          if name in rows_by_name}
            used = {row for g in fresh.games if g.bowl_row is not None
                    for row in (g.away_row, g.home_row) if row is not None}
            fcs = [i for i, team in enumerate(roster)
                   if (team.name or "").upper().startswith("FCS ")
                   and i not in field_rows and i not in user_rows]
            fbs = [i for i, team in enumerate(roster)
                   if i not in field_rows and i not in user_rows
                   and (team.name or "")
                   and not (team.name or "").upper().startswith("FCS ")]
            fillers = ([row for row in fbs if row not in used]
                       + [row for row in fcs if row not in used])
            fallback = fbs + fcs
            protected = set(round_of_record)
            for stale in fresh.games:
                if stale.index == user_rec or stale.index in protected \
                        or stale.bowl_row is None or stale.official \
                        or not ({stale.away_row, stale.home_row} & user_rows):
                    continue
                other = (stale.home_row if stale.away_row in user_rows
                         else stale.away_row)
                replacement = next((row for row in fillers if row != other),
                                   next((row for row in fallback
                                         if row != other), None))
                if replacement is None:
                    report.append(
                        f"game {stale.index}: stale user postseason game "
                        "could not be suppressed (no substitute team)")
                    continue
                if replacement in fillers:
                    fillers.remove(replacement)
                if stale.has_result or stale.presimmed:
                    report.extend(savesched.clear_engine_state(payload, stale))
                side = ("away_row" if stale.away_row in user_rows else
                        "home_row")
                report.extend(savesched.set_matchup(
                    payload, stale, **{side: replacement}))
                report.append(
                    f"game {stale.index}: stale engine postseason placement "
                    "replaced with a substitute throwaway")
                total += 1
        report.extend(savesched.set_user_pending(
            payload, user_rec, user_team_rows=user_rows))
    # restore the REAL committee ranking in the written world (the base
    # carries the championship-week prepare swap; the engine's selection is
    # done, so in-game polls can read true again)
    if pristine and rank_swap:
        cur = {t.row: t.rank for t in savepolls.parse(bytes(payload))}
        u, o = rank_swap.get("user_row"), rank_swap.get("other_row")
        if u is not None and o is not None \
                and cur.get(u) == rank_swap.get("other_rank") \
                and cur.get(o) == rank_swap.get("user_rank"):
            report.extend(savepolls.swap_committee_rank(payload, u, o))
            report.append("real committee ranking restored in the written save")
    # restore the REAL season results the championship-week prepare flipped
    # (the base carries the flips forever; the boundary is done with them,
    # so every written world reads the true season again)
    if pristine and result_flips:
        fresh2 = savesched.parse(bytes(payload))
        for flip in result_flips:
            idx = flip.get("game")
            if idx is None or idx >= len(fresh2.games):
                continue
            g = fresh2.games[idx]
            if (g.home_score, g.away_score) == (flip.get("away"), flip.get("home")):
                report.extend(savesched.set_result_scores(
                    payload, g, home=flip["home"], away=flip["away"]))
    # PIN the user's own played game: after the world is rewound to the base,
    # graft the exact bytes the engine wrote when the user played their final
    # game back onto its record, so their real matchup and score stay on their
    # schedule (marked final) instead of the base's leftover pairing. Done only
    # for a finished user (eliminated/champion); the record is out of the wave
    # pool, so no CPU game contends for it. Verbatim real bytes keep the result
    # request IDs valid (they are the record's own, stable across rewinds).
    if pristine and user_freeze:
        fresh3 = savesched.parse(bytes(payload))
        rec = user_freeze.get("record")
        data = bytes.fromhex(user_freeze.get("hex") or "")
        if (rec is not None and rec < len(fresh3.games)
                and len(data) == savesched.RECORD_SIZE):
            report.extend(savesched.write_record(payload, fresh3, rec, data))
    bowl_result: dict[str, Any] | None = None
    if regen_bowls and bowl_state:
        from . import bowl_editor
        bowl_ctx = {**bowl_state, "bracket": bracket, "plan": plan}
        bowl_result = bowl_editor.apply_during_playoff(
            payload, roster, bowl_ctx, report, dry_run=False)
        total += int(bowl_result.get("changed") or 0)
    if not total and base_raw is None:
        return {"written": False, "reason": "nothing to write", "report": report}
    # verify the patch still parses before touching disk
    savesched.parse(bytes(payload))
    confsetup._backup_once(ctx["path"])
    out = container.encode(ctx["raw"], bytes(payload), saved_at=datetime.now())
    ctx["path"].write_bytes(out)
    confsetup._table_cache.clear()
    if bowl_result and bowl_result.get("assignments"):
        from . import bowl_editor
        bowl_editor.persist_generated(int(bowl_state.get("year") or 0), bowl_result)
    return {"written": True, "games": total, "records": records, "report": report,
            "save": ctx["path"].name}


# ---------------------------------------------------------------------------
# the sync entry point
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# background autosync (the "mod running in the background" loop)
# ---------------------------------------------------------------------------
# A watchdog observer over the CFB 27 saves folder. Whenever the game writes
# a save (it autosaves at every week advance), the live bracket re-syncs and
# pushes any newly-decided custom-playoff matchups back into the save, so by
# the time the user looks at the new week the game already carries the custom
# bracket. The UI's
# /api/playoff/live polling is the fallback when watchdog is unavailable.

_autosync: dict[str, Any] = {"observer": None, "last": None}


def _on_saves_changed(changed_path: str | None = None,
                      *, recruiting_done: bool = False,
                      wait: bool = False) -> None:
    # The master auto-sync switch (per app, set from the header toggle). When
    # off, a new game save triggers NO automatic bracket write or poll push:
    # the user drives everything by hand via the Sync / apply buttons. This is
    # the escape hatch for editing custom rankings without the watcher
    # re-asserting under them.
    from . import app_settings
    if not app_settings.autosync_enabled():
        return

    # An explicit Scan performs recruiting synchronously.  Mark the rest of
    # the shared tool chain before returning its response so the frontend cannot
    # resume its scan in the small window before this thread starts.
    from . import recruiting_fix
    recruiting_enabled = recruiting_fix.is_enabled()
    if recruiting_done and recruiting_enabled:
        recruiting_fix.mark_shared_tools()

    def _run() -> None:
        try:
            # Recruiting is the first save mutation in the weekly chain.  The
            # The frontend will not resume its save scan until
            # this phase finishes, and a write holds on reload_required.
            if not recruiting_done and recruiting_enabled:
                recruiting_fix.auto_apply(changed_path)
        except Exception:  # noqa: BLE001 - the watcher must survive anything
            pass
        if not recruiting_done and recruiting_enabled:
            recruiting_fix.mark_shared_tools()
        try:
            # capture-only: the watcher records results and advances the
            # bracket the moment a new autosave lands; WRITES happen only
            # through the explicit apply (the "update dynasty file" button),
            # so the save never changes underneath a running game session.
            out = sync(write=False)
            _autosync["last"] = {
                "at": datetime.now().isoformat(timespec="seconds"),
                "status": out.get("status"),
                "save_written": bool(out.get("save_written")),
            }
        except Exception:  # noqa: BLE001 - the watcher must survive anything
            pass
        try:
            # the poll editor's auto-push (backend/polledit.py): unlike the
            # bracket, a user-owned poll IS written the moment a new save
            # lands; a write the running game later clobbers from memory is
            # simply re-applied on its next autosave, so the file on disk
            # converges to the user's ranking (lazy import: polledit imports
            # this module for the shared save-write lock)
            from . import polledit
            res = polledit.auto_apply()
            if res is not None and isinstance(_autosync.get("last"), dict):
                _autosync["last"]["polls_written"] = [
                    p for p, c in (res.get("changed") or {}).items() if c]
        except Exception:  # noqa: BLE001 - the watcher must survive anything
            pass
        finally:
            if recruiting_enabled:
                recruiting_fix.finish_shared_tools()
    if wait:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()


class _SavesHandler:
    """Trailing debounce handler for any DYNASTY file change."""

    def __init__(self, fire, debounce: float = 3.0):
        self._fire = fire
        self._debounce = debounce
        self._timer = None
        self._lock = threading.Lock()

    def dispatch(self, event) -> None:  # noqa: ANN001 - watchdog event
        path = getattr(event, "dest_path", "") or getattr(event, "src_path", "")
        if "DYNASTY-" not in Path(path).name.upper():
            return
        from . import app_settings, recruiting_fix
        if not app_settings.autosync_enabled():
            return
        # Recruiting progress only applies when this dynasty explicitly opted
        # in. With the tool off, the other editor syncs continue silently and
        # never show a recruiting modal or delay the initial setup flow.
        if recruiting_fix.is_enabled():
            # A Dynasty+ write causes its own filesystem event. Keep the reload
            # gate sticky until the user confirms CFB 27 loaded the patched file.
            if recruiting_fix.automation_status().get("reload_required"):
                return
            recruiting_fix.mark_detected(path)
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._fire, args=(path,))
            self._timer.daemon = True
            self._timer.start()


def start_autosync() -> bool:
    """Start watching the saves folder (idempotent). False when watchdog is
    unavailable or the folder does not exist."""
    if _autosync["observer"] is not None:
        return True
    try:
        from watchdog.observers import Observer
    except Exception:  # pragma: no cover
        return False
    from .saveparse import cfb27
    folder = cfb27.saves_dir()
    if not folder.is_dir():
        return False
    obs = Observer()
    obs.schedule(_SavesHandler(_on_saves_changed), str(folder), recursive=False)
    obs.daemon = True
    obs.start()
    _autosync["observer"] = obs
    return True


def autosync_info() -> dict[str, Any]:
    return {"active": _autosync["observer"] is not None, "last": _autosync["last"]}


@contextmanager
def _cross_process_lock():
    """Exclusive lock around the sync's read-modify-write of the live state.

    Multiple Tools processes can watch the same dynasty: their
    concurrent live.json read-modify-writes were observed eating state keys
    (wave_format vanished mid-run, 2026-07-08). Windows uses msvcrt region
    locking (fcntl elsewhere); the in-process _lock still guards threads."""
    path = dynasty_paths.sub("playoff") / "sync.lock"
    fh = open(path, "a+")
    locked = False
    try:
        try:
            import msvcrt
            fh.seek(0)
            for _ in range(150):  # msvcrt gives up quickly; wait up to ~30s
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                    break
                except OSError:
                    time.sleep(0.2)
        except ImportError:  # pragma: no cover - POSIX
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
            locked = True
        yield
    finally:
        try:
            if locked:
                try:
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except ImportError:  # pragma: no cover - POSIX
                    import fcntl
                    fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()


def _native_playoff_status() -> dict[str, Any]:
    """The live payload when the custom playoff automation is OFF (the default).

    CFB 27 runs its own native 12-team playoff, so this path writes NOTHING:
    no matchups, no rewinds, and no `needs_write` "update dynasty file" prompt,
    whatever `write` the caller passed. The UI collapses the postseason pages
    to the off-state switch, so no bracket is built either; the poll and the
    saves watcher hit this every few seconds and it must stay cheap (no save
    read, no dynasty load). Conference alignment and custom poll rankings reach
    the game through their own write paths, so they still shape the native
    bracket's seeding."""
    return {
        "available": True,
        "enabled": False,
        "status": "native",
        "in_game": True,
        "needs_write": False,
        "awaiting_reload": False,
        "save_written": False,
        "bracket": None,
        "guide": None,
        "notes": [
            "The custom playoff bracket is off, so CFB 27 runs its own native "
            "12-team playoff and Dynasty+ leaves the bracket alone.",
            "Your conference alignment and custom poll rankings still apply, so "
            "the game seeds its playoff from them.",
        ],
    }


def sync(*, write: bool = True) -> dict[str, Any]:
    """Recompute the live bracket from the current save; write matchups when
    the season has reached selection and the format fits in-game. Returns the
    full live payload for the UI."""
    # Capture the active dynasty ONCE. Scan/select updates the registry outside
    # this module's lock; resolving paths dynamically inside a long sync once
    # let an `_unscanned` 124-team bracket land in a newly selected 64-team
    # dynasty after the pointer changed mid-call. The context binding also
    # keeps confsetup/pipeline save reads on this same identity.
    active_id = dynasty_paths.current_id()
    with dynasty_paths.bind_current(active_id):
        with _lock, _cross_process_lock():
            # OFF (default): never touch the bracket; the game owns its native
            # playoff. Short-circuits before any write path so a manual apply is
            # a strict no-op too, exactly like the recruiting tool when off.
            if not is_enabled():
                return _native_playoff_status()
            return _sync_locked(write=write)


def _sync_locked(*, write: bool) -> dict[str, Any]:
    payload = confsetup.current_payload()
    # ALWAYS the save's own current week: the app pointer only advances on
    # Scan/select, so reading through it at the CCG -> bowl-week boundary
    # served an ARCHIVED pre-championship snapshot and the field froze with
    # stale rankings, stale records, and projected (best-ranked) conference
    # champions instead of the real CCG winners.
    dynasty = pipeline.load_live_dynasty()
    fmt = playoff.get_format()
    if payload is None:
        # no real save (mock/dev): projection only
        try:
            bracket = playoff.build_bracket(dynasty, fmt)
        except playoff.BracketError as exc:
            return {"available": False, "status": "invalid", "problems": [str(exc)]}
        return {"available": True, "status": "projected", "bracket": bracket,
                "in_game": False, "notes": ["No CFB 27 save is readable; this is a projection."],
                "guide": _build_guide(status="projected", mode=None, bracket=None,
                                      plan=None, store=None, user_names=set(),
                                      needs_write=False, awaiting_reload=False,
                                      slate_len=None)}

    from .saveparse import results as saveresults
    store = savesched.parse(payload)
    roster = saveteams.parse_teams(payload)
    ccgs = saveresults.conference_championships(store)
    # THE POSTSEASON must actually have ARRIVED for a freeze to make sense:
    # only from bowl week 1 on does the current week slate carry bowl-tagged
    # records (a regular-season slate is plain game records). Official CCGs
    # in the store are the primary signal, but they are a heuristic over an
    # engine-owned layout; this slate check is a second, independent signal
    # (defensive, 2026-07-09) so a CCG misread mid-season can never freeze a
    # field and let a wave write overwrite the live regular season.
    postseason_here = any(
        r < len(store.games) and store.games[r].bowl_row is not None
        for r in savesched.week_slate(payload))
    season_year = (dynasty.get("season") or {}).get("year")
    active_id = dynasty_paths.current_id()

    state = _load_state()
    # Defense in depth for a registry-pointer race. ``sync`` now binds every
    # path for the whole operation, and new live states also record the
    # identity they belong to. If a state file is ever copied or redirected
    # across dynasties, never let its frozen seeds and results become history
    # in the other save.
    persisted_id = state.get("dynasty_id")
    if persisted_id is not None and persisted_id != active_id:
        state = {"year": season_year, "status": "projected",
                 "dynasty_id": active_id}
        _snapshot_path().unlink(missing_ok=True)
        _restore_snapshot_path().unlink(missing_ok=True)
        _native_boundary_snapshot_path().unlink(missing_ok=True)
        _failed_boundary_snapshot_path().unlink(missing_ok=True)
    if state.get("year") != season_year:
        state = {"year": season_year, "status": "projected",
                 "dynasty_id": active_id}
        _snapshot_path().unlink(missing_ok=True)
        _restore_snapshot_path().unlink(missing_ok=True)
        _native_boundary_snapshot_path().unlink(missing_ok=True)
        _failed_boundary_snapshot_path().unlink(missing_ok=True)
    else:
        state["dynasty_id"] = active_id

    # CFB clears the week queue immediately after the championship advance.
    # Detect the official mapped title result before the stale-state and
    # projection gates inspect that now-empty queue, so the final sync can
    # capture the champion and archive the completed bracket.
    terminal_result_waiting = (
        not postseason_here
        and _terminal_result_waiting(state, store, roster)
    )

    # Self-heal: a frozen field only makes sense once the conference
    # championships are actually official. If the state says selected/later
    # but no CCGs have been played (e.g. a field frozen prematurely by an
    # older build, or the user rolled a save back), drop back to projection
    # so the live bracket tracks the current standings again instead of
    # serving a stale frozen bracket forever. A single ccgs=0 reading is NOT
    # trusted: a transient misread (a save mid-write, a registry refresh
    # during scan) once reset a staged mid-cycle state and deleted its base
    # snapshot (observed 2026-07-08); the reset now needs three consecutive
    # misses and never deletes the snapshot (only the season change does).
    stale_frozen = (
        (state.get("status") in ("selected", "in_progress")
         and not ccgs and not terminal_result_waiting)
        # a frozen field while the slate is still the REGULAR season means
        # the freeze misfired or the save was rolled back (a complete state
        # at the offseason's empty slate is legitimate, so "complete" is
        # exempt from this check)
        or (state.get("status") in ("selected", "in_progress")
            and not postseason_here and not terminal_result_waiting))
    if stale_frozen:
        misses = int(state.get("ccgs_missing") or 0) + 1
        if misses >= 3:
            # keep the prepare bookkeeping through a same-season reset, or
            # the flipped results would never be restored
            state = {"year": season_year, "status": "projected",
                     "dynasty_id": active_id,
                     "rank_swap": state.get("rank_swap"),
                     "result_flips": state.get("result_flips")}
        else:
            state["ccgs_missing"] = misses
            _save_state(state)
            return {"available": True, "status": state.get("status"),
                    "bracket": state.get("bracket"),
                    "in_game": bool(state.get("in_game")),
                    "mode": state.get("mode"),
                    "awaiting_reload": bool(state.get("awaiting_reload")),
                    "needs_write": False,
                    "notes": ["The save reads as mid-season right now; if this "
                              "persists the playoff state resets to a projection."],
                    "guide": _build_guide(
                        status=state.get("status"), mode=state.get("mode"),
                        bracket=state.get("bracket"), plan=state.get("plan"),
                        store=store, user_names=set(),
                        needs_write=False,
                        awaiting_reload=bool(state.get("awaiting_reload")),
                        slate_len=len(state.get("slate_records") or []) or None)}
    elif state.get("ccgs_missing"):
        state.pop("ccgs_missing", None)

    # THE FREEZE GATE: the field is frozen (and the cycle anchored) only once
    # the user has ADVANCED PAST conference-championship week into bowl week.
    # A single official CCG (the user playing and winning their own CCG while
    # still AT ccg week) must NOT trigger it: the other CCGs are not final,
    # and the current slate still holds CCG records, so an anchor here would
    # snapshot the wrong week (observed: Miami froze the instant its CCG went
    # official, mis-anchored the bye as a later-week game, and stuck). While
    # `at_ccg`, stay in projection/prepare regardless of a partial CCG count.
    at_ccg = _ccg_week(payload, store)
    if at_ccg and state.get("status") in ("selected", "in_progress"):
        # a premature freeze (older build, or a save rolled back to CCG week):
        # undo it and re-project so the anchor is taken at bowl week instead
        _snapshot_path().unlink(missing_ok=True)
        _restore_snapshot_path().unlink(missing_ok=True)
        _native_boundary_snapshot_path().unlink(missing_ok=True)
        state = {"year": season_year, "status": "projected",
                 "dynasty_id": active_id,
                 "result_flips": state.get("result_flips"),
                 "rank_swap": state.get("rank_swap")}

    try:
        # `not postseason_here` may gate NEW selection and demote a stale
        # selected state (via the 3-strikes self-heal above), but it must
        # NEVER demote a COMPLETE season: after the user advances past the
        # postseason the slate legitimately empties (end-of-season recap /
        # offseason), and sending the complete state through the projection
        # path flattened the finished bracket back to a pre-playoff view and
        # broke the engrave flow (observed live, Texas A&M recap).
        complete_now = state.get("status") == "complete"
        selection_unavailable = (
            not terminal_result_waiting
            and (not ccgs or at_ccg
                 or (not postseason_here and not complete_now))
        )
        if selection_unavailable \
                or state.get("status") in (None, "projected"):
            if selection_unavailable:
                # Regular season / CCG week projection. Before the user crosses
                # the selection boundary, guarantee that a custom-field team
                # outside the top 12 is placed on CFB's own CFP route. A later
                # external insertion can look perfect and launch, yet CFB drops
                # the postgame result because that team's native postseason
                # cache was never created. Temporarily flipping every loss is
                # the only observed input that survives the boundary's ranking
                # recomputation. The first playoff write restores every score.
                _unswap_dynasty_ranks(dynasty, state.get("rank_swap"))
                bracket = playoff.build_bracket(dynasty, fmt)
                user_names = {(dynasty.get("team") or {}).get("name")} - {None}
                rows_by_name = {t.name: i for i, t in enumerate(roster)}
                user_row = next((rows_by_name[name] for name in user_names
                                 if name in rows_by_name), None)
                field_names = {seed.get("team")
                               for seed in bracket.get("seeds") or []}
                prepare_due = False
                if (at_ccg and user_row is not None
                        and bool(user_names & field_names)
                        and not state.get("result_flips")):
                    rank_now = next(
                        (team.rank for team in savepolls.parse(payload)
                         if team.row == user_row), 0)
                    _wins_now, losses_now = store.record(user_row)
                    prepare_due = (rank_now not in range(1, 13)
                                   and losses_now > 0)
                write_result = None
                if prepare_due and write:
                    write_result = _apply_prepare(user_row, roster)
                    if write_result.get("written"):
                        state["result_flips"] = write_result["flips"]
                        state["awaiting_reload"] = True
                        prepare_due = False
                state.update({"status": "projected"})
                _save_state(state)
                out = {
                    "available": True, "status": "projected",
                    "bracket": bracket, "in_game": False,
                    "needs_write": prepare_due,
                    "awaiting_reload": bool(state.get("awaiting_reload")),
                    "notes": ["Projected field if the season ended today."],
                    "guide": _build_guide(
                        status="projected", mode=None, bracket=None,
                        plan=None, store=None, user_names=user_names,
                        needs_write=prepare_due,
                        awaiting_reload=bool(state.get("awaiting_reload")),
                        slate_len=None, at_ccg=at_ccg,
                        prepare_due=prepare_due,
                        prepared=bool(state.get("result_flips")
                                      or state.get("rank_swap"))),
                }
                if write_result and write_result.get("written"):
                    out["save_written"] = True
                    out["notes"].append(
                        "Your real season scores are temporarily presented to "
                        "CFB as an undefeated record so it creates your native "
                        "playoff path. Reload the dynasty, advance past the "
                        "conference championships, then update again. Dynasty+ "
                        "restores every real score in that playoff write.")
                return out
            # CCGs are official and we have not selected yet: freeze the field
            _unswap_dynasty_ranks(dynasty, state.get("rank_swap"))
            bracket = playoff.build_bracket(dynasty, fmt)
            slots0 = _postseason_slots(payload)
            select_user_names = {
                (dynasty.get("team") or {}).get("name")} - {None}
            select_rows_by_name = {team.name: index
                                   for index, team in enumerate(roster)}
            select_user_rows = {
                select_rows_by_name[name] for name in select_user_names
                if name in select_rows_by_name}
            select_field = {seed.get("team")
                            for seed in bracket.get("seeds") or []}
            native_user_safe = (
                not bool(select_user_names & select_field)
                or _user_has_native_cfp_path(
                    payload, store, select_user_rows))
            mode = ("stock"
                    if stock_mode_fits(bracket, slots0) and native_user_safe
                    else "native"
                    if native_mode_fits(bracket, slots0) and native_user_safe
                    else "cycle")
            state.update({
                "status": "selected",
                "format": fmt,
                "bracket": bracket,
                "plan": {},
                "in_game": True,
                "mode": mode,
            })
            # the base snapshot is taken below in the cycling section, once
            # the ANCHOR WEEK is reached (the week holding the user's
            # engine-scheduled game); never overwritten once taken
            _save_state(state)

        # selected or later: fill results from the save and advance. Mapping
        # is progressive: a game claims a save record only once both its
        # teams are decided, so each week's assignments happen right after
        # the previous round finishes.
        _unswap_dynasty_ranks(dynasty, state.get("rank_swap"))
        bracket = state.get("bracket") or playoff.build_bracket(dynasty, fmt)
        plan = state.get("plan") or {}
        slots = _postseason_slots(payload)
        # THE SELECTION WINDOW: until a bracket game goes FINAL the field is
        # not carved in stone. The frozen bracket re-seeds whenever the
        # committee ranking or the format changes underneath it, so (a) a
        # user-edited CFP poll at bowl week re-picks and re-seeds the field
        # (the requested "edit the polls right before the playoff starts"),
        # and (b) a field frozen by an older build from stale data self-heals
        # to the live save on the next sync. Once any game is final the
        # bracket is history and never re-seeded.
        no_finals = not any(g.get("status") == "final"
                            for rnd in bracket.get("rounds") or []
                            for g in rnd["games"])
        if state.get("status") == "selected" and no_finals:
            try:
                fresh = playoff.build_bracket(dynasty, fmt)
            except playoff.BracketError:
                fresh = None
            if fresh is not None and (fresh.get("seeds") != bracket.get("seeds")
                                      or (state.get("format") or {}) != fmt):
                same_field = ([s.get("team") for s in fresh.get("seeds") or []]
                              == [s.get("team") for s in bracket.get("seeds") or []])
                bracket = fresh
                state["bracket"] = fresh
                state["format"] = fmt
                if not same_field:
                    # the field itself changed: every mapping is stale
                    plan = {}
                    state["plan"] = {}
            # the mode follows the (possibly re-seeded) bracket while nothing
            # has been played; this also migrates a run an older build put in
            # stock mode with a too-short bracket (the broken 4-team path) or
            # in cycle mode with a bracket native mode now covers
            window_user_names = {
                (dynasty.get("team") or {}).get("name")} - {None}
            window_rows_by_name = {team.name: index
                                   for index, team in enumerate(roster)}
            window_user_rows = {
                window_rows_by_name[name] for name in window_user_names
                if name in window_rows_by_name}
            window_field = {seed.get("team")
                            for seed in bracket.get("seeds") or []}
            window_native_path = (
                bool(state.get("user_cfp_path"))
                if state.get("user_cfp_path") is not None
                else _user_has_native_cfp_path(
                    payload, store, window_user_rows))
            window_native_safe = (
                not bool(window_user_names & window_field)
                or window_native_path)
            want_mode = (
                "stock" if stock_mode_fits(bracket, slots)
                and window_native_safe
                else "native" if native_mode_fits(bracket, slots)
                and window_native_safe
                else "cycle")
            if state.get("mode") not in (None, want_mode):
                # a mode flip remaps every record: drop the old plan
                plan = {}
                state["plan"] = {}
                state.pop("borrowed", None)
            state["mode"] = want_mode
        rows_by_name = {t.name: i for i, t in enumerate(roster)}
        mode = state.get("mode") or ("stock" if state.get("in_game") else "cycle")
        state["mode"] = mode
        state["in_game"] = True
        # notes are per-sync advisories, never persisted (scrub old states)
        state.pop("notes", None)
        state.pop("cycled_records", None)  # legacy in-place-cycling bookkeeping
        notes: list[str] = []
        write_result: dict[str, Any] | None = None
        cycling = mode == "cycle"
        # the user's own program, so its games claim scarce slots first while
        # cycling (never a bye while the user's bracket game is still waiting)
        user_names = {(dynasty.get("team") or {}).get("name")} - {None}
        user_rows = {rows_by_name[n] for n in user_names if n in rows_by_name}
        # the duplicate-user-game clear and the queue user-mark only apply
        # when the user is IN the custom field (otherwise their real,
        # engine-scheduled game must be left playable)
        field_names = {s.get("team") for s in bracket.get("seeds") or []}
        user_in_field = bool(user_names & field_names)
        user_native_active = user_in_field and not any(
            g_.get("winner") and g_["winner"] not in user_names
            for rnd in bracket.get("rounds") or [] for g_ in rnd["games"]
            if any(s.get("team") in user_names for s in g_["slots"]))
        native = mode == "native"
        # HYBRID ENDGAME (2026-07-13): a bracket bigger than the game's
        # postseason cycles its early rounds at the anchor week, then hands the
        # final <=16-team endgame (the last <=4 rounds: round of 16,
        # quarterfinals, semifinals, championship) to native mode so those play
        # forward on the real bowl-week calendar and are recorded in-game. The
        # handoff fires the moment every pre-endgame round is final (the 16
        # survivors are known). `use_native` then drives the native write path
        # for the tail; while the early rounds are unfinished the cycle path
        # runs as before. A pure native bracket (<=16 teams) has the whole
        # bracket as its tail, so use_native is true from the start.
        native_tail = native_tail_rounds(bracket) if cycling else set()
        # Every early round stays on the Bowl Week 1 cycle. A final-16 native
        # handoff is allowed for a live user only when CFB selected that program
        # for its own CFP path. Directly inserting an ordinary-bowl team produces
        # a Play Game action, but the engine discards the completed result unless
        # its hidden postseason cache is refreshed. The safe fallback keeps every
        # remaining user round on the proven organic bowl-record cycle.
        if cycling and state.pop("fallback_cycle", None):
            state.pop("route_forward_clean", None)
            notes.append(
                "This playoff was upgraded to the native final-16 handoff. "
                "Your preliminary matchup now stays in Bowl Week 1 instead "
                "of waiting for the ordinary bowl CFB 27 originally assigned.")
        if cycling and state.get("wave_format") == 9 \
                and state.get("base_wave"):
            notes.append(
                "This Bowl Week 1 wave is being rebuilt from its clean "
                "snapshot. A format 9 custom-bye placeholder could put an "
                "FCS team in a native CFP record and crash CFB 27 on load; "
                "format 10 replaces it with a safe non-field FBS opponent.")
        if cycling and state.get("wave_format") == 10 \
                and state.get("handoff") and state.get("base_wave"):
            notes.append(
                "This native handoff needs one repair update. The prior "
                "bowl rebuild protected all original playoff entrants instead "
                "of only the 16 survivors, which could leave incomplete Bowl "
                "Week 1 requests and crash CFB 27 on load. The repaired write "
                "restores complete matchups without changing your bracket.")
        hybrid = cycling and bool(native_tail)
        pre_tail_final = bool(native_tail) and all(
            g.get("status") == "final"
            for rnd in bracket.get("rounds") or []
            if str(rnd["round"]) not in native_tail
            for g in rnd["games"])
        # Native records are safe for a live user only when CFB selected that
        # program onto its own CFP path. Merely inserting the team and building
        # apparently complete request rows can launch a game whose postgame
        # result CFB discards because its internal team schedule cache still
        # belongs to an ordinary bowl. The reference editor can refresh that
        # cache only through retire and rehire. Dynasty+ instead stays on the
        # proven organic bowl-record cycle until the user is eliminated. New
        # seasons use the championship-week prepare above to make this fallback
        # exceptional by guaranteeing an engine-selected CFP path.
        current_native_path = (
            bool(state.get("user_cfp_path"))
            if state.get("user_cfp_path") is not None
            else _user_has_native_cfp_path(payload, store, user_rows))
        if state.get("user_cfp_path") is None:
            state["user_cfp_path"] = current_native_path
        legacy_native_cache_recovery = bool(
            cycling and state.get("handoff") and user_native_active
            and state.get("user_cfp_path") is False)
        native_tail_user_safe = not user_native_active or current_native_path
        cycle_native_tail = native_tail if native_tail_user_safe else set()
        # A pure native run reached this mode only after the selection-time
        # route check above. The runtime guard is for a hybrid handoff whose
        # user may still be attached to an ordinary bowl record.
        use_native = (native or (hybrid and pre_tail_final
                                 and native_tail_user_safe))
        first_tail = (min(native_tail, key=int) if native_tail else None)
        # for a hybrid handoff the endgame is written onto the pre-lock base
        # (the current world is the locked, cycled anchor week), so its borrow
        # and record hygiene read from the base; pure native operates on the
        # current pre-lock arrival. Resolved below once the base is loaded.
        snap_raw: bytes | None = None
        base_payload: bytes | None = None
        base_store: savesched.GameStore | None = None
        anchor_locked = False
        if cycling:
            # A LOCKED WORLD CAN NEVER BE THE BASE (the Notre Dame lesson,
            # extended 2026-07-12): the engine never re-locks a week it
            # already locked, so wave games written onto a post-lock snapshot
            # come up detached and are NEVER simmed; load-and-exit records
            # nothing, forever (reported live: a 9-game first round stuck at
            # 0 recorded; the save showed the wave matchups cleared to the
            # dormant 0x1d2d shape while the engine's own pre-sims of its
            # ORIGINAL slate sat untouched around them). Older builds took
            # the anchor snapshot from whatever the newest autosave was, so a
            # user who loaded into bowl week before the app first synced got
            # a post-lock base. Self-heal such a run: drop the doomed base
            # and re-anchor the whole cycle on the next PRE-lock arrival.
            if _snapshot_path().exists() and state.get("base_locked"):
                if not _week_locked(payload, store):
                    # the current save is a fresh, not-yet-locked arrival
                    # week: re-anchor everything here (new snapshot below)
                    _snapshot_path().unlink(missing_ok=True)
                    for k in ("slate_records", "base_wave", "wave_format",
                              "base_locked", "dead_records", "clobber_strikes",
                              "silent_strikes", "user_engine_week", "tail_caps",
                              "user_cfp_path", "awaiting_reload"):
                        state.pop(k, None)
                    # unmap every unfinished game: its record belonged to the
                    # dead base's week and means nothing at the new anchor
                    for rnd in bracket.get("rounds") or []:
                        recs = plan.get(str(rnd["round"])) or []
                        for gi, g_ in enumerate(rnd["games"]):
                            if gi < len(recs) and recs[gi] is not None \
                                    and g_.get("status") != "final":
                                recs[gi] = None
                                g_.pop("record_index", None)
                                g_.pop("_disk", None)
                    notes.append(
                        "The playoff re-anchored on this week. Its earlier "
                        "snapshot was taken after CFB 27 had already simmed "
                        "that week, which is why no playoff results were "
                        "being recorded.")
                elif state.get("status") in ("selected", "in_progress"):
                    # still sitting on the locked week: nothing written here
                    # can ever sim, so stop the wave loop and walk the user
                    # to a fresh week instead
                    anchor_locked = True
            # A hybrid always anchors on Bowl Week 1. Its preliminary rounds
            # cycle there, then its final 16 are written onto the same clean
            # arrival world before the user advances through the native CFP
            # weeks. The user's engine-selected destination is only diagnostic:
            # a program placed in a later ordinary bowl still gets its custom
            # Bowl Week 1 game, with the conditional in-game cache refresh
            # described in the guide if the Actions tab remains stale.
            uew_now = (_user_engine_week(payload, store, user_rows)
                       if (user_rows and user_in_field) else "none")
            # HYBRID anchors at bowl week 1 (the first postseason arrival, taken
            # by the freeze gate), NOT route-forward to the user's own bowl: the
            # native endgame needs the game's CFP records on their real weeks
            # (round of 16 on the first-round records at bowl week 1, then the
            # quarterfinals at week 2, and so on), so the early rounds must cycle
            # from week 1. The user's early-round games are made playable the
            # same way native mode does (the pre-lock queue mark), not by
            # riding their engine bowl.
            # A hybrid uses the cycle base only for the one-time round-of-16
            # bridge. Once `handoff` is set, every remaining round follows the
            # current save forward. The snapshot may stay on disk strictly as
            # a recovery copy; its presence never reactivates the bridge.
            need_anchor = not _snapshot_path().exists() and (
                (hybrid and not state.get("handoff"))
                or (not hybrid and uew_now in ("here", "none")))
            if need_anchor:
                ctx0 = confsetup._read_table()
                if ctx0 is not None:
                    if _week_locked(ctx0["payload"]):
                        # the arrival save is already post-lock (the user
                        # loaded into the week, or the app first saw the
                        # dynasty mid-week): snapshotting it would brick the
                        # cycle (see above), so wait for a fresh week instead.
                        # Only an ACTIVE run blocks on it; a completed season
                        # (its handoff is already complete) needs no new base.
                        if state.get("status") in ("selected", "in_progress"):
                            anchor_locked = True
                    else:
                        _snapshot_path().write_bytes(ctx0["raw"])
            state.pop("anchor_pending", None)
            if anchor_locked:
                state["awaiting_anchor"] = True
                _save_state(state)
                return {
                    "available": True, "status": state["status"],
                    "bracket": bracket, "in_game": True, "mode": mode,
                    "needs_write": False, "awaiting_reload": False,
                    "notes": [
                        "CFB 27 has already locked and simmed this bowl week, "
                        "so the playoff cannot schedule games into it. In CFB "
                        "27, play or sim the current week, advance to the next "
                        "bowl week, then exit to the main menu; the playoff "
                        "starts there automatically."],
                    "guide": _build_guide(
                        status=state["status"], mode=mode, bracket=bracket,
                        plan=plan, store=store, user_names=user_names,
                        needs_write=False, awaiting_reload=False,
                        slate_len=None, anchor_pending=True,
                        anchor_locked=True)}
            if not _snapshot_path().exists() and not hybrid:
                # the user has not reached their first game's week yet: do not
                # cycle (no anchor); guide them to advance to it. Their game
                # enters the slate when they arrive, and the anchor is taken
                # then. A top-4 seed advances one week (past the first-round
                # bye) to their quarterfinal; nothing before then is disturbed.
                # (hybrid never waits: it anchored at bowl week 1 above.)
                state["awaiting_anchor"] = True
                _save_state(state)
                target = _user_engine_target_week(payload, store, user_rows)
                where = f"bowl week {target}" if target else "the bowl week that holds your first playoff game"
                return {
                    "available": True, "status": state["status"],
                    "bracket": bracket, "in_game": True, "mode": mode,
                    "needs_write": False, "awaiting_reload": False,
                    "notes": [f"Advance in CFB 27 to {where} (you have a "
                              "first-round bye), then exit to the main menu. "
                              "The playoff anchors there and begins."],
                    "guide": _build_guide(
                        status=state["status"], mode=mode, bracket=bracket,
                        plan=state.get("plan") or {}, store=store,
                        user_names=user_names, needs_write=False,
                        awaiting_reload=False, slate_len=None,
                        anchor_pending=True, target_week=target)}
            state.pop("awaiting_anchor", None)
            if _snapshot_path().exists():
                snap_raw = _snapshot_path().read_bytes()
                base_payload = container.decode(snap_raw).payload
                base_store = savesched.parse(base_payload)
                # the base week's slate: which records the engine will lock
                # (sim or offer for play) on loading the base world
                if not state.get("slate_records"):
                    state["slate_records"] = savesched.week_slate(base_payload)
                if state.get("user_engine_week") is None and user_rows:
                    state["user_engine_week"] = _user_engine_week(
                        base_payload, base_store, user_rows)
                if state.get("tail_caps") is None:
                    # which stock rounds lie AFTER the anchor week (only
                    # those can host the calendar tail; a stock round whose
                    # records sit in the anchor slate is wave territory)
                    stock = _postseason_slots(base_payload)
                    in_slate = set(state["slate_records"])
                    caps = []
                    for kind, cap in (("championship", 1), ("semifinal", 2),
                                      ("quarterfinal", 4)):
                        if any(r in in_slate for r in stock.get(kind) or []):
                            break
                        caps.append(cap)
                    state["tail_caps"] = caps
                if state.get("user_cfp_path") is None and user_rows:
                    # whether the user's engine game sits on the stock CFP
                    # records: only then do the calendar-tail weeks carry
                    # native user wiring (the engine advances the user
                    # through ITS bracket as they win)
                    stock = _postseason_slots(base_payload)
                    stock_recs = {r for v in stock.values() for r in v}
                    state["user_cfp_path"] = any(
                        r in stock_recs for r in state["slate_records"]
                        if r < len(base_store.games)
                        and ({base_store.games[r].away_row,
                              base_store.games[r].home_row} & user_rows))
                if state.get("base_locked") is None:
                    # a snapshot that raced the in-session lock: waves written
                    # from it never sim (see the self-heal above, which this
                    # flag arms on the NEXT sync). New anchors are gated on
                    # _week_locked, so this only trips for bases taken by
                    # older builds or adopted mid-postseason.
                    state["base_locked"] = any(
                        base_store.games[r].presimmed or base_store.games[r].has_result
                        for r in state["slate_records"] if r < len(base_store.games))
        # NATIVE/HYBRID borrow: reserve extra first-round bowl hosts (and drop
        # the user's own engine record from the host pools). A hybrid endgame
        # is written onto the PRE-LOCK base (the current anchor week is locked
        # after cycling), so it borrows from the base's slate; pure native uses
        # the current pre-lock arrival. Runs before the fill loop so the
        # assignment sees the extended slots.
        # THE NATIVE REFERENCE WORLD. Pure native reasons about record state
        # from the current pre-lock arrival. A HYBRID handoff writes the
        # endgame's first round (round of 16) onto the pre-lock BASE (the
        # current anchor week is locked from cycling), so while that round is
        # unwritten the native fill + write must judge record availability,
        # the slate, and matchups from the BASE, not the spent cycled world;
        # once it is played, first_tail_final makes the current world take over
        # and the saved base remains recovery-only.
        first_tail_final = bool(first_tail) and all(
            g.get("status") == "final"
            for rnd in bracket.get("rounds") or []
            if str(rnd["round"]) == first_tail
            for g in rnd["games"])
        bridging = (hybrid and use_native and snap_raw is not None
                    and not first_tail_final)
        nstore = base_store if (bridging and base_store is not None) else store
        npayload = (container.decode(snap_raw).payload
                    if (bridging and snap_raw is not None) else payload)
        if use_native:
            # The record store, payload, AND slot classification must describe
            # the same reference world. The cycled save has relabeled borrowed
            # bowls, so carrying its slot list into a clean-base bridge can
            # make regular bowls look like stock first-round records. Borrowing
            # then undercounts capacity and leaves native games unmapped.
            slots = (_postseason_slots(npayload) if bridging
                     else dict(slots))
            if bridging and base_store is not None and snap_raw is not None:
                _native_borrow(state, bracket, slots, base_store,
                               container.decode(snap_raw).payload,
                               user_rows, user_native_active, notes)
            else:
                # Pure native and the post-handoff portion of a hybrid both
                # reason from the current forward-moving arrival save.
                _native_borrow(state, bracket, slots, store, payload,
                               user_rows, user_native_active, notes)
        if cycling and not use_native:
            # Older cycle plans could stage a ready user game from the next
            # round while ordinary games in the current round were still
            # waiting. Remove that mapping before user_live is calculated,
            # otherwise the premature game freezes assignment forever.
            gate_notes = _enforce_cycle_round_gate(
                bracket, plan, skip_rounds=cycle_native_tail)
            if not legacy_native_cache_recovery:
                notes.extend(gate_notes)
        # the user's unfinished mapped wave game, if any, and whether it is
        # LIVE in the current save (record still theirs, not yet official).
        # While live, the whole wave is FROZEN: no new assignments and no
        # base rewrite, so the world the user is playing is never disturbed
        # and the staged-wave bookkeeping stays true. Applies only to worlds
        # written by this build (wave_format); older worlds must rewrite.
        migrated = state.get("wave_format") == _WAVE_FORMAT
        user_rec = None
        if cycling and user_in_field:
            for rnd in bracket.get("rounds") or []:
                recs = plan.get(str(rnd["round"])) or []
                for g_, rec in zip(rnd["games"], recs):
                    if rec is not None and g_.get("status") != "final" and \
                            any(s.get("team") in user_names for s in g_["slots"]):
                        user_rec = rec
        user_live = False
        if migrated and user_rec is not None and user_rec < len(store.games):
            gr = store.games[user_rec]
            # live means the record holds THE MAPPED GAME'S matchup (not
            # merely the user's team: a leftover engine pairing on the
            # user's record, e.g. the original bowl opponent surviving a
            # wave where the user's next game was undecided, must be
            # REWRITTEN, not protected)
            user_game = next(
                (g_ for rnd in bracket.get("rounds") or []
                 for g_, rec in zip(rnd["games"],
                                    plan.get(str(rnd["round"])) or [])
                 if rec == user_rec and g_.get("status") != "final"), None)
            if user_game is not None and not gr.official and \
                    (gr.away_row in user_rows or gr.home_row in user_rows):
                want = {rows_by_name.get(s.get("team"))
                        for s in user_game["slots"] if s.get("team")}
                if {gr.away_row, gr.home_row} == want:
                    user_live = True
        # Records whose base matchup involves the user are exempt from the
        # dead-record quarantine and reserved against CPU games.
        user_base_recs = set()
        if base_store is not None and user_rows:
            user_base_recs = {r for r in state.get("slate_records") or []
                              if r < len(base_store.games)
                              and ({base_store.games[r].away_row,
                                    base_store.games[r].home_row} & user_rows)}
        frozen_user_rec = (state.get("user_frozen") or {}).get("record")
        if isinstance(frozen_user_rec, int):
            # A CFP-bye user can have no record in the Bowl Week 1 base and
            # still play an early custom game on a borrowed wave record. Once
            # they lose, that dynamically chosen record is just as sacred as
            # a base user bowl: later CPU assignment must not reuse it while
            # user_frozen restores the old matchup over every write.
            user_base_recs.add(frozen_user_rec)
        pre_final = {g["id"] for rnd in bracket.get("rounds") or []
                     for g in rnd["games"] if g.get("status") == "final"}
        misfires: dict[str, set[int]] = {}
        reseeding = bool((bracket.get("format") or {}).get("reseed"))
        live_slate = set(savesched.week_slate(payload))
        for _ in range(len(bracket.get("rounds") or []) + 1):
            # cycle-phase rounds read the engine's pre-sims (allow_unofficial);
            # once the endgame hands off to native, its rounds read only
            # OFFICIAL results (they play forward on the real calendar)
            _fill_results(bracket, plan, store, roster,
                          allow_unofficial=(cycling and not use_native),
                          unofficial_records=(live_slate if use_native else None),
                          user_names=user_names, misfires=misfires)
            recovered_notes = (_recover_native_advancements(
                bracket, plan, store, roster, slots, live_slate)
                if use_native else [])
            if recovered_notes:
                notes.extend(recovered_notes)
            if reseeding:
                # a finished round re-pairs the next one from its survivors;
                # the assignment below then maps the newly decided games
                playoff.fill_reseeded_rounds(bracket)
            if cycling and not use_native and misfires.get("skipped"):
                # a record aged to official-with-no-result was SKIPPED by the
                # engine outright: quarantine on the first strike, inside the
                # loop so this sync's reassignment already avoids it
                add = misfires["skipped"] - user_base_recs \
                    - set(state.get("dead_records") or [])
                if add:
                    state["dead_records"] = sorted(
                        set(state.get("dead_records") or []) | add)
            if cycling and not use_native:
                if user_live:
                    break  # plan frozen while the user's game is live
                user_alive = user_in_field and not any(
                    g_.get("winner") and g_["winner"] not in user_names
                    for rnd in bracket.get("rounds") or [] for g_ in rnd["games"]
                    if any(s.get("team") in user_names for s in g_["slots"]))
                pool = _slate_pool(state, base_store) if base_store is not None else []
                if (not user_in_field or not user_alive) and user_rows \
                        and base_store is not None:
                    # the user's OWN engine record is never a wave host: while
                    # they are not in the field it holds the engine's real game
                    # for them; once ELIMINATED it holds their LAST played
                    # result and must be left alone (writing a CPU pairing there
                    # was overwriting the user's own game, e.g. Oregon vs
                    # Colorado after the SDSU loss).
                    finished_user_recs = {
                        rec for rnd in bracket.get("rounds") or []
                        for game, rec in zip(
                            rnd["games"], plan.get(str(rnd["round"])) or [])
                        if rec is not None and game.get("status") == "final"
                        and any(slot.get("team") in user_names
                                for slot in game.get("slots") or [])
                    }
                    protected_user_recs = user_base_recs | finished_user_recs
                    pool = [r for r in pool if r not in protected_user_recs]
                # The retired calendar-tail path stays disabled here. It tried
                # to write future CFP records before their arrival boundary,
                # so the engine rebuilt over them. The supported HYBRID path
                # is separate: cycle only rounds before the native tail, then
                # bridge the round of 16 onto the clean pre-lock base and let
                # each later arrival week be written by the native branch.
                tail_ok = False
                cal = (_calendar_rounds(bracket, state.get("tail_caps"))
                       if tail_ok else set())
                if reseeding:
                    immediate_path: set[str] = set()
                    path_games = _reseed_gate_games(bracket)
                else:
                    immediate_path, later_path = _user_path_groups(
                        bracket, user_names)
                    path_games = immediate_path | later_path
                # A playable campus or plain-neutral cycle game stays on the
                # user's organic record, but its borrowed bowl identity cannot
                # supply valid CFP field art. Reserve one native first-round
                # record on a sibling game so the write pass has a unique,
                # custom-owned identity to swap onto the user's record.
                needs_cfp_presentation = user_alive and any(
                    game.get("status") != "final"
                    and all(slot.get("type") == "team"
                            for slot in game.get("slots") or [])
                    and any(slot.get("team") in user_names
                            for slot in game.get("slots") or [])
                    and ((game.get("site") or {}).get("type") == "campus"
                         or ((game.get("site") or {}).get("type") == "neutral"
                             and not (game.get("site") or {}).get("bowl")))
                    for rnd in bracket.get("rounds") or []
                    if str(rnd["round"]) not in cal | cycle_native_tail
                    for game in rnd.get("games") or [])
                presentation_records = (
                    set(_postseason_slots(base_payload).get("first_round") or [])
                    if needs_cfp_presentation and base_payload is not None
                    else set())
                changed = base_store is not None and _assign_records_cycle(
                    bracket, plan, pool, base_store,
                    rows_by_name, priority_names=user_names,
                    path_ids=path_games,
                    immediate_path_ids=immediate_path,
                    # skip the native endgame rounds: they hand off to the
                    # forward calendar once the early rounds are all final
                    user_alive=user_alive, skip_rounds=cal | cycle_native_tail,
                    # map the user's own game into the wave only while they are
                    # alive; once eliminated there is no user game and their
                    # record is out of the pool (left with their last result)
                    user_present=user_alive,
                    presentation_records=presentation_records)
                if cal:
                    sub = {"rounds": [rnd for rnd in bracket.get("rounds") or []
                                      if str(rnd["round"]) in cal]}
                    # REACTIVE PIN: map the user's current tail-round game onto
                    # the CFP record the engine ACTUALLY put them in this week
                    # (found by reading the current save), and reserve it, so
                    # the opponent rewrite lands on their live game and no CPU
                    # game overwrites it.
                    _pin_user_tail(sub, plan, slots, store, rows_by_name,
                                   user_names, bracket)
                    # map the calendar rounds onto the stock QF/SF/NCG records
                    # (a sub-bracket view keeps the walk-back kinds aligned)
                    changed = _assign_records(
                        sub, plan, slots, store, rows_by_name) or changed
            else:
                changed = False
                if use_native and user_native_active:
                    # reserve the user's engine record for their OWN game
                    # before positional assignment can hand it to a sibling
                    # (against the base while bridging the hybrid handoff)
                    changed = _native_pin_user(
                        bracket, plan, slots, nstore, npayload,
                        user_names, user_rows) or changed
                changed = (_assign_records(
                    bracket, plan, slots, nstore, rows_by_name) or changed)
            changed = bool(changed or recovered_notes)
            if not changed:
                break
        if cycling and not use_native:
            finished_user_recs = {
                rec for rnd in bracket.get("rounds") or []
                for game, rec in zip(
                    rnd["games"], plan.get(str(rnd["round"])) or [])
                if rec is not None and game.get("status") == "final"
                and any(slot.get("team") in user_names
                        for slot in game.get("slots") or [])
            }
            _quarantine_dead_records(state, bracket, plan, store, roster,
                                     misfires,
                                     user_base_recs | finished_user_recs,
                                     user_names,
                                     pre_final, notes)
        if legacy_native_cache_recovery and user_rec is not None:
            accepted = any(
                game.get("status") == "final" and game.get("id") not in pre_final
                and rec == user_rec
                and any(slot.get("team") in user_names
                        for slot in game.get("slots") or [])
                for rnd in bracket.get("rounds") or []
                for game, rec in zip(
                    rnd["games"], plan.get(str(rnd["round"])) or []))
            if accepted:
                # A persisted result is the only reliable proof that the
                # retire-and-rehire refresh rebuilt CFB's hidden team route.
                # From the next sync onward this user may follow the native tail.
                state["user_cfp_path"] = True
                legacy_native_cache_recovery = False
                notes.append(
                    "CFB accepted the repaired user result. The native playoff "
                    "route is refreshed and later rounds continue normally.")
        state["plan"] = plan
        # Keep the hybrid's clean Bowl Week 1 anchor through completion. It is
        # no longer used after the round-of-16 bridge (bridging is gated by
        # first_tail_final above), but it is the only safe recovery point if a
        # later game patch damages CFB's boundary allocation. Completion
        # already exempts hybrid runs from the pure-cycle restore and removes
        # the snapshot normally.
        # freeze the user's OWN played game the moment it is official, so a
        # rewind can restore it verbatim instead of resetting their schedule
        # (cycle phase only; the native endgame plays forward with no rewind,
        # so its records keep the user's real result on their own)
        if cycling and not use_native and user_in_field:
            _capture_user_result(state, store, bytes(payload), bracket, plan,
                                 user_names, rows_by_name)
        # Reload tracking: after the app writes matchups, the game only picks
        # them up when the user reloads the dynasty (it holds the loaded week
        # in memory). The flag set on every write clears as soon as the
        # ENGINE visibly touches one of our mapped records (a pre-sim result
        # appears or a wave game goes official) - evidence the running game
        # is working from a world that contains the wave.
        if state.get("awaiting_reload"):
            # ``_fill_results`` runs immediately above this block. When CFB
            # pre-sims every CPU game in a round but leaves the user's game
            # open, those CPU games have already changed to ``final`` and the
            # unfinished-only scan below can no longer see them. The newly
            # captured finals are themselves the strongest possible proof
            # that CFB loaded this staged world, so clear the flag before
            # looking for an as-yet-uncaptured result. Without this check the
            # guide loops on Update/Load even while the correct Play Game
            # action is present (Texas Tech vs Ohio State, round four).
            newly_captured = any(
                game.get("status") == "final" and game.get("id") not in pre_final
                for rnd in bracket.get("rounds") or []
                for game in rnd.get("games") or [])
            if newly_captured:
                state["awaiting_reload"] = False
            # the pinned record does NOT count as evidence: its result was
            # written by the app's own pin, not the engine, and it is present
            # on every post-elimination wave, so counting it silenced the
            # reload banner for the whole CPU sim-out (review finding)
            pin_rec = (state.get("user_frozen") or {}).get("record")
            name_by_row = {i: team.name for i, team in enumerate(roster)}
            for rnd in bracket.get("rounds") or []:
                if not state.get("awaiting_reload"):
                    break
                recs = plan.get(str(rnd["round"])) or []
                if any(game.get("status") != "final"
                       and rec is not None and rec != pin_rec
                       and rec < len(store.games)
                       and store.games[rec].has_result
                       and _record_matches(store.games[rec], game, name_by_row)
                       for game, rec in zip(rnd["games"], recs)):
                    state["awaiting_reload"] = False
                    break
        needs_write = False
        rewound = False
        advance_prompt = False
        calendar_keys: set[str] = set()
        calendar_ready: set[str] = set()  # tail rounds whose week is CURRENT
        if state.get("status") in ("selected", "in_progress"):
            if cycling and not use_native:
                # CYCLE MODE: every write rebuilds the world from the PRE-LOCK
                # base snapshot with the wave's matchups in place, so the
                # engine locks them itself on load (the only way the USER's
                # own game reaches the dynasty home screen; an in-place patch
                # of a locked week only changes the schedule display). A write
                # is due when the current save does not already stage every
                # unfinished mapped game; mid-wave the world is left alone.
                # For a hybrid bracket this runs only for the EARLY rounds;
                # once they are all final the endgame hands off to native
                # (the elif below).
                handles = savestadiums.stadium_table(payload)
                bowl_handles = _bowl_stadium_handles(payload)
                user_alive_now = user_in_field and not any(
                    g_.get("winner") and g_["winner"] not in user_names
                    for rnd in bracket.get("rounds") or [] for g_ in rnd["games"]
                    if any(s.get("team") in user_names for s in g_["slots"]))
                user_unfinished = user_in_field and any(
                    g_.get("status") != "final"
                    for rnd in bracket.get("rounds") or [] for g_ in rnd["games"]
                    if any(s.get("team") in user_names for s in g_["slots"]))
                # ACTIVE = the user still has a game to play (alive AND a game
                # left this run): only then does the cycle FCS-fill their record
                # and queue-mark it. DONE = in the field with no game left
                # (eliminated, or champion): keep their last played result
                # untouched - stop the FCS fill, drop them from the wave pool
                # (fix above), and PIN their real final game onto their record
                # across every rewind. The remaining rounds sim as CPU waves.
                user_active = user_in_field and user_alive_now and user_unfinished
                user_done = user_in_field and not user_unfinished
                user_freeze = (state.get("user_frozen") if user_done else None)
                tail_ok = False  # calendar tail disabled; cycle at the anchor
                cal = (_calendar_rounds(bracket, state.get("tail_caps"))
                       if tail_ok else set())
                calendar_keys = cal
                tail_active = bool(cal) and all(
                    g_.get("status") == "final"
                    for rnd in bracket.get("rounds") or []
                    if str(rnd["round"]) not in cal
                    for g_ in rnd["games"])
                if tail_active:
                    # THE CALENDAR TAIL: the remaining rounds ride the game's
                    # own postseason weeks (QF week 2, SF week 3, NCG week 4).
                    # ONLY the round whose stock records are in the CURRENT
                    # slate is written - a future round is written after the
                    # user ADVANCES to its week (else the game gets pre-written
                    # to a week the user is not on, so they reload and still see
                    # last week's completed game, and the premature write can
                    # collide with the engine's own bracket build). If no tail
                    # round is at the current week, guide the user to advance.
                    state["tail"] = True
                    slate_now = set(savesched.week_slate(payload))
                    stock_slots = _postseason_slots(payload)
                    kind_of = _round_kind_map(bracket)
                    cal_now = {k for k in cal if any(
                        r in slate_now for r in (stock_slots.get(kind_of.get(k)) or []))}
                    calendar_ready = cal_now
                    if cal_now:
                        if write:
                            write_result = _apply_to_save(
                                bracket, plan, regen_bowls=False,
                                user_rows=user_rows if user_active else None,
                                only_rounds=cal_now, bowl_state=state)
                        else:
                            probe = _apply_to_save(
                                bracket, plan, regen_bowls=False,
                                user_rows=user_rows if user_active else None,
                                dry_run=True, only_rounds=cal_now,
                                bowl_state=state)
                            needs_write = bool(probe.get("would_write"))
                    elif user_active:
                        # the user's next game is on a LATER bowl week
                        needs_write = False
                        notes.append(
                            "Your next playoff game is on the next bowl week. In "
                            "CFB 27, advance one bowl week, then exit and press "
                            "Update Dynasty File; your matchup is set there, not "
                            "on the current week.")
                if not tail_active:
                    has_wave = any(
                        rec is not None and g.get("status") != "final"
                        for rnd in bracket.get("rounds") or []
                        if str(rnd["round"]) not in cal
                        for g, rec in zip(rnd["games"],
                                          plan.get(str(rnd["round"])) or []))
                    # wave format 2+ = queue user-mark writes (a world written
                    # by an older build lacks it: the user's game was
                    # pre-simmed as a CPU game, so it must be rewritten). While
                    # the user's game is LIVE (user_live, computed above, which
                    # also froze the plan) the world is never rewritten: newly
                    # decided games wait for the next wave.
                    staged = bool(state.get("base_wave")) and migrated and _wave_staged(
                        payload, bracket, plan, store, rows_by_name, handles,
                        skip_rounds=cal, bowl_handles=bowl_handles,
                        user_rows=user_rows,
                        bowl_table=savebowls.parse(payload))
                    due = (has_wave and not staged and snap_raw is not None
                           and not user_live)
                    # the wave's SECOND step: once the user has loaded the wave
                    # (the lock allocated the record's result slots) the user
                    # request row's +40 must be filled in place, or the hub
                    # keeps showing a bye. Only when the wave itself is staged.
                    user_fix = (not due and staged and user_rec is not None
                                and savesched.user_pending_fix_due(
                                    payload, user_rec, user_rows))
                    if not write:
                        needs_write = due or user_fix
                    elif user_fix:
                        write_result = _apply_user_fix(user_rec, user_rows)
                        if write_result.get("written"):
                            notes.append(
                                "The user schedule row is updated. Reload the "
                                "dynasty, open Actions, and play the scheduled "
                                "matchup.")
                    elif due:
                        # NO BASE REBASE, EVER (removed 2026-07-09, Notre Dame
                        # run): a mid-session autosave is POST-lock, and the
                        # engine does NOT re-lock a week it already locked, so
                        # wave records cleared to the scheduled-unplayed shape
                        # on such a base come up DETACHED on reload: the CPU
                        # games are never simmed (observed in-game: the user's
                        # whole second round sat unsimmed; only their own game,
                        # kept alive by the per-team user wiring, was playable).
                        # Only the pre-lock ARRIVAL autosave re-locks and
                        # re-sims on load, so the anchor snapshot is the one
                        # and only wave base. Cost: the week's one-time
                        # presentations (the Heisman ceremony) replay on every
                        # rewound load; fixing that needs the watched-flag
                        # byte, not a different base. The emulator models
                        # every load as PRE-lock, so it cannot catch this
                        # class of bug; do not trust it alone for base-shape
                        # changes.
                        # a wave replacing a progressed world is a rewind
                        progressed = any(
                            r < len(store.games)
                            and (store.games[r].official or store.games[r].has_result)
                            for r in state.get("slate_records") or [])
                        write_result = _apply_to_save(
                            bracket, plan, regen_bowls=False, base_raw=snap_raw,
                            user_rows=user_rows if user_active else None,
                            user_freeze=user_freeze,
                            pristine=True, rank_swap=state.get("rank_swap"),
                            result_flips=state.get("result_flips"),
                            only_rounds={str(rnd["round"])
                                         for rnd in bracket.get("rounds") or []
                                         if str(rnd["round"]) not in cal},
                            bowl_state=state)
                        if write_result.get("written"):
                            state["base_wave"] = True
                            state["wave_format"] = _WAVE_FORMAT
                            state["plan"] = plan
                            if progressed:
                                rewound = True
                                state["rewinds"] = int(state.get("rewinds") or 0) + 1
                    if has_wave and snap_raw is None \
                            and not legacy_native_cache_recovery:
                        notes.append(
                            "The playoff needs the base-week snapshot to schedule "
                            "its games, but none exists and no save is readable.")
            elif use_native:
                # NATIVE MODE (2026-07-13): every round is written onto its
                # OWN bowl week's pre-lock arrival autosave, the same write
                # shape as a cycle wave (the engine locks the matchups itself
                # on the next load, including the user's queue mark), but the
                # calendar only ever moves FORWARD: no snapshot, no rewinds,
                # no completion restore, and every game records on its real
                # bowl week. Rounds whose stock records are not in the
                # current slate wait for the user to advance to their week;
                # the engine's own CFP games in the weeks before the
                # bracket's first round are dead-week games that count for
                # nothing (the arrival re-write replaces whatever the
                # engine's boundary built from them).
                #
                # HYBRID HANDOFF: for a >16 bracket the endgame's FIRST round
                # (the round of 16) is written by rewinding to the cycle base
                # one last time (the current anchor week is locked after
                # cycling the early rounds), exactly like a cycle wave; after
                # the user plays it, the remaining rounds move forward. The
                # snapshot is retained only as a recovery copy and is never
                # written again after the bridge.
                # while bridging the hybrid handoff, reason from the pre-lock
                # BASE (the round-of-16 is written there); otherwise from the
                # current forward-advanced arrival
                slate_now = set(savesched.week_slate(npayload))
                kind_of = _round_kind_map(bracket)
                # native uses its own step vocabulary in _build_guide (keyed
                # off mode, not on_calendar), so calendar_keys stays empty;
                # calendar_ready carries the rounds whose week is CURRENT,
                # which drives the per-round cursor (advance vs load/play)
                ready = _native_ready_rounds(bracket, slots, slate_now)
                # The NEXT round is written before this week's advance, once
                # all of its participants are known. CFB allocates result
                # objects at that boundary; waiting until arrival produced
                # one-object quarterfinals that played but could not save.
                prestage = _native_prestage_rounds(
                    bracket, slots, slate_now) - ready
                write_rounds = ready | prestage
                calendar_ready = ready
                locked_now = _week_locked(npayload, nstore)
                # records hosting an ENDGAME (native tail) game. For a hybrid
                # this must EXCLUDE the early cycle rounds' plan records: the
                # bridge writes onto the clean base, where those records are
                # just base bowls to be regenerated (keeping them would leave
                # a survivor double-booked in a leftover bowl and freeze the
                # advance). Pure native has no cycle rounds, so this is every
                # mapped record.
                tail_keys = native_tail if hybrid else None
                assigned_all = {
                    rec for key, recs in plan.items()
                    if tail_keys is None or key in tail_keys
                    for rec in recs or [] if rec is not None}
                # Only records that actually host an unfinished custom game
                # are exempt from ordinary-bowl regeneration. A user game can
                # pin itself to a separate engine record after the borrow pool
                # was chosen, leaving one persisted borrowed candidate unused.
                # Keeping that unused bowl preserves its original field team
                # beside the same team in a custom CFP record and freezes the
                # week (64-team repro: Houston appeared in records 373/927).
                keep = assigned_all
                # the engine's own leftover playoff pairings on this week's
                # unclaimed stock records would double-book field teams (a
                # frozen engine on advance); they are neutralized to FCS
                # filler by the write below
                user_recs_now = {g.index for g in nstore.games
                                 if g.index in slate_now and not g.official
                                 and ({g.away_row, g.home_row} & user_rows)}
                stock_now = _postseason_slots(npayload)
                neutral = {r
                           for rnd in bracket.get("rounds") or []
                           if str(rnd["round"]) in ready
                           for r in stock_now.get(
                               kind_of.get(str(rnd["round"]))) or []
                           if r in slate_now and r < len(nstore.games)
                           and not nstore.games[r].official
                           and r not in assigned_all
                           and r not in user_recs_now}
                # future-round stock records the engine pre-penciled a field
                # team into (the top seeds sit in the quarterfinal records at
                # arrival, but play EARLIER in the custom bracket): blank them
                # to TBD so advancing into the next week is not a double-book.
                # The engine rebuilds that round at its own boundary and the
                # app writes the custom matchup over it when its week arrives.
                field_rows = {rows_by_name[n] for n in field_names
                              if n in rows_by_name}
                blank = {r
                         for rnd in bracket.get("rounds") or []
                         if str(rnd["round"]) not in write_rounds
                         for r in stock_now.get(
                             kind_of.get(str(rnd["round"]))) or []
                         if r < len(nstore.games) and not nstore.games[r].official
                         and r not in assigned_all
                         and ({nstore.games[r].away_row,
                               nstore.games[r].home_row} & field_rows)}
                # the user's queue machinery applies only when their own
                # unfinished custom game is part of this week's write
                user_rec_n = next(
                    (rec for rnd in bracket.get("rounds") or []
                     if str(rnd["round"]) in ready
                     for g_, rec in zip(rnd["games"],
                                        plan.get(str(rnd["round"])) or [])
                     if rec is not None and g_.get("status") != "final"
                     and any(s.get("team") in user_names
                             for s in g_["slots"])), None)
                user_here = user_in_field and user_rec_n is not None
                # the handoff bridge: the round of 16 rewinds to the cycle base
                # one last time (the current anchor week is locked from
                # cycling), so it is a pristine base write like a wave; every
                # later endgame round writes forward at its own arrival
                bridge = (hybrid and snap_raw is not None and first_tail in ready)
                base_raw_n = snap_raw if bridge else None
                pristine_n = True if bridge else (not locked_now)
                # Once the freshly written native round is present in the
                # CURRENT save, it remains the active world both before and
                # after CFB 27 locks it. Comparing that loaded world back to
                # the clean bridge snapshot always finds the intentional
                # matchup delta and used to send the guide into an endless
                # Update, Load, Update loop. Match the ready round against the
                # current save first. A migrated, matching round must never be
                # rewritten until the user advances and the engine makes the
                # next bowl week current.
                ready_records = [
                    rec for rnd in bracket.get("rounds") or []
                    if str(rnd["round"]) in ready
                    for game, rec in zip(
                        rnd["games"], plan.get(str(rnd["round"])) or [])
                    if rec is not None and rec < len(store.games)
                    and game.get("status") != "final"
                    and all(slot.get("type") == "team"
                            for slot in game.get("slots") or [])]
                ready_mapped = bool(ready_records)
                prestage_records = [
                    rec for rnd in bracket.get("rounds") or []
                    if str(rnd["round"]) in prestage
                    for game, rec in zip(
                        rnd["games"], plan.get(str(rnd["round"])) or [])
                    if rec is not None and rec < len(store.games)
                    and game.get("status") != "final"
                    and all(slot.get("type") == "team"
                            for slot in game.get("slots") or [])]
                expected_prestage = sum(
                    1 for rnd in bracket.get("rounds") or []
                    if str(rnd["round"]) in prestage
                    for game in rnd["games"]
                    if game.get("status") != "final")
                prestage_mapped = (not prestage or
                                   len(prestage_records) == expected_prestage)
                skip_ready = {str(rnd["round"])
                              for rnd in bracket.get("rounds") or []
                              if str(rnd["round"]) not in ready}
                skip_prestage = {str(rnd["round"])
                                 for rnd in bracket.get("rounds") or []
                                 if str(rnd["round"]) not in prestage}
                # A save repaired directly from the reference tool's exact
                # three-field recipe can be format-current even when an older
                # running app process last persisted wave_format=11. Recognize
                # the on-disk HomeScheduled shape and migrate metadata without
                # asking for another destructive rewrite.
                reference_staged = ready_mapped and all(
                    payload[store.games[rec].offset + 84] & 0xF0 == 0x60
                    and payload[store.games[rec].offset + 97] & 0x11 == 0
                    for rec in ready_records)
                if reference_staged and not migrated:
                    state["wave_format"] = _WAVE_FORMAT
                staged_args = (
                    payload, bracket, plan, store, rows_by_name,
                    savestadiums.stadium_table(payload))
                ready_staged = (not ready) or (
                    ready_mapped and (migrated or reference_staged)
                    and _wave_staged(
                        *staged_args, skip_rounds=skip_ready,
                        bowl_handles=_bowl_stadium_handles(payload),
                        user_rows=user_rows,
                        bowl_table=savebowls.parse(payload)))
                # Future-round staging deliberately does not touch this
                # week's user request or temporary field recipe. Validate its
                # matchup and venue only; presentation is finalized on arrival.
                prestage_staged = (not prestage) or (
                    prestage_mapped and _wave_staged(
                        *staged_args, skip_rounds=skip_prestage,
                        bowl_handles=_bowl_stadium_handles(payload),
                        user_rows=set(),
                        bowl_table=savebowls.parse(payload)))
                if prestage and prestage_staged \
                        and not _native_boundary_snapshot_path().exists():
                    _capture_native_boundary_snapshot(prestage_records)
                forced_recovery = set(
                    state.get("force_boundary_recovery_records") or [])
                request_issue = [
                    rec for rec in ready_records
                    if rec in slate_now and rec < len(store.games)
                    and (rec in forced_recovery
                         or savesched.request_id_pair_partial(
                             payload, store.games[rec]))]
                native_staged = bool(write_rounds) and ready_staged \
                    and prestage_staged and not request_issue
                duplicate_user_request = bool(
                    user_rec_n is not None
                    and savesched.user_pending_count(payload, user_rec_n) > 1)
                pending_prestage = set(state.get("prestage_records") or [])
                if pending_prestage and pending_prestage <= slate_now \
                        and ready_staged and all(
                            record < len(store.games)
                            and savesched.request_id_pair_complete(
                                payload, store.games[record])
                            for record in pending_prestage):
                    # The week boundary itself is proof that CFB loaded the
                    # pre-staged world: these records are now current and own
                    # complete two-sided request IDs. Clear the reload flag
                    # so the guide goes straight to Play Game on arrival.
                    state["awaiting_reload"] = False
                    state.pop("prestage_records", None)
                    state.pop("boundary_recovery", None)
                    state.pop("force_boundary_recovery_records", None)
                    _native_boundary_snapshot_path().unlink(missing_ok=True)
                if write_rounds:
                    if native_staged:
                        needs_write = duplicate_user_request
                        if write and duplicate_user_request:
                            write_result = _apply_duplicate_user_request_fix(
                                user_rec_n, user_rows)
                            if write_result.get("written"):
                                notes.append(
                                    "CFB 27 created two Actions entries for "
                                    "the same playoff game. Dynasty+ removed "
                                    "the extra entry without changing the "
                                    "matchup or its participant requests.")
                        elif write:
                            write_result = {
                                "written": False,
                                "reason": "current native round already staged",
                                "report": [],
                            }
                        cpu_presims = sum(
                            1 for rnd in bracket.get("rounds") or []
                            if str(rnd["round"]) in ready
                            for game, rec in zip(
                                rnd["games"],
                                plan.get(str(rnd["round"])) or [])
                            if rec is not None and rec < len(store.games)
                            and game.get("status") != "final"
                            and not any(slot.get("team") in user_names
                                        for slot in game.get("slots") or [])
                            and store.games[rec].has_result
                            and not store.games[rec].official)
                        if cpu_presims:
                            notes.append(
                                f"The other {cpu_presims} playoff games in "
                                "this round are already simulated. Their "
                                "results become official in Dynasty+ after "
                                "you finish your game and advance the week.")
                    elif write:
                        if request_issue and ready_staged and prestage_staged:
                            round_order = bracket.get("rounds") or []
                            ready_positions = [
                                index for index, rnd in enumerate(round_order)
                                if str(rnd["round"]) in ready]
                            prior_records: set[int] = set()
                            if ready_positions and min(ready_positions) > 0:
                                prior = round_order[min(ready_positions) - 1]
                                prior_records = {
                                    record for record in
                                    (plan.get(str(prior["round"])) or [])
                                    if record is not None}
                            recovery = _native_boundary_recovery_base(
                                state, payload, store, request_issue,
                                prior_records)
                            if recovery is not None:
                                write_result = _apply_to_save(
                                    bracket, plan, regen_bowls=True,
                                    base_raw=recovery["raw"],
                                    user_rows=user_rows if user_here else None,
                                    pristine=False, only_rounds=write_rounds,
                                    keep_records=keep, neutralize=neutral,
                                    blank_records=blank, bowl_state=state)
                                if write_result.get("written"):
                                    state["boundary_recovery"] = {
                                        "records": request_issue,
                                        "source": recovery["source"],
                                        "prior_slate": recovery["slate"],
                                    }
                                    state["prestage_records"] = request_issue
                                    state.pop(
                                        "force_boundary_recovery_records", None)
                                    _capture_native_boundary_snapshot(
                                        request_issue)
                                    notes.append(
                                        "CFB 27 issued only one participant "
                                        "request for these games. Dynasty+ "
                                        "restored the prior bowl week with "
                                        "its completed results intact and "
                                        "staged both teams before the boundary.")
                            else:
                                write_result = {
                                    "written": False,
                                    "reason": ("no safe prior-week boundary "
                                               "snapshot is available"),
                                    "report": [],
                                }
                                state["boundary_recovery"] = {
                                    "records": request_issue,
                                    "blocked": True,
                                }
                                notes.append(
                                    "This matchup has only one engine-issued "
                                    "participant request. Do not play it again; "
                                    "no safe prior-week recovery snapshot was "
                                    "found for this dynasty.")
                        else:
                            write_result = _apply_to_save(
                                bracket, plan, regen_bowls=True,
                                base_raw=base_raw_n,
                                user_rows=user_rows if user_here else None,
                                pristine=pristine_n,
                                only_rounds=write_rounds,
                                keep_records=keep, neutralize=neutral,
                                blank_records=blank, bowl_state=state)
                            if write_result.get("written") and prestage:
                                state["prestage_records"] = prestage_records
                                _capture_native_boundary_snapshot(
                                    prestage_records)
                        if not write_result.get("written") \
                                and user_rec_n is not None \
                                and savesched.user_pending_fix_due(
                                    payload, user_rec_n, user_rows):
                            # the queue's second step (the +40 RequestId) when
                            # the round itself is already staged
                            write_result = _apply_user_fix(user_rec_n, user_rows)
                            if write_result.get("written"):
                                notes.append(
                                    "The user schedule row is updated. Reload the "
                                    "dynasty, open Actions, and play the scheduled "
                                    "matchup.")
                        elif locked_now and user_here and not bridge \
                                and write_result.get("written") \
                                and savesched.user_pending_game(payload) != user_rec_n:
                            notes.append(
                                "CFB 27 had already locked this week before "
                                "the update, so your own game cannot be "
                                "offered for play this round; it is simmed "
                                "when you advance. For the next round, press "
                                "Update Dynasty File right after arriving at "
                                "its week, before loading the dynasty.")
                        if bridge and write_result.get("written"):
                            # The last rewind is complete. Later syncs advance
                            # forward; the base remains recovery-only.
                            state["handoff"] = True
                    else:
                        # Never let awaiting_reload suppress this probe. A
                        # later plan repair can change which native record owns
                        # the user's game while that old flag is still set. The
                        # SMU quarterfinal then had Michigan in record 928,
                        # Actions wired to record 931, and the stale flag told
                        # the user to load forever. native_staged above is the
                        # authoritative proof that a successful write is still
                        # present; anything else must be probed and repaired.
                        probe = _apply_to_save(
                            bracket, plan, regen_bowls=True,
                            base_raw=base_raw_n,
                            user_rows=user_rows if user_here else None,
                            pristine=pristine_n, only_rounds=write_rounds,
                            keep_records=keep, neutralize=neutral,
                            blank_records=blank, dry_run=True,
                            bowl_state=state)
                        needs_write = bool(request_issue
                                           or probe.get("would_write"))
                        if duplicate_user_request:
                            needs_write = True
                        if not needs_write and user_rec_n is not None and \
                                savesched.user_pending_fix_due(payload,
                                                               user_rec_n,
                                                               user_rows):
                            needs_write = True
                elif any(g_.get("status") != "final"
                         for rnd in bracket.get("rounds") or []
                         for g_ in rnd["games"]):
                    notes.append(
                        "The next playoff round is on a later bowl week. In "
                        "CFB 27, play or sim the current week as normal (any "
                        "of the game's own playoff games this week do not "
                        "count toward your bracket), advance to the next "
                        "bowl week, then exit to the main menu and press "
                        "Update Dynasty File.")
            elif write:
                write_result = _apply_to_save(
                    bracket, plan, regen_bowls=True,
                    user_rows=user_rows if user_in_field else None,
                    bowl_state=state)
            else:
                # capture-only sync (the poll / saves watcher): probe whether
                # an explicit apply would change the save, so the UI can show
                # the "update your dynasty file" action
                probe = _apply_to_save(
                    bracket, plan, regen_bowls=True,
                    user_rows=user_rows if user_in_field else None,
                    dry_run=True, bowl_state=state)
                needs_write = bool(probe.get("would_write"))
        restore_pending_g = False
        engrave_state_g: str | None = ("done" if state.get("engrave_written")
                                       else None)
        if bracket.get("champion"):
            # RESTORE THE ENGINE'S CLEAN POSTSEASON on completion. A pure-cycle
            # playoff leaves the save's bowl/CFP records full of custom
            # matchups, relabeled bowls, and double-booked teams, which FREEZE
            # the engine on the next advance. Hand the game back its own
            # untouched postseason (the base snapshot) so the user can play or
            # sim the rest of the bowl weeks normally; the custom results live
            # in Playoff History. A calendar-tail run already rode the real
            # weeks, so it is left as-is. A HYBRID is exempt too: its endgame
            # played forward on the game's own records (nothing to restore),
            # its retained base is recovery-only and is removed at completion.
            restore_due = (cycling and not hybrid and not state.get("tail")
                           and not state.get("postseason_restored")
                           and (_snapshot_path().exists()
                                or _restore_snapshot_path().exists()))
            restored_now = False
            if restore_due and write:
                r = _restore_base_to_save()
                if r.get("written"):
                    state["postseason_restored"] = True
                    restored_now = True
                    notes.append(
                        "The custom playoff is complete and saved to Playoff "
                        "History. Your dynasty has been handed back the game's "
                        "own bowl slate for the rest of the postseason: reload "
                        "in CFB 27, then play or sim the remaining bowl weeks to "
                        "finish your season.")
            elif restore_due and not write:
                needs_write = True  # prompt Update, which runs the restore
                # shown on EVERY capture while the restore is pending: hiding
                # it after the first poll left the button unexplained and the
                # old guide text ("continue as normal") pointed at the exact
                # action that freezes the engine
                notes.append(
                    "The custom playoff is complete. Press Update Dynasty "
                    "File once more to hand the game back its own postseason, "
                    "then reload and finish your season.")
            restore_pending_g = restore_due and not state.get("postseason_restored")
            # ENGRAVE the user's real playoff run onto their season schedule.
            # A pure cycle does this after restoring and simming the engine's
            # throwaway postseason. A hybrid already rode the native endgame,
            # so an eliminated user's ordinary bowl can be engraved as soon as
            # the championship completes. One explicit final update rewrites
            # the OFFICIAL records that hold the user (their bowl or CFP path,
            # 1-4 slots) with the custom matchups, sites, and scores.
            if restored_now:
                # the restore JUST replaced the save; `store` still reflects
                # the pre-restore wave world, so the ready/target gates below
                # would misread (observed: the pinned record counted as an
                # engrave target, the fresh clean base then had none, and the
                # engrave marked itself hopeless in the same Update as the
                # restore, silently skipping the whole finish flow). The user
                # must play the cosmetic weeks first anyway: just point the
                # guide there and re-evaluate on later syncs.
                engrave_state_g = "advance" if user_in_field else None
            elif (cycling and not state.get("tail")
                    and (state.get("postseason_restored") or hybrid)
                    and not state.get("engraved") and user_in_field):
                user_games_f = _user_final_games(bracket, user_names)
                if not user_games_f:
                    state["engraved"] = True  # user's games were simmed: nothing to show
                elif not _engrave_ready(store, user_rows):
                    engrave_state_g = "advance"
                elif not _engrave_targets(store, user_rows):
                    engrave_state_g = "advance"  # no official record holds the
                    # user YET (mid-cosmetic-weeks); re-probe on later syncs
                elif write:
                    r = _engrave_user_games(bracket, user_names)
                    if r.get("written"):
                        state["engraved"] = True
                        state["engrave_written"] = True
                        engrave_state_g = "done"
                        kept = min(len(user_games_f), r["games"])
                        notes.append(
                            f"Your playoff run is on your season schedule: the "
                            f"last {kept} of your {len(user_games_f)} playoff "
                            "games now replace the cosmetic results (the save "
                            "has room for as many games as the engine gave "
                            "you). Reload in CFB 27 to see them.")
                    # a failed write is NOT terminal (the save may simply not
                    # be there yet): leave engraved unset so the gates
                    # re-evaluate against the next capture
                elif not write:
                    engrave_state_g = "ready"
                    needs_write = True
                    notes.append(
                        "One more Update Dynasty File writes your real playoff "
                        "games onto your season schedule, replacing the "
                        "cosmetic bowl results the engine simmed.")
            state["status"] = "complete"
            state["awaiting_reload"] = False
            # keep the base snapshot until the clean-postseason restore is done
            # (or is not applicable); dropping it early would strand the restore
            if hybrid or not (cycling and not state.get("tail")) \
                    or state.get("postseason_restored"):
                _snapshot_path().unlink(missing_ok=True)
                _restore_snapshot_path().unlink(missing_ok=True)
                _native_boundary_snapshot_path().unlink(missing_ok=True)
            # write history once per completed run (not on every 30s poll,
            # which churned completed_at forever); a same-season re-run with
            # a different champion still replaces the entry
            prev_entry = next((r for r in history()
                               if r.get("year") == season_year), None)
            if prev_entry is None \
                    or prev_entry.get("champion") != bracket["champion"]:
                _append_history({
                    "year": season_year,
                    "format_teams": (state.get("format") or fmt).get("teams"),
                    "champion": bracket["champion"],
                    "bracket": bracket,
                    "completed_at": datetime.now().isoformat(timespec="seconds"),
                })
        elif plan and any(
                g.get("status") == "final"
                for rnd in bracket.get("rounds") or [] for g in rnd["games"]):
            state["status"] = "in_progress"
        if write_result and write_result.get("written") and state["status"] != "complete":
            state["awaiting_reload"] = True
            state["wave_format"] = _WAVE_FORMAT
        state["bracket"] = bracket
        _save_state(state)
        # The user can play while they are in the field and still alive. Their
        # engine-selected postseason destination no longer gates this: format 10
        # writes the custom matchup and its user request in Bowl Week 1 so the
        # Actions tab exposes Play Game directly.
        # Once eliminated, their last result stands and the rest of the bracket
        # sims without promising another matchup.
        user_alive_out = user_in_field and not any(
            g_.get("winner") and g_["winner"] not in user_names
            for rnd in bracket.get("rounds") or [] for g_ in rnd["games"]
            if any(s.get("team") in user_names for s in g_["slots"]))
        user_can_play = user_in_field and user_alive_out
        out = {
            "available": True,
            "status": state["status"],
            "bracket": bracket,
            "in_game": bool(state.get("in_game")),
            "mode": state.get("mode"),
            "awaiting_reload": bool(state.get("awaiting_reload")),
            "needs_write": needs_write,
            "notes": notes,
            "guide": _build_guide(
                status=state["status"], mode=state.get("mode"), bracket=bracket,
                plan=plan, store=store, user_names=user_names,
                needs_write=needs_write,
                awaiting_reload=bool(state.get("awaiting_reload")),
                slate_len=len(state.get("slate_records") or []) or None,
                prepared=bool(state.get("rank_swap") or state.get("result_flips")),
                anchor_pending=advance_prompt,
                calendar_rounds=calendar_keys,
                tail_ready_rounds=calendar_ready,
                user_present=user_can_play,
                user_native=True,
                restore_pending=restore_pending_g,
                engrave_state=engrave_state_g,
                # a hybrid bracket's endgame rounds render with the native
                # forward-calendar steps; its earlier rounds stay cycle-style
                native_rounds=cycle_native_tail,
                boundary_recovery=state.get("boundary_recovery"),
                legacy_native_cache_recovery=legacy_native_cache_recovery),
        }
        if write_result and write_result.get("written"):
            out["save_written"] = True
            out["written_games"] = write_result.get("games")
            recovering_boundary = bool(state.get("boundary_recovery"))
            hint = (" Reload the dynasty, open Actions, and play the scheduled "
                    "matchup."
                    if state.get("mode") == "cycle" and write_result.get("games")
                    and not recovering_boundary
                    else "")
            if rewound:
                out["rewound"] = True
                out["notes"] = list(out["notes"]) + [
                    "The next wave of playoff games is ready: the dynasty was "
                    "rewound to the playoff week with new matchups. Reload your "
                    "dynasty in CFB 27 (exit to the main menu and load it again) "
                    "to play them." + hint]
            else:
                message = (
                    "The prior bowl week is restored and the next round is "
                    "staged. Load the dynasty, advance one bowl week, then "
                    "exit to the main menu and update again."
                    if recovering_boundary else
                    "Playoff matchups were written into the save. If the dynasty is "
                    "open in CFB 27, reload it in game to pick them up." + hint)
                out["notes"] = list(out["notes"]) + [message]
        return out
    except playoff.BracketError as exc:
        return {"available": False, "status": "invalid", "problems": [str(exc)]}
