"""The poll editor: hand any of the save's national polls to the user.

An editor tool (ships in BOTH apps; routes stay ungated). The save keeps its
polls as full per-team orderings in the TeamStore (backend/saveparse/polls.py):
the CFP committee ranking (which drives the engine's playoff selection and
seeding, and is available from week 1 even though the game only unveils it
late in the season) and the AP-style media poll. Each poll runs in one of
three modes, per dynasty:

  game        the engine owns it (default): never touched.
  manual      the user's hand ordering. Stored as an ordered head list of
              team names; everything below the head keeps the engine's
              relative order.
  algorithm   a computer rating (backend/rankings.py) recomputed from the
              season's official results on every application.

AUTO-PUSH: the user never has to push a poll by hand. The playoff autosync
watcher (backend/playoff_live.py) calls auto_apply() whenever
CFB 27 writes a dynasty save; any poll not in 'game' mode is recomputed and,
if the save disagrees, written back in place through the conference editor's
proven flow (backup once, patch, verify by re-parse, re-encode). The engine's
weekly recompute anchors on the prior ranks it loads, so a written poll also
bends the engine's own next poll. While the game session is running the
engine's next autosave overwrites the write from memory; the watcher then
simply re-applies, so the save on disk always converges to the user's poll
and the game reads it on the next dynasty load.

GUARD: the custom playoff automation plants a committee-rank swap at
championship week and owns the postseason ranks while a bracket is live
(see playoff_live). Committee writes hold (with a reason the UI shows)
whenever the live playoff is beyond projection or a prepare swap is planted;
the AP poll is flavor only and never held.

State lives at data/dynasties/<id>/polls/editor.json.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from . import confsetup, dynasty_paths, rankings
from .saveparse import container
from .saveparse import polls as savepolls
from .saveparse import schedule as savesched
from .saveparse import teams as saveteams

_MODES = ("game", "manual", "algorithm")

# poll key -> UI label; the committee poll is listed first because it is the
# one the engine's selection actually reads.
POLL_LABELS = {"cfp": "CFP Committee Rankings", "ap": "AP Top 25"}


def _state_path():
    return dynasty_paths.sub("polls") / "editor.json"


def _default_poll() -> dict[str, Any]:
    return {"mode": "game", "algorithm": "colley", "manual": []}


def _default_config() -> dict[str, Any]:
    return {"polls": {p: _default_poll() for p in savepolls.POLLS},
            "auto_apply": True, "last_applied": None}


def get_config() -> dict[str, Any]:
    cfg = _default_config()
    try:
        raw = json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return cfg
    for p in savepolls.POLLS:
        saved = (raw.get("polls") or {}).get(p) or {}
        if saved.get("mode") in _MODES:
            cfg["polls"][p]["mode"] = saved["mode"]
        if saved.get("algorithm") in rankings.ALGORITHMS:
            cfg["polls"][p]["algorithm"] = saved["algorithm"]
        manual = saved.get("manual")
        if isinstance(manual, list):
            cfg["polls"][p]["manual"] = [str(n) for n in manual if n]
    if isinstance(raw.get("auto_apply"), bool):
        cfg["auto_apply"] = raw["auto_apply"]
    if isinstance(raw.get("last_applied"), dict):
        cfg["last_applied"] = raw["last_applied"]
    return cfg


def _save_config(cfg: dict[str, Any]) -> None:
    _state_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def set_config(body: dict[str, Any]) -> dict[str, Any]:
    """Merge a config update from the UI (validated), save, and return it."""
    cfg = get_config()
    polls = body.get("polls") or {}
    for p in savepolls.POLLS:
        upd = polls.get(p)
        if not isinstance(upd, dict):
            continue
        mode = upd.get("mode")
        if mode is not None:
            if mode not in _MODES:
                raise ValueError(f"unknown poll mode: {mode!r}")
            cfg["polls"][p]["mode"] = mode
        algo = upd.get("algorithm")
        if algo is not None:
            if algo not in rankings.ALGORITHMS:
                raise ValueError(f"unknown ranking algorithm: {algo!r}")
            cfg["polls"][p]["algorithm"] = algo
        manual = upd.get("manual")
        if manual is not None:
            if not isinstance(manual, list):
                raise ValueError("manual order must be a list of team names")
            names = [str(n) for n in manual if n]
            if len(names) != len(set(names)):
                raise ValueError("manual order lists a team twice")
            cfg["polls"][p]["manual"] = names
    if isinstance(body.get("auto_apply"), bool):
        cfg["auto_apply"] = body["auto_apply"]
    _save_config(cfg)
    return cfg


# ---------------------------------------------------------------------------
# reading the save
# ---------------------------------------------------------------------------

def _official_games(store: savesched.GameStore) -> list[rankings.GameResult]:
    """The season's official results in play order, ready for the raters.
    Pre-simmed and unpublished scores stay out (no spoilers, same rule as
    every other reader); bowls and neutral-site games are flagged neutral."""
    done = [g for g in store.games
            if g.scheduled and g.has_result and g.official
            and g.winner_row is not None]
    done.sort(key=lambda g: g.result_slot if g.result_slot is not None else 1 << 30)
    return [rankings.GameResult(
        home=g.home_row, away=g.away_row,
        home_score=g.home_score, away_score=g.away_score,
        neutral=g.bowl_row is not None or g.venue_uid is not None)
        for g in done]


def _identity_map() -> dict[str, dict[str, Any]]:
    """team name -> the identity the rest of the app renders (espn_id, logo,
    color), from the dynasty's own all_teams. The league seed resolves the
    espn id even when the save's team name does not match the ESPN directory
    key (SMU, TCU, Texas Tech, South Carolina, ...), so poll logos match the
    playoff and home pages instead of falling back to a monogram. Empty when
    the dynasty cannot be loaded (mock/dev)."""
    from . import pipeline  # lazy: pipeline pulls in the module registry
    try:
        ptr = pipeline.current_pointer()
        dyn = pipeline.load_dynasty(ptr.get("year"), ptr.get("week"))
    except Exception:  # noqa: BLE001 - logos are best-effort flavor
        return {}
    return {row["name"]: row for row in (dyn.get("all_teams") or [])
            if row.get("name")}


def _poll_entries(payload: bytes, roster: list[saveteams.Team],
                  records: dict[int, tuple[int, int]], poll: str,
                  directory: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for rank, row in enumerate(savepolls.poll_order(payload, poll), start=1):
        if row >= len(roster):
            continue
        t = roster[row]
        w, l = records.get(row, (0, 0))
        rec = directory.get(t.name) or {}
        out.append({"rank": rank, "row": row, "team": t.name,
                    "school": t.school, "abbr": t.abbreviation,
                    "record": f"{w}-{l}",
                    "conference": rec.get("conference"),
                    "espn_id": rec.get("espn_id"),
                    "logo": rec.get("logo"),
                    "color": rec.get("color")})
    return out


def _human_orders(payload: bytes, poll: str) -> list[list[int]]:
    """The poll orderings the BCS formula treats as the human vote: every
    OTHER poll the save carries (the one being written is excluded so a
    weekly re-apply never feeds a poll its own last output). Empty orderings
    are dropped by the rater."""
    return [savepolls.poll_order(payload, other)
            for other in savepolls.POLLS if other != poll]


def _records(store: savesched.GameStore) -> dict[int, tuple[int, int]]:
    recs: dict[int, tuple[int, int]] = {}
    for g in store.games:
        if not (g.scheduled and g.has_result and g.official):
            continue
        w, l = g.winner_row, g.loser_row
        if w is None:
            continue
        recs[w] = (recs.get(w, (0, 0))[0] + 1, recs.get(w, (0, 0))[1])
        recs[l] = (recs.get(l, (0, 0))[0], recs.get(l, (0, 0))[1] + 1)
    return recs


def _playoff_hold() -> str | None:
    """Why committee writes must currently keep their hands off the ranks
    (None = free). The custom playoff automation owns the committee ranking
    from its championship-week prepare through a live bracket.

    The hold exists ONLY to protect that AUTOMATIC route-forward, so it lifts
    entirely when the user has turned auto-sync off: they have opted out of the
    automation and are driving by hand, and their custom rankings are then
    authoritative (they write straight to the save's committee field, which the
    engine reads for the real CFP and the custom bracket seeds from)."""
    from . import app_settings
    if not app_settings.autosync_enabled():
        return None
    from . import playoff_live  # lazy: playoff_live also imports this module
    # With the custom playoff automation OFF (the opt-in default), the game runs
    # its native bracket and the user's custom rankings are exactly how they
    # shape its seeding, so nothing holds the committee field back.
    if not playoff_live.is_enabled():
        return None
    state = playoff_live._load_state()
    status = state.get("status")
    # "selected" is intentionally NOT held: until a bracket game goes final
    # the playoff sync re-seeds the frozen field from the committee ranking
    # on every pass, so editing the poll at bowl week is exactly how the user
    # shapes the final field (the requested pre-playoff edit window). Only a
    # bracket with recorded results owns the ranks.
    if status == "in_progress":
        return ("the custom playoff bracket is under way; the committee "
                "ranking is under playoff control until the season completes")
    if status == "selected" and any(
            g.get("status") == "final"
            for rnd in (state.get("bracket") or {}).get("rounds") or []
            for g in rnd["games"]):
        return ("the custom playoff bracket is under way; the committee "
                "ranking is under playoff control until the season completes")
    if state.get("rank_swap"):
        return ("the custom playoff's championship-week prepare is planted "
                "in the save; committee edits resume after selection")
    return None


def _native_seal_notice(payload: bytes) -> str | None:
    """A non-blocking heads-up for committee edits while the game runs its
    OWN playoff (custom automation off), or None when it does not apply.

    The engine seeds its native bracket exactly once, at the conference-
    championship-to-bowl-week boundary, by writing actual team refs into the
    stock first-round records; after that it never re-reads the committee
    ranking for bracket STRUCTURE, only for the seed labels painted on the
    bracket screen (verified on a tester's saves: a bowl-week push moved
    BYU/SMU to 11/12 on every tile, but they kept their byes and played the
    quarterfinals). So once those records are seeded, a push still writes
    fine but can no longer reshape the field, and the editor should say so.
    With the automation ON this never fires: the selection window re-seeds
    the custom bracket from the poll, and the playoff hold covers the rest.
    """
    from . import playoff_live  # lazy: playoff_live also imports this module
    if playoff_live.is_enabled():
        return None
    try:
        first_round = playoff_live._postseason_slots(payload).get(
            "first_round") or []
        if not first_round:
            return None
        store = savesched.parse(payload)
        if not any(store.games[r].scheduled for r in first_round
                   if 0 <= r < store.count):
            return None
    except Exception:  # noqa: BLE001 - the notice is best-effort flavor
        return None
    return ("the game has already set its own playoff bracket, so a "
            "committee push from here only relabels the seed numbers shown "
            "next to each team. The matchups and byes stay as the game "
            "selected them. To reshape the field, edit the ranking before "
            "advancing past conference championship week, or turn on the "
            "custom playoff and Dynasty+ will rewrite the bracket for you.")


def desired_rows(poll: str, cfg: dict[str, Any] | None = None,
                 payload: bytes | None = None) -> list[int] | None:
    """The full team-row ordering this poll SHOULD carry under the user's
    config, or None when the engine owns it (mode 'game', or no save)."""
    cfg = cfg or get_config()
    pc = cfg["polls"][poll]
    if pc["mode"] == "game":
        return None
    payload = payload if payload is not None else confsetup.current_payload()
    if payload is None:
        return None
    prior = savepolls.poll_order(payload, poll)
    if not prior:
        return None
    if pc["mode"] == "manual":
        roster = saveteams.parse_teams(payload)
        row_of = {t.name: i for i, t in enumerate(roster)}
        prior_set = set(prior)
        head = [row_of[n] for n in pc["manual"]
                if n in row_of and row_of[n] in prior_set]
        head_set = set(head)
        return head + [r for r in prior if r not in head_set]
    store = savesched.parse(payload)
    return rankings.compute(pc["algorithm"], _official_games(store), prior,
                            {"human_orders": _human_orders(payload, poll)})


# ---------------------------------------------------------------------------
# the API surface
# ---------------------------------------------------------------------------

def get_state() -> dict[str, Any]:
    """Everything the poll editor page renders: the save's current polls, the
    user's config, the algorithm catalog, and the auto-push status."""
    from . import playoff_live  # lazy (import cycle; also reused for watcher info)
    cfg = get_config()
    out: dict[str, Any] = {
        "available": False,
        "config": cfg,
        "poll_labels": POLL_LABELS,
        "algorithms": [{"id": k, **v} for k, v in rankings.ALGORITHMS.items()],
        "autosync": playoff_live.autosync_info(),
    }
    payload = confsetup.current_payload()
    if payload is None:
        out["reason"] = "No CFB 27 save is readable for this dynasty."
        return out
    try:
        roster = saveteams.parse_teams(payload)
        store = savesched.parse(payload)
        records = _records(store)
        directory = _identity_map()
        polls = {p: _poll_entries(payload, roster, records, p, directory)
                 for p in savepolls.POLLS}
    except ValueError as exc:
        out["reason"] = f"The save's poll structures did not parse: {exc}"
        return out
    out["available"] = True
    out["polls"] = polls
    out["games_played"] = sum(1 for g in store.games
                              if g.scheduled and g.has_result and g.official)
    hold = _playoff_hold()
    out["holds"] = {"cfp": hold, "ap": None}
    # only the committee ranking shapes a bracket, so only it gets the
    # native-bracket-already-seeded notice (see _native_seal_notice)
    out["notices"] = {"cfp": _native_seal_notice(payload), "ap": None}
    # what auto-push WOULD do right now, so the page can show pending drift
    # without writing anything, plus the EFFECTIVE ordering each poll resolves
    # to under the user's config (manual head / algorithm). The rankings grid
    # renders `effective` so a just-edited poll shows the user's order straight
    # away, even before the auto-push has rewritten the save on disk (and even
    # when a playoff hold defers the committee write).
    pending: dict[str, bool] = {}
    effective: dict[str, list[dict[str, Any]]] = {}
    for p in savepolls.POLLS:
        desired = desired_rows(p, cfg, payload)
        cur = savepolls.poll_order(payload, p)
        pending[p] = bool(desired) and desired != cur and not (
            p == "cfp" and hold)
        if desired:
            by_row = {e["row"]: e for e in polls[p]}
            eff = [{**by_row[r], "rank": i}
                   for i, r in enumerate(desired, start=1) if r in by_row]
            effective[p] = eff or polls[p]
        else:
            effective[p] = polls[p]
    out["pending"] = pending
    out["effective"] = effective
    return out


