"""Map parsed SeasonGameStore games onto the dynasty schema blocks.

Builds, from the real save: the user's `schedule.recent_results`, the
`conference_standings` of the user's conference, and `national.scoreboard`.
Only OFFICIAL results are surfaced (the engine pre-sims the current week's
games before the user advances; leaking those would spoil outcomes, so
pre-simmed scores stay out of every schema block).

Week numbers come from the schedule-calendar structures when the caller has
them (`week_of` maps record index -> display week); without a mapping, games
are ordered by their result-slot ids (allocated in play order) and week is
omitted rather than guessed.
"""
from __future__ import annotations

from typing import Any

from . import schedule as sched
from . import teams as saveteams


def _fmt_record(w: int, l: int) -> str:
    return f"{w}-{l}"


def conference_championships(store: sched.GameStore,
                             alignment: dict[int, str] | None = None,
                             expected: int = 10) -> set[int]:
    """Record indices of the conference championship games.

    CCGs live above the bowl block positionally (validated across every
    dynasty observed so far), but position alone is a fragile promise:
    record allocation is engine-owned and the regular season is known to
    span records on both sides of the block in some layouts. A candidate
    must therefore clear three tests (the extra two are DEFENSIVE, added
    2026-07-09; they change nothing on the validated layouts):

    1. POSITION: a no-bowl-ref record above every bowl-tagged record (CCG
       records are never in the bowl block).
    2. SEASON COMPLETE: CCGs cannot have been played until the regular
       season is essentially over, so until >=95% of the no-bowl schedule is
       official there are NO championships, whatever sits above the block.
    3. CHRONOLOGY: CCGs are the only no-bowl games played AFTER rivalry
       week, so only the last `expected` official no-bowl results by
       result-slot order qualify; an early-season game that happens to live
       above the bowl block is excluded by its early slot.

    Returns an empty set until CCG week is actually played."""
    max_bowl = max((g.index for g in store.games if g.bowl_row is not None),
                   default=-1)
    if max_bowl < 0:
        return set()
    season = [g for g in store.games if g.bowl_row is None and g.scheduled]
    done = [g for g in season if g.official and g.result_slot is not None]
    if not season or len(done) < 0.95 * len(season):
        return set()  # regular season not finished: no CCGs exist yet
    slots = sorted(g.result_slot for g in done)
    cutoff = slots[-expected] if len(slots) >= expected else 0
    out: set[int] = set()
    for g in done:
        if g.index <= max_bowl or g.result_slot < cutoff:
            continue
        if alignment:
            ca, ch = alignment.get(g.away_row), alignment.get(g.home_row)
            if ca and ch and ca != ch:
                continue
        out.add(g.index)
    return out


def rivalry_week_results(store: sched.GameStore,
                         alignment: dict[int, str] | None = None) -> dict[int, bool]:
    """team row -> True if the team LOST its rivalry-week game.

    Rivalry week is the final regular-season week. With no explicit week field
    in the save, it is derived from play order: excluding the conference
    championships, a team's rivalry-week game is its LAST regular-season game
    (result slots are allocated in play order). Only games that are the last
    game for BOTH participants (or whose opponent went on to a CCG) qualify,
    so a team idle in the final week is simply absent from the map. Empty
    until the regular season is complete."""
    ccgs = conference_championships(store, alignment)
    regular = [g for g in store.games
               if g.scheduled and g.official and g.bowl_row is None
               and g.index not in ccgs and g.result_slot is not None]
    if not regular:
        return {}
    last: dict[int, sched.Game] = {}
    for g in regular:
        for t in (g.away_row, g.home_row):
            if t is not None and (t not in last or g.result_slot > last[t].result_slot):
                last[t] = g
    out: dict[int, bool] = {}
    for t, g in last.items():
        opp = g.home_row if g.away_row == t else g.away_row
        if last.get(opp) is not g:
            continue  # opponent played later, so g was not the final week
        out[t] = g.loser_row == t
    return out


