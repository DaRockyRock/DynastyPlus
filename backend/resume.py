"""Team resumes and the national scoreboard, straight from the save.

An editor-tool data surface:
no fabrication, only what the SeasonGameStore and the TeamStore rank
fields already contain. Powers the rankings hub's team cards, the click-through
resume view (the teams a program beat and lost to, with their records and
current ranks), the side-by-side resume comparison, and the week's scoreboard.

Spoiler rule (same as every other reader): only OFFICIAL results are surfaced.
The engine pre-sims the current week's games when the week begins, so a
not-yet-official score exists in the save; leaking it would spoil the user's
own week. Pre-simmed games appear as 'scheduled' with no score.

Ranks shown against a game are the opponent's CURRENT poll ranks. The save
keeps only the live per-team orderings (saveparse/polls.py), not a poll
history, so "beat #4 Miami" reads as "beat Miami, currently #4".
"""
from __future__ import annotations

from typing import Any

from . import confsetup, polledit
from .saveparse import bowls as savebowls
from .saveparse import polls as savepolls
from .saveparse import results as saveresults
from .saveparse import schedule as savesched
from .saveparse import teams as saveteams

# ---------------------------------------------------------------------------
# shared season context (parsed once per request)
# ---------------------------------------------------------------------------


class _Season:
    """Everything the resume/scoreboard builders read, parsed once."""

    def __init__(self, payload: bytes):
        self.payload = payload
        self.roster = saveteams.parse_teams(payload)
        self.store = savesched.parse(payload)
        self.ranks = {t.row: t for t in savepolls.parse(payload)}
        self.identity = polledit._identity_map()
        # row -> conference name (via the dynasty's own merged registry)
        self.conference = {}
        for row, t in enumerate(self.roster):
            ident = self.identity.get(t.name) or {}
            if ident.get("conference"):
                self.conference[row] = ident["conference"]
        self.records: dict[int, tuple[int, int]] = {}
        self.conf_records: dict[int, tuple[int, int]] = {}
        for g in self.official_games():
            w, l = g.winner_row, g.loser_row
            self.records[w] = (self.records.get(w, (0, 0))[0] + 1,
                               self.records.get(w, (0, 0))[1])
            self.records[l] = (self.records.get(l, (0, 0))[0],
                               self.records.get(l, (0, 0))[1] + 1)
            cw, cl = self.conference.get(g.away_row), self.conference.get(g.home_row)
            if cw and cw == cl and g.bowl_row is None:
                self.conf_records[w] = (self.conf_records.get(w, (0, 0))[0] + 1,
                                        self.conf_records.get(w, (0, 0))[1])
                self.conf_records[l] = (self.conf_records.get(l, (0, 0))[0],
                                        self.conf_records.get(l, (0, 0))[1] + 1)
        try:
            table = savebowls.parse(payload)
            self.bowl_names = {b.index: b.name for b in table.bowls}
            self.bowl_names.update({pb.index: pb.name for pb in table.playoff})
        except (ValueError, AttributeError):
            self.bowl_names = {}
        self.ccgs = saveresults.conference_championships(self.store, self.conference)

    def official_games(self) -> list[savesched.Game]:
        return [g for g in self.store.games
                if g.scheduled and g.has_result and g.official
                and g.winner_row is not None]

    def team_bits(self, row: int | None) -> dict[str, Any]:
        """The identity block every game side / resume header renders."""
        if row is None or row >= len(self.roster):
            return {"row": None, "team": "TBD", "school": "TBD", "abbr": ""}
        t = self.roster[row]
        ident = self.identity.get(t.name) or {}
        w, l = self.records.get(row, (0, 0))
        cw, cl = self.conf_records.get(row, (0, 0))
        rk = self.ranks.get(row)
        return {
            "row": row,
            "team": t.name,
            "school": t.school,
            "abbr": t.abbreviation,
            "record": f"{w}-{l}",
            "conf_record": f"{cw}-{cl}",
            "conference": self.conference.get(row),
            "espn_id": ident.get("espn_id"),
            "logo": ident.get("logo"),
            "color": ident.get("color"),
            "cfp_rank": (rk.rank if rk and 1 <= rk.rank <= 25 else None),
            "ap_rank": (rk.ap_rank if rk and 1 <= rk.ap_rank <= 25 else None),
        }