def preview(algorithm: str, poll: str = "cfp") -> dict[str, Any]:
    """Rank the current season with `algorithm` WITHOUT saving anything (the
    picker's live preview)."""
    if algorithm not in rankings.ALGORITHMS:
        raise ValueError(f"unknown ranking algorithm: {algorithm!r}")
    if poll not in savepolls.POLLS:
        raise ValueError(f"unknown poll: {poll!r}")
    payload = confsetup.current_payload()
    if payload is None:
        return {"available": False, "entries": []}
    roster = saveteams.parse_teams(payload)
    store = savesched.parse(payload)
    prior = savepolls.poll_order(payload, poll)
    order = rankings.compute(algorithm, _official_games(store), prior,
                             {"human_orders": _human_orders(payload, poll)})
    records = _records(store)
    directory = _identity_map()
    cur_rank = {row: i + 1 for i, row in enumerate(prior)}
    entries = []
    for rank, row in enumerate(order, start=1):
        if row >= len(roster):
            continue
        t = roster[row]
        w, l = records.get(row, (0, 0))
        rec = directory.get(t.name) or {}
        entries.append({"rank": rank, "row": row, "team": t.name,
                        "school": t.school, "abbr": t.abbreviation,
                        "record": f"{w}-{l}",
                        "espn_id": rec.get("espn_id"),
                        "logo": rec.get("logo"),
                        "color": rec.get("color"),
                        "delta": (cur_rank[row] - rank) if row in cur_rank else None})
    return {"available": True, "algorithm": algorithm, "entries": entries}