def build_blocks(payload: bytes, *, user_row: int | None,
                 alignment: dict[int, str] | None = None,
                 week_of: dict[int, int] | None = None,
                 current_week: int | None = None) -> dict[str, Any]:
    """Schema blocks derived from the save's own results.

    alignment: team row -> conference name (from conferences.parse + roster).
    Returns {"recent_results": [...], "conference_standings": [...],
             "scoreboard": [...], "team_records": {row: (w, l)}}.
    """
    roster = saveteams.parse_teams(payload)
    store = sched.parse(payload)
    week_of = week_of or {}

    def team_bits(row: int | None) -> dict[str, Any]:
        if row is None or row >= len(roster):
            return {"name": "TBD", "abbr": "", "school": "TBD"}
        t = roster[row]
        return {"name": t.name, "abbr": t.abbreviation, "school": t.school}

    # official W/L per team
    records: dict[int, list[int]] = {}
    for g in store.games:
        if not (g.scheduled and g.has_result and g.official):
            continue
        w, l = g.winner_row, g.loser_row
        if w is None:
            continue
        records.setdefault(w, [0, 0])[0] += 1
        records.setdefault(l, [0, 0])[1] += 1

    # conference records (both teams in the same conference)
    conf_records: dict[int, list[int]] = {}
    if alignment:
        for g in store.games:
            if not (g.scheduled and g.has_result and g.official):
                continue
            ca, ch = alignment.get(g.away_row), alignment.get(g.home_row)
            if not ca or ca != ch:
                continue
            w, l = g.winner_row, g.loser_row
            if w is None:
                continue
            conf_records.setdefault(w, [0, 0])[0] += 1
            conf_records.setdefault(l, [0, 0])[1] += 1

    out: dict[str, Any] = {"team_records": {r: tuple(v) for r, v in records.items()},
                           "conference_records": {r: tuple(v) for r, v in conf_records.items()},
                           "rivalry_week_lost": rivalry_week_results(store, alignment)}

    # crowned conference champions: conference -> the CCG winner's team row.
    # Empty until championship week is actually played (the CCG detector
    # returns nothing before then), so a projection keeps using standings.
    if alignment:
        champs: dict[str, int] = {}
        ccg_idx = conference_championships(store, alignment)
        for g in store.games:
            if g.index in ccg_idx and g.winner_row is not None:
                conf = alignment.get(g.winner_row)
                if conf:
                    champs[conf] = g.winner_row
        out["conference_champions"] = champs

    # the user's played games, newest last (week order when known)
    if user_row is not None:
        mine = [g for g in store.games
                if user_row in (g.away_row, g.home_row)
                and g.scheduled and g.has_result and g.official]
        mine.sort(key=lambda g: week_of.get(g.index, g.result_slot or g.index))
        results = []
        for g in mine:
            home = g.home_row == user_row
            opp = team_bits(g.away_row if home else g.home_row)
            us = g.home_score if home else g.away_score
            them = g.away_score if home else g.home_score
            row: dict[str, Any] = {
                "opponent": opp["school"],
                "opponent_abbr": opp["abbr"],
                "home": home,
                "result": "W" if us > them else "L",
                "score": f"{us}-{them}",
                "rank_matchup": None,
            }
            if g.index in week_of:
                row["week"] = week_of[g.index]
            results.append(row)
        out["recent_results"] = results

    # the user's conference standings
    if alignment and user_row is not None and alignment.get(user_row):
        conf = alignment[user_row]
        rows = [r for r, c in alignment.items() if c == conf and r < len(roster)]

        def sort_key(r: int):
            cw, cl = conf_records.get(r, (0, 0))
            ow, ol = records.get(r, (0, 0))
            pct = cw / max(1, cw + cl)
            return (-pct, -cw, -(ow / max(1, ow + ol)), roster[r].school)

        standings = []
        for r in sorted(rows, key=sort_key):
            cw, cl = conf_records.get(r, (0, 0))
            ow, ol = records.get(r, (0, 0))
            standings.append({
                # full team name: every selection surface (the playoff pool
                # dedupes by this string) uses full names; school stays for
                # short display
                "team": roster[r].name,
                "school": roster[r].school,
                "abbr": roster[r].abbreviation,
                "conf_record": _fmt_record(cw, cl),
                "overall": _fmt_record(ow, ol),
            })
        out["conference_standings"] = standings

    # scoreboard: current week's games when the calendar is known; otherwise
    # the most recently completed official games
    board_games: list[sched.Game]
    if week_of and current_week is not None:
        board_games = [g for g in store.games
                       if week_of.get(g.index) == current_week and g.scheduled]
    else:
        done = [g for g in store.games if g.scheduled and g.has_result and g.official]
        # result slots are allocated in PLAY order; record indices are structural
        # (a late-November game can sit at a low index), so sort by slot or the
        # "most recent finals" board resurfaces games from weeks ago.
        done.sort(key=lambda g: g.result_slot if g.result_slot is not None else -1)
        board_games = done[-30:]
        # A full FBS week outnumbers the window, so the user's newest final can
        # slip out; it is the one game the board must always carry.
        if user_row is not None:
            user_done = [g for g in done if user_row in (g.away_row, g.home_row)]
            if user_done and user_done[-1] not in board_games:
                board_games.append(user_done[-1])
    board = []
    for g in board_games:
        away, home = team_bits(g.away_row), team_bits(g.home_row)
        aw, al = records.get(g.away_row, (0, 0))
        hw, hl = records.get(g.home_row, (0, 0))
        entry: dict[str, Any] = {
            "home": {"name": home["school"], "abbr": home["abbr"], "record": _fmt_record(hw, hl), "rank": None},
            "away": {"name": away["school"], "abbr": away["abbr"], "record": _fmt_record(aw, al), "rank": None},
            "conference_game": bool(alignment and alignment.get(g.away_row)
                                    and alignment.get(g.away_row) == alignment.get(g.home_row)),
            "neutral": g.bowl_row is not None,
            "user": user_row in (g.away_row, g.home_row),
            "status": "final" if (g.has_result and g.official) else "scheduled",
            "home_score": g.home_score if g.official else None,
            "away_score": g.away_score if g.official else None,
        }
        if g.index in week_of:
            entry["week"] = week_of[g.index]
        board.append(entry)
    out["scoreboard"] = board
    return out
