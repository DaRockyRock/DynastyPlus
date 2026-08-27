"""Story candidate detection: every reportable thing that happened (or looms).

Each detector is a pure function over the save + the ratings store + the prior
week's archive snapshot, emitting StoryCandidates with the facts that story needs
(pre-formatted strings, never raw numbers the model would have to do math on) and
raw salience signals for the scorer. Candidate ids are deterministic hashes so
re-running a week reproduces the same slate and downstream dedup keys hold.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .. import dynasty_paths
from . import ratings
from .state import WorldState


@dataclass
class StoryCandidate:
    id: str
    type: str
    scope: str                    # "program" | "national"
    phase: str                    # "preview" | "reaction"
    subjects: list[str]
    facts: dict[str, Any]
    signals: dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    arc_id: str | None = None
    arc_note: str | None = None      # cross-week continuity note from the arc registry


def _cid(year: int, week: int, type_: str, subjects: list[str]) -> str:
    raw = f"{year}:{week}:{type_}:{'|'.join(sorted(subjects))}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _make(year: int, week: int, type_: str, scope: str, phase: str,
          subjects: list[str], facts: dict, **signals: float) -> StoryCandidate:
    return StoryCandidate(id=_cid(year, week, type_, subjects), type=type_, scope=scope,
                          phase=phase, subjects=subjects, facts=facts, signals=dict(signals))


def _prior_snapshot(year: int, week: int) -> dict | None:
    """Last week's full dynasty snapshot from the archive (poll movement and
    recruiting diffs are diffs against this). None in week 1."""
    if week <= 1:
        return None
    p = dynasty_paths.sub("archive") / str(year) / f"{week - 1}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _rank_label(rank: Any, name: str) -> str:
    return f"No. {rank} {name}" if rank else name


# --- reaction detectors (finals) -------------------------------------------
def _result_candidates(dynasty: dict, state: WorldState, year: int, week: int,
                       games: list[dict]) -> list[StoryCandidate]:
    out: list[StoryCandidate] = []
    for g in games:
        if int(g.get("week") or 0) != week:
            continue
        winner, loser = g["winner"], g["loser"]
        wr, lr = g.get("winner_rank"), g.get("loser_rank")
        surp = float(g.get("surprisal") or 0.0)
        facts = {
            "result": f"{_rank_label(wr, winner)} beat {_rank_label(lr, loser)} {g['score']}",
            "margin": f"{g['margin']}-point margin",
            "pregame": f"the winner had a {g['p_winner_pregame'] * 100:.0f} percent pre-game chance",
        }
        if g.get("user"):
            won = winner == state.team_name
            out.append(_make(year, week, "user_result", "program", "reaction",
                             [state.team_name, loser if won else winner], facts,
                             surprise=surp, magnitude=min(g["margin"] / 28.0, 1.0),
                             proximity=1.0, conflict=0.0 if won else 0.5,
                             goodness=1.0 if won else 0.0))
            continue
        upset = surp >= 1.5  # winner was under ~35 percent
        ranked_clash = bool(wr and lr)
        if upset:
            out.append(_make(year, week, "upset", "national", "reaction",
                             [winner, loser], facts,
                             surprise=surp, magnitude=min(g["margin"] / 28.0, 1.0),
                             eliteness=(1.0 if lr and lr <= 10 else 0.6 if lr else 0.2),
                             proximity=0.2, conflict=0.4))
        elif ranked_clash:
            out.append(_make(year, week, "ranked_clash", "national", "reaction",
                             [winner, loser], facts,
                             surprise=surp, magnitude=min(g["margin"] / 28.0, 1.0),
                             eliteness=max(0.0, (30 - (wr or 25) - (lr or 25)) / 30.0) + 0.5,
                             proximity=0.2))
        elif g["margin"] >= 28 and (wr or lr):
            out.append(_make(year, week, "blowout", "national", "reaction",
                             [winner, loser], facts,
                             surprise=surp, magnitude=1.0,
                             eliteness=0.5 if (wr and wr <= 10) else 0.3, proximity=0.15))
    return out


# --- poll movement (needs last week's snapshot) -----------------------------
def _poll_candidates(dynasty: dict, state: WorldState, year: int, week: int) -> list[StoryCandidate]:
    prior = _prior_snapshot(year, week)
    if not prior:
        return []
    now = {r.get("team"): r.get("rank") for r in ((dynasty.get("national") or {}).get("ap_top25") or [])}
    was = {r.get("team"): r.get("rank") for r in ((prior.get("national") or {}).get("ap_top25") or [])}
    out: list[StoryCandidate] = []
    # a new No. 1 is its own story
    new1 = next((t for t, r in now.items() if r == 1), None)
    old1 = next((t for t, r in was.items() if r == 1), None)
    if new1 and old1 and new1 != old1:
        out.append(_make(year, week, "new_number_one", "national", "reaction", [new1, old1],
                         {"change": f"{new1} takes over at No. 1 from {old1}"},
                         magnitude=1.0, eliteness=1.0, surprise=0.8, proximity=0.2))
    moves: list[tuple[str, int, int]] = []
    for team, r in now.items():
        if team in was and was[team] and r:
            moves.append((team, was[team], r))
        elif team and r and team not in was:
            moves.append((team, 26, r))           # entered the poll
    for team, prev, cur in moves:
        delta = prev - cur
        if abs(delta) < 4 and not (prev > 25 >= cur):
            continue
        verb = "climbs" if delta > 0 else "falls"
        out.append(_make(year, week, "poll_jump" if delta > 0 else "poll_fall",
                         "program" if team == state.team_name else "national", "reaction",
                         [team], {"move": f"{team} {verb} from No. {prev if prev <= 25 else 'unranked'} "
                                          f"to No. {cur}"},
                         magnitude=min(abs(delta) / 10.0, 1.0),
                         eliteness=max(0.0, (26 - cur) / 25.0),
                         proximity=1.0 if team == state.team_name else 0.2,
                         goodness=1.0 if delta > 0 else 0.0,
                         conflict=0.0 if delta > 0 else 0.4))
    return out


# --- previews ---------------------------------------------------------------
def _preview_candidates(dynasty: dict, state: WorldState, year: int, week: int) -> list[StoryCandidate]:
    out: list[StoryCandidate] = []
    up = state.next_game
    if up and up.get("opponent"):
        opp = up["opponent"]
        p = ratings.game_prob(year, dynasty, state.team_name, opp, a_home=bool(up.get("home")),
                              line=up.get("spread"), a_abbr=(dynasty.get("team") or {}).get("abbreviation"))
        facts = {"matchup": f"{state.team_name} {'host' if up.get('home') else 'travel to'} "
                            f"{_rank_label(up.get('opponent_rank'), opp)}",
                 "kickoff": f"{up.get('kickoff', 'Saturday')} on {up.get('tv', 'TV')}",
                 "spread": up.get("spread") or "no line posted",
                 "win_chance": f"{p * 100:.0f} percent win probability",
                 "opp_coach": (f"{opp} is coached by {up.get('opponent_coach')}"
                               if up.get("opponent_coach") else "")}
        out.append(_make(year, week, "next_game_preview", "program", "preview",
                         [state.team_name, opp], facts,
                         proximity=1.0, stakes=0.7 if state.rivalry_next else 0.45,
                         conflict=0.6 if state.rivalry_next else 0.2,
                         eliteness=0.6 if up.get("opponent_rank") else 0.2))
    # season-open: the title-race landscape is the national lead before any kickoff
    if state.season_open:
        ap = [x for x in ((dynasty.get("national") or {}).get("ap_top25") or []) if x.get("team")]
        if ap:
            tops = ap[:3]
            firsts = ap[0].get("first")
            facts = {"favorites": ", ".join(f"No. {x['rank']} {x['team']}" for x in tops),
                     "ballot": f"{ap[0]['team']} took {firsts} first-place votes" if firsts else "",
                     "note": "season opens this week; expectations only, no results exist yet"}
            out.append(_make(year, week, "title_race", "national", "preview",
                             [x["team"] for x in tops], facts,
                             eliteness=1.0, magnitude=0.7, stakes=0.6, proximity=0.2))
    # marquee national games this week: ranked vs ranked, closest expected margins first
    sb = [g for g in ((dynasty.get("national") or {}).get("scoreboard") or [])
          if g.get("status") == "scheduled" and not g.get("user")]
    marquee: list[tuple[float, dict]] = []
    for g in sb:
        hr = (g.get("home") or {}).get("rank")
        ar = (g.get("away") or {}).get("rank")
        if not (hr and ar):
            continue
        quality = (52 - hr - ar) / 50.0                       # both top-5 ~ 0.84
        parsed = ratings.parse_line(g.get("line"))
        closeness = 1.0 - min(abs(parsed[1]) / 21.0, 1.0) if parsed else 0.5
        marquee.append((quality * 0.6 + closeness * 0.4, g))
    marquee.sort(key=lambda x: -x[0])
    for q, g in marquee[:3]:
        home, away = g.get("home") or {}, g.get("away") or {}
        out.append(_make(year, week, "marquee_preview", "national", "preview",
                         [home.get("name"), away.get("name")],
                         {"matchup": f"{_rank_label(away.get('rank'), away.get('name'))} at "
                                     f"{_rank_label(home.get('rank'), home.get('name'))}",
                          "line": g.get("line") or "no line",
                          "note": "NOT PLAYED YET, preview only"},
                         eliteness=q, magnitude=q, proximity=0.2, stakes=q * 0.8))
    return out


# --- recruiting -------------------------------------------------------------
def _recruiting_candidates(dynasty: dict, state: WorldState, year: int, week: int) -> list[StoryCandidate]:
    out: list[StoryCandidate] = []
    rec = dynasty.get("recruiting") or {}
    prior = _prior_snapshot(year, week)
    prior_commits = {c.get("name") for c in ((prior or {}).get("recruiting") or {}).get("commits") or []}
    for c in rec.get("commits") or []:
        if c.get("name") and c["name"] not in prior_commits:
            out.append(_make(year, week, "commit", "program", "reaction", [c["name"]],
                             {"who": f"{c.get('stars')}-star {c.get('position')} {c['name']}",
                              "from": c.get("hometown") or "", "class_impact": "a new pledge"},
                             proximity=1.0, goodness=1.0,
                             eliteness=min((c.get("stars") or 3) / 5.0, 1.0),
                             magnitude=(c.get("stars") or 3) / 5.0))
    # the live battles: high-interest, high-star targets where the user leads or contends
    targets = sorted((t for t in rec.get("targets") or [] if t.get("name")),
                     key=lambda t: -(t.get("stars") or 0) * (t.get("interest") or 0))
    for t in targets[:3]:
        leading = t.get("leader") == state.team_name
        out.append(_make(year, week, "recruiting_battle", "program", state.phase, [t["name"]],
                         {"who": f"{t.get('stars')}-star {t.get('position')} {t['name']} "
                                 f"({t.get('hometown', '')})",
                          "status": f"UNCOMMITTED (still being recruited, has not signed); "
                                    f"interest {t.get('interest')}/100, "
                                    f"{'leader: ' + str(t.get('leader')) if t.get('leader') else 'no leader yet'}",
                          "prediction": f"projected to lean {t.get('predicted')}, not a done deal"
                                        if t.get("predicted") else ""},
                         proximity=1.0, eliteness=min((t.get("stars") or 3) / 5.0, 1.0),
                         goodness=0.6 if leading else 0.3,
                         stakes=0.5 if (t.get("stars") or 0) >= 4 else 0.3))
    return out


# --- the carousel watch (grounds national insider items) --------------------
def _carousel_candidates(dynasty: dict, state: WorldState, year: int, week: int) -> list[StoryCandidate]:
    if state.season_open:
        return []  # preseason hot-seat chatter stays out of the cascade entirely
    rows = []
    for team, c in (dynasty.get("coaches") or {}).items():
        if isinstance(c, dict) and not c.get("is_user") and (c.get("hot_seat") or 0) >= 60:
            rows.append((c.get("hot_seat", 0), team, c))
    rows.sort(reverse=True)
    out = []
    for heat, team, c in rows[:2]:
        out.append(_make(year, week, "hot_seat_watch", "national", state.phase,
                         [c.get("name"), team],
                         {"who": f"{c.get('name')} ({team}), year {c.get('tenure_years')}, "
                                 f"{c.get('record')}",
                          "heat": f"seat temperature {heat}/100, trend {c.get('trend', 'flat')}"},
                         conflict=0.7, eliteness=min((c.get("prestige") or 5) / 10.0, 1.0),
                         magnitude=heat / 100.0, proximity=0.15))
    return out


# --- evergreens (the off-week floor) ----------------------------------------
def _evergreen_candidates(dynasty: dict, state: WorldState, year: int, week: int) -> list[StoryCandidate]:
    """Filler program content for quiet weeks (a bye, or a stretch with no game and
    no recruiting movement) so the feed is never empty. Drawn from the roster and the
    season so far; rotated by week so it does not repeat. Low salience by design."""
    out: list[StoryCandidate] = []
    team = state.team_name
    players = (dynasty.get("roster") or {}).get("key_players") or []
    if players:
        p = players[week % len(players)]
        out.append(_make(year, week, "player_spotlight", "program", state.phase, [p.get("name")],
                         {"who": f"{p.get('position')} {p.get('name')} ({p.get('year', '')})",
                          "angle": f"a feature on where {p.get('name')} fits for {team} this season"},
                         proximity=1.0, goodness=0.4, eliteness=0.3, magnitude=0.2))
    groups = ["the offensive line", "the secondary", "the receiving corps", "the front seven",
              "special teams", "the quarterback room", "the running back room"]
    out.append(_make(year, week, "position_feature", "program", state.phase, [team],
                     {"focus": f"a position-group feature on {groups[week % len(groups)]} at {team}"},
                     proximity=1.0, goodness=0.3, magnitude=0.2))
    if not state.season_open:
        out.append(_make(year, week, "season_retrospective", "program", state.phase, [team],
                         {"standing": f"where {team} stands at {state.record[0]}-{state.record[1]}, "
                                      f"{state.games_remaining} games to play",
                          "angle": "a check-in on the season's arc so far"},
                         proximity=1.0, goodness=0.3, magnitude=0.25))
    return out


# --- entry point -------------------------------------------------------------
def detect(dynasty: dict, state: WorldState, year: int, week: int) -> list[StoryCandidate]:
    """The week's full candidate pool. Finals are folded into the ratings first
    (idempotent), so surprise signals are available to every detector."""
    games = ratings.process_week(year, week, dynasty)
    pool: list[StoryCandidate] = []
    pool += _result_candidates(dynasty, state, year, week, games)
    pool += _poll_candidates(dynasty, state, year, week)
    pool += _preview_candidates(dynasty, state, year, week)
    pool += _recruiting_candidates(dynasty, state, year, week)
    pool += _carousel_candidates(dynasty, state, year, week)
    # Floor: if the program slate is thin (a bye week, a quiet stretch), draw
    # evergreens so the program feed always has texture.
    if sum(1 for c in pool if c.scope == "program") < 3:
        pool += _evergreen_candidates(dynasty, state, year, week)
    return pool