def _user_row(season: _Season) -> int | None:
    """The user's team row, resolved through the loaded dynasty (best effort;
    the scoreboard only uses it to float the user's game)."""
    from . import pipeline  # lazy: pipeline pulls in the module registry
    try:
        ptr = pipeline.current_pointer()
        dyn = pipeline.load_dynasty(ptr.get("year"), ptr.get("week"))
        name = ((dyn.get("team") or {}).get("name") or "").strip()
    except Exception:  # noqa: BLE001 - flavor only
        return None
    return next((i for i, t in enumerate(season.roster) if t.name == name), None)


def _season() -> tuple[_Season | None, str | None]:
    payload = confsetup.current_payload()
    if payload is None:
        return None, "No CFB 27 save is readable for this dynasty."
    try:
        return _Season(payload), None
    except ValueError as exc:
        return None, f"The save's season structures did not parse: {exc}"


def _game_label(season: _Season, g: savesched.Game) -> str | None:
    """Bowl / playoff / CCG tag for a game, when the save names one."""
    if g.bowl_row is not None:
        return season.bowl_names.get(g.bowl_row) or "Bowl Game"
    if g.index in season.ccgs:
        conf = season.conference.get(g.home_row) or season.conference.get(g.away_row)
        return f"{conf} Championship" if conf else "Conference Championship"
    return None


# ---------------------------------------------------------------------------
# the team resume
# ---------------------------------------------------------------------------

def team_resume(row: int) -> dict[str, Any]:
    """One team's full season resume: every official result with the
    opponent's identity, record, and current ranks, plus the summary the
    resume header and the comparison view read."""
    season, reason = _season()
    if season is None:
        return {"available": False, "reason": reason}
    if not 0 <= row < len(season.roster):
        return {"available": False, "reason": f"team row {row} is out of range"}

    mine = [g for g in season.store.games
            if row in (g.away_row, g.home_row) and g.scheduled]
    played = [g for g in mine if g.has_result and g.official
              and g.winner_row is not None]
    played.sort(key=lambda g: g.result_slot if g.result_slot is not None else 1 << 30)
    # future matchups are known (the store holds the whole season) but carry
    # no reliable order; pre-simmed not-yet-official results stay hidden
    upcoming = [g for g in mine if not (g.has_result and g.official)]

    games: list[dict[str, Any]] = []
    pf = pa = 0
    streak_kind, streak_len = None, 0
    vs_top25 = [0, 0]
    home_rec, away_rec, neutral_rec = [0, 0], [0, 0], [0, 0]
    for i, g in enumerate(played, start=1):
        home = g.home_row == row
        opp = season.team_bits(g.away_row if home else g.home_row)
        us = g.home_score if home else g.away_score
        them = g.away_score if home else g.home_score
        won = g.winner_row == row
        neutral = g.venue_uid is not None or g.bowl_row is not None
        pf += us
        pa += them
        if streak_kind == ("W" if won else "L"):
            streak_len += 1
        else:
            streak_kind, streak_len = ("W" if won else "L"), 1
        if opp["cfp_rank"]:
            vs_top25[0 if won else 1] += 1
        side = neutral_rec if neutral else (home_rec if home else away_rec)
        side[0 if won else 1] += 1
        games.append({
            "n": i,
            "opponent": opp,
            "home": home,
            "neutral": neutral,
            "result": "W" if won else "L",
            "score": f"{us}-{them}",
            "margin": us - them,
            "conference_game": (g.bowl_row is None
                                and season.conference.get(g.away_row) is not None
                                and season.conference.get(g.away_row)
                                == season.conference.get(g.home_row)),
            "label": _game_label(season, g),
        })

    # quality ordering: ranked opponents first (best rank), then by the
    # opponent's current winning percentage
    def quality(entry: dict[str, Any]) -> tuple:
        opp = entry["opponent"]
        rank = opp["cfp_rank"] or 99
        w, l = (int(x) for x in (opp["record"] or "0-0").split("-"))
        return (rank, -(w / max(1, w + l)))

    wins = sorted((g for g in games if g["result"] == "W"), key=quality)
    losses = sorted((g for g in games if g["result"] == "L"),
                    key=quality, reverse=True)

    n = len(played)
    return {
        "available": True,
        "team": season.team_bits(row),
        "summary": {
            "points_for": pf,
            "points_against": pa,
            "ppg": round(pf / n, 1) if n else 0.0,
            "papg": round(pa / n, 1) if n else 0.0,
            "avg_margin": round((pf - pa) / n, 1) if n else 0.0,
            "streak": f"{streak_kind}{streak_len}" if streak_kind else None,
            "vs_top25": f"{vs_top25[0]}-{vs_top25[1]}",
            "home": f"{home_rec[0]}-{home_rec[1]}",
            "away": f"{away_rec[0]}-{away_rec[1]}",
            "neutral": f"{neutral_rec[0]}-{neutral_rec[1]}",
        },
        "games": games,
        "best_wins": wins[:3],
        "worst_losses": losses[:3],
        "upcoming": [{
            "opponent": season.team_bits(g.away_row if g.home_row == row else g.home_row),
            "home": g.home_row == row,
            "neutral": g.venue_uid is not None or g.bowl_row is not None,
            "label": _game_label(season, g),
        } for g in upcoming],
    }


