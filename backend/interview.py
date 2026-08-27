"""Post-game press conference: the interactive interview after the user's game.

When the user's game finishes, five local reporters take turns asking the coach
one question each. The coach answers in his own words; if an answer is vague or
evasive a reporter may, rarely, follow up once. The whole exchange is PUBLIC: it
is rendered into the news context (directory.press_conference_block) and the
phone's media context, so any reporter, local or national, can quote the coach in
an article or a text.

This is a leaf module (it must not import directory or pipeline, which import it):
it depends only on llm, customization, narrative, and modules.base for the prompt
context. Transcripts persist per season at data/interviews/<year>.json, keyed by
the completed game's game_key ("week|home|away"), mirroring messages.py.

State machine per presser:
  start  -> reporter 0 asks (status in_progress, awaiting an answer)
  answer -> records it; the reporter may ask one rare follow-up (an RNG gate keeps
            it rare and deterministic, model only judges quality), else the next
            reporter asks; after the fifth reporter the presser is complete
  skip   -> the LLM answers the remaining questions in the coach's voice so the
            transcript stays complete and reporters still have material

Everything falls back to a deterministic mock so the presser always completes even
with no LLM connection (otherwise the news gate that waits on it would deadlock).
"""
from __future__ import annotations

import json
import random
import re
import threading
from typing import Any

from . import customization, dynasty_paths, llm, narrative
from .modules import base

_lock = threading.Lock()
N_REPORTERS = 5
_FOLLOWUP_CHANCE = 0.25  # gate on top of a vague/evasive judgment; one per presser


# --- store ----------------------------------------------------------------
def _path(year: int):
    return dynasty_paths.sub("interviews") / f"{year}.json"