def apply(*, force: bool = False) -> dict[str, Any]:
    """Write every non-'game' poll into the save when it differs from the
    user's ranking. Serialized with the playoff sync (same cross-process
    lock): both writers patch the same save file."""
    from . import playoff_live  # lazy: shares its save-write serialization
    with playoff_live._cross_process_lock():
        return _apply_locked(force=force)


def _apply_locked(*, force: bool) -> dict[str, Any]:
    cfg = get_config()
    active = [p for p in savepolls.POLLS if cfg["polls"][p]["mode"] != "game"]
    if not active:
        return {"available": True, "written": False, "changed": {},
                "reason": "every poll is in game mode"}
    ctx = confsetup._read_table()
    if ctx is None:
        return {"available": False, "written": False, "changed": {},
                "reason": "no readable save"}
    payload = bytearray(ctx["payload"])
    hold = _playoff_hold()
    changed: dict[str, bool] = {}
    held: dict[str, str] = {}
    report: list[str] = []
    for p in active:
        if p == "cfp" and hold and not force:
            held[p] = hold
            continue
        desired = desired_rows(p, cfg, bytes(payload))
        if not desired:
            continue
        current = savepolls.poll_order(bytes(payload), p)
        if desired == current:
            changed[p] = False
            continue
        report.extend(savepolls.set_poll_order(payload, desired, p))
        changed[p] = True
    if not any(changed.values()):
        return {"available": True, "written": False, "changed": changed,
                "held": held, "report": report}
    # verify the patch still parses before touching disk (the same discipline
    # as every other save writer)
    for p in savepolls.POLLS:
        savepolls.poll_order(bytes(payload), p)
    savesched.parse(bytes(payload))
    confsetup._backup_once(ctx["path"])
    out = container.encode(ctx["raw"], bytes(payload), saved_at=datetime.now())
    ctx["path"].write_bytes(out)
    confsetup._table_cache.clear()
    cfg["last_applied"] = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "save": ctx["path"].name,
        "polls": [p for p, c in changed.items() if c],
    }
    _save_config(cfg)
    return {"available": True, "written": True, "changed": changed,
            "held": held, "report": report, "save": ctx["path"].name}


def auto_apply() -> dict[str, Any] | None:
    """The watcher hook: re-assert the user's polls after the game writes a
    save. No-op (returns None) when the global auto-sync switch is off, when
    this dynasty's auto-push is off, or when every poll is the engine's."""
    from . import app_settings
    if not app_settings.autosync_enabled():
        return None
    cfg = get_config()
    if not cfg.get("auto_apply"):
        return None
    if all(pc["mode"] == "game" for pc in cfg["polls"].values()):
        return None
    return apply()