# ---------------------------------------------------------------------------
# the scoreboard
# ---------------------------------------------------------------------------

def scoreboard(user_row: int | None = None) -> dict[str, Any]:
    """The week's slate plus the latest finals, league-wide.

    `slate` is the engine's own current-week queue (SeasonGameRequest): once
    the user advances past the week those games read final with scores;
    before that they are scheduled matchups with scores withheld. `recent`
    is every official final in reverse play order (the head of the list is
    the most recently completed week)."""
    season, reason = _season()
    if season is None:
        return {"available": False, "reason": reason}
    if user_row is None:
        user_row = _user_row(season)

    def entry(g: savesched.Game) -> dict[str, Any]:
        final = g.has_result and g.official and g.winner_row is not None
        return {
            "index": g.index,
            "away": season.team_bits(g.away_row),
            "home": season.team_bits(g.home_row),
            "away_score": g.away_score if final else None,
            "home_score": g.home_score if final else None,
            "status": "final" if final else "scheduled",
            "neutral": g.venue_uid is not None or g.bowl_row is not None,
            "conference_game": (g.bowl_row is None
                                and season.conference.get(g.away_row) is not None
                                and season.conference.get(g.away_row)
                                == season.conference.get(g.home_row)),
            "label": _game_label(season, g),
            "user": user_row is not None and user_row in (g.away_row, g.home_row),
        }

    by_index = {g.index: g for g in season.store.games}
    slate = [entry(by_index[i]) for i in savesched.week_slate(season.payload)
             if i in by_index and by_index[i].scheduled]
    # finals first, the user's game on top of its group
    slate.sort(key=lambda e: (e["status"] != "final", not e["user"]))

    done = season.official_games()
    done.sort(key=lambda g: g.result_slot if g.result_slot is not None else -1,
              reverse=True)
    slate_idx = {e["index"] for e in slate}
    recent = [entry(g) for g in done[:60] if g.index not in slate_idx]

    return {"available": True, "slate": slate, "recent": recent}