def _read(year: int) -> dict[str, Any]:
    p = _path(year)
    if not p.exists():
        return {"year": year, "pressers": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("pressers"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"year": year, "pressers": {}}


def _write(year: int, data: dict[str, Any]) -> None:
    try:
        _path(year).write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def get(year: int, game_key: str) -> dict[str, Any] | None:
    return _read(year)["pressers"].get(game_key)


def is_complete(year: int, game_key: str | None) -> bool:
    if not game_key:
        return True  # no game -> nothing owed
    p = get(year, game_key)
    return bool(p and p.get("status") == "complete")


def completed(year: int) -> list[dict[str, Any]]:
    """Finished pressers this season, oldest first (the public record)."""
    pressers = _read(year)["pressers"].values()
    done = [p for p in pressers if p.get("status") == "complete"]
    return sorted(done, key=lambda p: p.get("week", 0))


# --- reporters -------------------------------------------------------------
def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def reporters_for(dynasty: dict[str, Any]) -> list[dict[str, Any]]:
    """The five reporters at the podium: local beat first, topped up with national
    voices if a customized program has fewer than five local reporters. Stable id
    matches directory's scheme so PersonName and the news layer reconcile."""
    reps = customization.section("reporters") or []
    locals_ = [r for r in reps if (r.get("scope") or "").lower() == "local"]
    nationals = [r for r in reps if (r.get("scope") or "").lower() != "local"]
    chosen = (locals_ + nationals)[:N_REPORTERS]
    out = []
    for r in chosen:
        out.append({
            "id": f"reporters:{_slug(r.get('name', ''))}",
            "name": r.get("name", "Reporter"),
            "outlet": r.get("outlet", ""),
            "scope": r.get("scope", "local"),
            "beat": r.get("beat", "program"),
            "reliability": r.get("reliability", 75),
            "bio": r.get("bio", ""),
            "traits": r.get("traits") or {},
        })
    return out


def _persona(rep: dict[str, Any]) -> str:
    t = rep.get("traits") or {}
    bits = []
    if t.get("ego", 0) >= 70 or t.get("confidence", 0) >= 80:
        bits.append("pointed and not shy about pressing")
    if t.get("loyalty", 0) >= 75:
        bits.append("close to the program and fan base")
    if t.get("composure", 0) >= 80:
        bits.append("measured and even-handed")
    voice = ", ".join(bits) or "fair but probing"
    return f"{rep['name']} of {rep['outlet']} ({rep.get('beat', 'program')} beat), {voice}"


# --- game brief for prompts -----------------------------------------------
def _game_view(dynasty: dict[str, Any]) -> dict[str, Any] | None:
    lg = dynasty.get("last_game")
    if not lg:
        return None
    user = (dynasty.get("team") or {}).get("name")
    home, away = lg["home"], lg["away"]
    user_home = lg.get("user_is_home")
    us, them = (home, away) if user_home else (away, home)
    won = us["score"] > them["score"]
    opp_coach = ((dynasty.get("coaches") or {}).get(them["name"]) or {}).get("name")
    return {
        "user": user, "opponent": them["name"], "opp_abbr": them.get("abbr"),
        "opp_coach": opp_coach,
        "us_score": us["score"], "opp_score": them["score"],
        "result": "W" if won else "L", "home": user_home,
        "result_line": f"{'W' if won else 'L'} {us['score']}-{them['score']} {'vs' if user_home else 'at'} {them['name']}",
        "lg": lg,
    }


def _game_brief(view: dict[str, Any]) -> str:
    lg = view["lg"]
    ts = lg["team_stats"]["home" if view["home"] else "away"]
    box = lg["box"]["home" if view["home"] else "away"]
    lines = [f"GAME JUST PLAYED: {view['user']} {view['result_line']}."
             + (" (overtime)" if lg.get("overtime") else "")]
    if view.get("opp_coach"):
        lines.append(f"{view['opponent']} is coached by {view['opp_coach']}.")
    lines.append(
        f"Your team: {ts['total_yards']} total yards ({ts['pass_yards']} pass, {ts['rush_yards']} rush), "
        f"{ts['first_downs']} first downs, {ts['third_down']} on third down, {ts['turnovers']} turnovers, "
        f"{ts['sacks']} sacks, time of possession {ts['time_of_possession']}.")
    if box["passing"]:
        p = box["passing"][0]
        lines.append(f"QB {p['name']}: {p['c_att']}, {p['yards']} yds, {p['td']} TD, {p['int']} INT.")
    if box["rushing"]:
        r = box["rushing"][0]
        lines.append(f"Leading rusher {r['name']}: {r['car']} car, {r['yards']} yds, {r['td']} TD.")
    if box["receiving"]:
        w = box["receiving"][0]
        lines.append(f"Leading receiver {w['name']}: {w['rec']} rec, {w['yards']} yds, {w['td']} TD.")
    if lg.get("scoring_summary"):
        lines.append("Scoring: " + "; ".join(
            f"Q{s['quarter']} {s['team_abbr']} {s['detail']}" for s in lg["scoring_summary"][:10]))
    if lg.get("key_plays"):
        kp = [k["description"] for k in lg["key_plays"] if k.get("kind") in ("Turnover", "Explosive")][:3]
        if kp:
            lines.append("Notable plays: " + "; ".join(kp))
    return "\n".join(lines)


def _pbp_block(view: dict[str, Any]) -> str:
    """The full snap-by-snap play log, so the reporters genuinely have every play
    of the game to draw on. This is the one place that needs it; the shared
    context (base.build_context) deliberately drops it to stay light."""
    plays = (view.get("lg") or {}).get("play_by_play") or []
    if not plays:
        return ""
    lines = []
    for p in plays:
        dd = f"{p['down']} and {p['distance']}" if p.get("down") else ""
        lines.append(f"  Q{p.get('quarter')} {p.get('clock', '')} {p.get('team_abbr', '')} "
                     f"{dd} at {p.get('yardline', '')}: {p.get('description', '')}".strip())
    return "=== FULL PLAY-BY-PLAY (every play of the game) ===\n" + "\n".join(lines)


def _presser_context(dynasty: dict, view: dict[str, Any], year: int, week: int) -> str:
    """A LEAN context for the presser. A reporter asks about THIS game, and the full
    game brief (box score, stats, scoring, notable plays) is already in the user
    prompt while the authoritative facts ride in `grounding`. So the presser does NOT
    need the full ~80KB dynasty dump as a cached block, which made each question and
    answer slow and prone to JSON-parse failures on a local model. We send just the
    fictional-universe rule and the key facts (a couple of KB)."""
    t = dynasty.get("team", {}) or {}
    hc = (t.get("head_coach", {}) or {}).get("name", "the head coach")
    return (
        "This is a FICTIONAL college football dynasty universe. Use ONLY the names and "
        "facts provided; never use real-life coaches, players, or results, even for real "
        f"teams. The head coach of {t.get('name', 'the program')} is {hc} and nobody else.\n\n"
        f"=== KEY FACTS ===\n{base.grounding_facts(dynasty)}"
    )


# --- LLM + mock generation -------------------------------------------------
def _llm_ok(use_llm: bool) -> bool:
    return bool(use_llm) and base.llm_available()


def _ask_question(dynasty, view, rep, asked, year, week, use_llm) -> str:
    coach = ((dynasty.get("team") or {}).get("head_coach") or {}).get("name") or "Coach"
    if _llm_ok(use_llm):
        try:
            system = (
                f"You are {_persona(rep)}, at the post-game press conference for {coach} of "
                f"{view['user']}. Ask ONE pointed question in your own voice. MOST reporters ask "
                "about THIS game (use the real result, stats and plays); SOME ask about the bigger "
                "storylines around the program this week (listed below) instead. One or two "
                "sentences, conversational, no preamble. Never use dashes as punctuation. "
                "Return strict JSON: {\"question\": \"...\"}."
            )
            # The week's storylines so the room asks about real threads, not only the game.
            storylines = ""
            try:
                from . import editorial
                storylines = editorial.presser_brief(dynasty, year, week)
            except Exception:
                storylines = ""
            prior = "\n".join(f"- {q}" for q in asked) or "(none yet)"
            prompt = (f"{_game_brief(view)}\n\n"
                      + (storylines + "\n\n" if storylines else "")
                      + "Questions other reporters already asked (ask about something different):\n"
                      + f"{prior}\n\nYour question as {rep['name']}:")
            data = llm.generate_json(system, prompt, cached_context=_presser_context(dynasty, view, year, week),
                                     grounding=base.reactive_grounding(dynasty, year, week), max_tokens=300, temperature=0.7)
            q = (data.get("question") if isinstance(data, dict) else None) or ""
            q = base.sanitize(q).strip()
            if q:
                return q
        except Exception:
            pass
    return _mock_question(view, rep, len(asked))


def _assess(dynasty, view, rep, question, answer, year, week, use_llm) -> str:
    """Judge the coach's answer: 'direct', 'vague', or 'evasive'. The decision to
    actually follow up is gated by an RNG outside the model (see _answer)."""
    if _llm_ok(use_llm):
        try:
            system = (
                "You are a press-conference moderator judging whether a coach's answer was "
                "direct and substantive, or vague, evasive, or misleading. Return strict JSON: "
                "{\"assessment\": \"direct\" | \"vague\" | \"evasive\"}."
            )
            prompt = f"Reporter asked: {question}\nCoach answered: {answer}\nJudge the answer:"
            data = llm.generate_json(system, prompt, max_tokens=80, temperature=0.2)
            a = (data.get("assessment") if isinstance(data, dict) else "") or ""
            if a in ("direct", "vague", "evasive"):
                return a
        except Exception:
            pass
    return "direct"  # mock: never provokes a follow-up


def _follow_up_question(dynasty, view, rep, question, answer, year, week, use_llm) -> str:
    coach = ((dynasty.get("team") or {}).get("head_coach") or {}).get("name") or "Coach"
    if _llm_ok(use_llm):
        try:
            system = (
                f"You are {_persona(rep)}. The coach's answer was vague or evasive. Ask ONE sharp, "
                "polite follow-up that presses for a real answer. One sentence. Never use dashes as "
                "punctuation. Return strict JSON: {\"question\": \"...\"}."
            )
            prompt = f"Your question: {question}\n{coach}'s answer: {answer}\nYour follow-up:"
            data = llm.generate_json(system, prompt, max_tokens=160, temperature=0.7)
            q = base.sanitize((data.get("question") if isinstance(data, dict) else "") or "").strip()
            if q:
                return q
        except Exception:
            pass
    return "Just to follow up, can you be a little more specific there?"


def _coach_answer(dynasty, view, rep, question, year, week, use_llm) -> str:
    """The coach's own answer, generated when the user skips the rest of the presser."""
    coach = ((dynasty.get("team") or {}).get("head_coach") or {}).get("name") or "Coach"
    if _llm_ok(use_llm):
        try:
            system = (
                f"You are {coach}, head coach of {view['user']}, at your post-game press conference "
                f"after a {view['result_line']}. Answer the reporter in a measured, in-character head "
                "coach voice, grounded in what happened in this game. One to three sentences, no "
                "preamble. Never use dashes as punctuation. Return strict JSON: {\"answer\": \"...\"}."
            )
            prompt = f"{_game_brief(view)}\n\n{rep['name']} of {rep['outlet']} asked: {question}\n\nYour answer:"
            data = llm.generate_json(system, prompt, cached_context=_presser_context(dynasty, view, year, week),
                                     grounding=base.reactive_grounding(dynasty, year, week), max_tokens=260, temperature=0.7)
            a = base.sanitize((data.get("answer") if isinstance(data, dict) else "") or "").strip()
            if a:
                return a
        except Exception:
            pass
    return _mock_coach_answer(view, rep)


# --- deterministic mock pools ---------------------------------------------
def _mock_question(view: dict[str, Any], rep: dict[str, Any], idx: int) -> str:
    lg = view["lg"]
    box = lg["box"]["home" if view["home"] else "away"]
    qb = box["passing"][0]["name"] if box["passing"] else "your quarterback"
    rb = box["rushing"][0]["name"] if box["rushing"] else "the run game"
    won = view["result"] == "W"
    pool = [
        f"What was the difference for you tonight in the {view['us_score']}-{view['opp_score']} {'win' if won else 'loss'}?",
        f"What did you see from {qb} and the passing game today?",
        f"{rb} carried the load on the ground. How big was that to the game plan?",
        f"The defense gave up {view['opp_score']}. How did you feel about that side of the ball?",
        f"What does this result mean heading into next week against your next opponent?",
        "Was there a turning point where you felt the game swing?",
    ]
    return base.sanitize(pool[idx % len(pool)])


def _mock_coach_answer(view: dict[str, Any], rep: dict[str, Any] | None = None) -> str:
    won = view["result"] == "W"
    if won:
        pool = [
            "Proud of how this group competed for four quarters. We made the plays we had to make and now we get back to work.",
            "Credit our guys. They prepared the right way and it showed. Plenty to clean up, but a win is a win.",
            "That is a good football team we just beat. Our players earned this one, and we move on to the next.",
            "We talked all week about finishing, and the guys did that. Now the standard does not change.",
        ]
    else:
        pool = [
            "We did not play clean enough to win tonight, and that starts with me. We will own it and get better.",
            "Give them credit, they made more plays than we did. We have to be sharper, and we will be.",
            "Disappointed, but this is a resilient group. We will look at the tape, learn from it, and respond.",
            "Too many self-inflicted mistakes. We coach it, we fix it, and we come back to work tomorrow.",
        ]
    seed = view["result_line"] + (rep.get("id", "") if rep else "")
    return base.sanitize(random.Random(seed).choice(pool))


# --- public state machine --------------------------------------------------
def pending(year: int, dynasty: dict[str, Any]) -> dict[str, Any] | None:
    """If the user's last game has no completed presser, return the owed game,
    else None. Used by the pipeline gate and the frontend trigger."""
    view = _game_view(dynasty)
    if not view:
        return None
    gk = view["lg"]["game_key"]
    if is_complete(year, gk):
        return None
    return {"game_key": gk, "week": view["lg"]["week"], "opponent": view["opponent"],
            "result_line": view["result_line"]}


def _public(presser: dict[str, Any]) -> dict[str, Any]:
    """The presser as the frontend consumes it: identity, reporters, transcript so
    far, and what (if anything) the coach is being asked right now."""
    turns = presser.get("turns", [])
    awaiting = presser.get("awaiting")
    idx = presser.get("current", 0)
    rep = presser["reporters"][idx] if idx < len(presser["reporters"]) else None
    prompt = None
    if presser.get("status") != "complete" and rep:
        prompt = {"reporter": rep, "index": idx, "total": len(presser["reporters"]),
                  "kind": awaiting, "question": presser.get("current_question", "")}
    return {
        "game_key": presser["game_key"], "week": presser["week"],
        "opponent": presser.get("opponent"), "result_line": presser.get("result_line"),
        "reporters": presser["reporters"], "turns": turns,
        "status": presser["status"], "prompt": prompt,
    }


def start(year: int, week: int, dynasty: dict[str, Any], *, use_llm: bool) -> dict[str, Any] | None:
    """Begin (or resume) the presser for the user's last game."""
    view = _game_view(dynasty)
    if not view:
        return None
    gk = view["lg"]["game_key"]
    with _lock:
        data = _read(year)
        existing = data["pressers"].get(gk)
        if existing:
            return _public(existing)
        reporters = reporters_for(dynasty)
        presser = {
            "game_key": gk, "week": view["lg"]["week"], "opponent": view["opponent"],
            "result_line": view["result_line"], "reporters": reporters,
            "turns": [], "current": 0, "awaiting": "answer", "follow_up_spent": False,
            "current_question": "", "status": "in_progress",
        }
        data["pressers"][gk] = presser
        _write(year, data)
    # Generate reporter 0's question outside the lock (LLM call may be slow).
    q = _ask_question(dynasty, view, reporters[0], [], year, week, use_llm)
    with _lock:
        data = _read(year)
        p = data["pressers"][gk]
        if not p["current_question"]:
            p["current_question"] = q
            _write(year, data)
    return _public(get(year, gk))


def answer(year: int, week: int, game_key: str, dynasty: dict[str, Any], text: str,
           *, use_llm: bool) -> dict[str, Any] | None:
    """Record the coach's answer to the current question, then advance: a rare
    follow-up from the same reporter, the next reporter, or completion."""
    view = _game_view(dynasty)
    text = base.sanitize((text or "").strip())
    with _lock:
        data = _read(year)
        p = data["pressers"].get(game_key)
        if not p or p["status"] == "complete":
            return _public(p) if p else None
        idx = p["current"]
        rep = p["reporters"][idx]
        question = p["current_question"]
        awaiting = p["awaiting"]

    if awaiting == "follow_up":
        # Answer to a follow-up: record both and move on to the next reporter.
        with _lock:
            data = _read(year)
            p = data["pressers"][game_key]
            p["turns"][-1]["follow_up_answer"] = text
            _write(year, data)
        return _advance(year, week, game_key, dynasty, idx + 1, use_llm)

    # A fresh main answer: record the turn, then judge for a possible follow-up.
    turn = {"reporter_id": rep["id"], "reporter_name": rep["name"], "outlet": rep["outlet"],
            "question": question, "answer": text}
    with _lock:
        data = _read(year)
        p = data["pressers"][game_key]
        p["turns"].append(turn)
        _write(year, data)

    assessment = _assess(dynasty, view, rep, question, text, year, week, use_llm)
    # Deterministic, rare follow-up: model only judges quality; the RNG decides.
    gate = random.Random(f"{game_key}|{rep['id']}|fu").random()
    do_follow = (assessment != "direct" and gate < _FOLLOWUP_CHANCE
                 and not _read(year)["pressers"][game_key].get("follow_up_spent"))
    if do_follow:
        fq = _follow_up_question(dynasty, view, rep, question, text, year, week, use_llm)
        with _lock:
            data = _read(year)
            p = data["pressers"][game_key]
            p["turns"][-1]["follow_up_question"] = fq
            p["follow_up_spent"] = True
            p["awaiting"] = "follow_up"
            p["current_question"] = fq
            _write(year, data)
        return _public(get(year, game_key))

    return _advance(year, week, game_key, dynasty, idx + 1, use_llm)


def _advance(year, week, game_key, dynasty, next_idx, use_llm) -> dict[str, Any]:
    """Move to reporter `next_idx`, or finish the presser."""
    view = _game_view(dynasty)
    with _lock:
        data = _read(year)
        p = data["pressers"][game_key]
        if next_idx >= len(p["reporters"]):
            p["status"] = "complete"
            p["awaiting"] = None
            p["current_question"] = ""
            _write(year, data)
            _seed_narrative(year, p)
            return _public(p)
        p["current"] = next_idx
        p["awaiting"] = "answer"
        asked = [t["question"] for t in p["turns"]]
        rep = p["reporters"][next_idx]
        _write(year, data)
    q = _ask_question(dynasty, view, rep, asked, year, week, use_llm)
    with _lock:
        data = _read(year)
        p = data["pressers"][game_key]
        p["current_question"] = q
        _write(year, data)
    return _public(get(year, game_key))


def skip(year: int, week: int, game_key: str, dynasty: dict[str, Any], *, use_llm: bool) -> dict[str, Any] | None:
    """The coach declines the rest: the LLM answers the remaining questions in his
    voice so the transcript stays complete and reporters still have material."""
    view = _game_view(dynasty)
    if not view:
        return None
    with _lock:
        data = _read(year)
        p = data["pressers"].get(game_key)
        if not p or p["status"] == "complete":
            return _public(p) if p else None

    # Finish the current open turn (a question is on the table) and every reporter
    # who has not gone yet, auto-answering each.
    while True:
        with _lock:
            data = _read(year)
            p = data["pressers"][game_key]
            idx = p["current"]
            awaiting = p["awaiting"]
            rep = p["reporters"][idx]
            question = p["current_question"]
            turns_len = len(p["turns"])

        if awaiting == "follow_up":
            auto = _coach_answer(dynasty, view, rep, question, year, week, use_llm)
            with _lock:
                data = _read(year)
                p = data["pressers"][game_key]
                p["turns"][-1]["follow_up_answer"] = auto
                p["turns"][-1]["auto"] = True
                _write(year, data)
            nxt = idx + 1
        else:
            auto = _coach_answer(dynasty, view, rep, question, year, week, use_llm)
            with _lock:
                data = _read(year)
                p = data["pressers"][game_key]
                p["turns"].append({"reporter_id": rep["id"], "reporter_name": rep["name"],
                                   "outlet": rep["outlet"], "question": question,
                                   "answer": auto, "auto": True})
                _write(year, data)
            nxt = idx + 1

        if nxt >= len(rep_list(year, game_key)):
            with _lock:
                data = _read(year)
                p = data["pressers"][game_key]
                p["status"] = "complete"
                p["awaiting"] = None
                p["current_question"] = ""
                _write(year, data)
                _seed_narrative(year, p)
            return _public(get(year, game_key))

        # Prepare the next reporter's question for the auto-answer loop.
        with _lock:
            data = _read(year)
            p = data["pressers"][game_key]
            p["current"] = nxt
            p["awaiting"] = "answer"
            asked = [t["question"] for t in p["turns"]]
            next_rep = p["reporters"][nxt]
            _write(year, data)
        q = _ask_question(dynasty, view, next_rep, asked, year, week, use_llm)
        with _lock:
            data = _read(year)
            p = data["pressers"][game_key]
            p["current_question"] = q
            _write(year, data)


def rep_list(year: int, game_key: str) -> list[dict[str, Any]]:
    p = get(year, game_key)
    return p["reporters"] if p else []


_CHARGED = (
    "fire", "fired", "firing", "leav", "step away", "step down", "quit", "resign",
    "retire", "done", "embarrass", "unacceptable", "not good enough", "have to be better",
    "won't be", "wont be", "never", "suspend", "out for", "transfer", "portal", "benched",
)


def public_statement(presser: dict[str, Any] | None, *, max_chars: int = 400) -> str:
    """The coach's single most newsworthy press-conference answer, on the record,
    for the world-reaction engine to judge. NOT the whole transcript: passing every
    answer glued together made the breaking post a dump of his words. Returns the
    most charged answer (a firing threat, a shot, a real admission); a routine
    presser yields only bland answers, which the engine's guardrail then declines to
    break. Empty when he said nothing of substance."""
    if not presser:
        return ""
    answers: list[str] = []
    for t in presser.get("turns", []):
        for key in ("answer", "follow_up_answer"):
            a = (t.get(key) or "").strip()
            if len(a) > 1:
                answers.append(a)
    if not answers:
        return ""

    def score(a: str) -> int:
        low = a.lower()
        return sum(2 for w in _CHARGED if w in low) + min(len(a) // 50, 3)

    return max(answers, key=score)[:max_chars]


def _seed_narrative(year: int, presser: dict[str, Any]) -> None:
    """Log a one-line memory anchor so later weeks remember the presser happened."""
    try:
        first = next((t for t in presser.get("turns", []) if t.get("answer")), None)
        if first:
            narrative.log_week(year, presser.get("week", 0),
                               [f"Post-game presser ({presser.get('result_line', '')}): "
                                f"coach told {first['reporter_name']}, \"{first['answer'][:140]}\""])
    except Exception:
        pass
