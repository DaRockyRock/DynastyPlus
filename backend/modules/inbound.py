"""Unprompted inbound texts.

Real life does not wait for the coach to reach out first. On each new week this
module picks a varied handful of people from the dynasty universe and has them
text the coach first, in character and aware of the week: players reacting to the
result, coordinators with a game plan wrinkle or carousel jitters, the AD checking
the trajectory, recruits with news on their process, reporters fishing for intel
or a quote, rival coaches comparing carousel notes, awards voters weighing the
resume. Each text is composed by phone.compose_inbound (LLM with a mock fallback)
and delivered into the right thread marked unread.

Selection is deterministic per (year, week) and capped, so it feels alive without
spamming, and delivery is guarded once-per-week in the message store so re-running
the pipeline (prewarm, regenerate, the watcher) never doubles up a text.

This module is registered just before `phone` so the phone roster, generated
right after, picks up everyone who just texted and shows them in the list.
"""
from __future__ import annotations

import random
import re
from typing import Any

from .. import cache, customization, directory, progress
from .. import messages as msg_store
from . import base, phone

MODULE = "inbound"

# How many people text the coach in a given week (chosen per week), and the most
# from any one category, so a week is a varied mix rather than five reporters.
_WEEK_COUNTS = [3, 3, 4, 4, 5]
_CATEGORY_CAP = 2

# Base likelihood each kind reaches out, before week-specific boosts.
_BASE_WEIGHT = {
    "player": 4, "staff": 4, "ad": 2, "recruit": 3, "transfer": 2,
    "media": 3, "analyst": 1, "voter": 1, "committee": 1,
    "opp_coach": 1, "candidate": 1, "contact": 1,
}


# --- dynasty readers ------------------------------------------------------
def _last_result(dynasty: dict) -> dict | None:
    res = (dynasty.get("schedule") or {}).get("recent_results") or []
    return res[0] if res else None


def _result_phrase(dynasty: dict):
    """(\"the team just won 34 to 20 vs Maryland\", won, last) or None."""
    last = _last_result(dynasty)
    if not last:
        return None
    won = last.get("result") == "W"
    loc = "vs" if last.get("home") else "at"
    score = str(last.get("score", "")).replace("-", " to ")
    phrase = f"the team just {'won' if won else 'lost'} {score} {loc} {last.get('opponent', '')}".strip()
    return phrase, won, last


def _next_opp(dynasty: dict) -> str:
    return ((dynasty.get("schedule") or {}).get("upcoming") or {}).get("opponent") or ""


# --- topics: why this person is texting, plus an offline opener pool -------
def _had_presser(dynasty: dict, year: int, week: int) -> bool:
    """True when the press conference being reacted to is from THIS week. A presser
    is only fresh news the week it happens, so this is False once the week advances,
    otherwise people re-text about last week's remarks all over again."""
    p = base._latest_presser(year, week)
    return bool(p) and p.get("week") == week


def _topic(rng: random.Random, contact: dict, kind: str, dynasty: dict,
           record: dict | None = None, *, presser: bool = False, game_this_week: bool = False):
    program = dynasty["team"]["name"]
    # The last game/result is only "news to react to" the week it was played; in a
    # later (preview) week people talk about the upcoming game and their roles, not
    # last week's result again.
    rp = _result_phrase(dynasty) if game_this_week else None
    nxt = _next_opp(dynasty)

    if kind == "player":
        opts = []
        if presser:
            opts.append(("You just watched the coach's post-game press conference. You are texting him reacting to "
                         "what he actually said in it (his tone and his words) and to the result. Respond to what he "
                         "really said, not generic motivation.",
                         ["saw the presser coach", "we hear you, that's on us", "we'll show you different"] if not (rp and rp[1])
                         else ["loved what you said up there coach", "we ride with you", "on to the next"]))
        if rp:
            opts.append((f"{rp[0]}. You are texting the coach your reaction as one of his players.",
                         ["that was a war coach", "we built different fr", "on to the next one"] if rp[1]
                         else ["this one stings coach", "we'll be back, i promise you that", "put it on me, i'll be better"]))
        if nxt:
            opts.append((f"You are locked in for the upcoming game against {nxt} and texting the coach about it.",
                         [f"ready for {nxt} coach", "i'll be dialed saturday", "lets go get this one"]))
        opts.append(("You want to talk to the coach about your role or your snaps.",
                     ["coach can we talk about my reps", "feel like i can give yall more", "just wanna help any way i can"]))
        opts.append(("You want to check in with the coach about your NIL situation.",
                     ["coach you got a sec to talk NIL", "some stuff came across my plate i wanna run by you"]))
        return rng.choice(opts)

    if kind == "recruit":
        rec = record or {}
        we_lead = (rec.get("leader") or "") == program
        opts = [
            ("You just picked up another scholarship offer and wanted this coach to hear it from you.",
             ["coach just picked up another offer", "wanted you to hear it from me", "still got love for yall though"]),
            ("You are letting the coach know you are trying to lock in a visit.",
             ["coach i wanna get back on campus", "trying to lock a visit before i decide", "yall still my priority visit"]),
            ("You have a question about how you would be used or developed at this program.",
             ["coach whats my path to the field look like", "how would yall actually use me"]),
        ]
        if rp:
            opts.append((f"You saw that {rp[0]} and are reacting to the coach as a recruit watching closely.",
                         ["yo i saw the game coach", "yall looked good fr"] if rp[1]
                         else ["tough one coach but i see the vision", "i'm still locked in on yall"]))
        if we_lead:
            opts.append(("You are getting close to a decision and this program is your leader, so you are warm and want to talk.",
                         ["coach we might need to talk soon", "yall sitting real high for me rn"]))
        else:
            opts.append(("Another school is recruiting you hard and you are being honest with this coach about where you stand.",
                         ["coach another school coming hard", "wanted to be upfront with you", "where do i really stand with yall"]))
        return rng.choice(opts)

    if kind == "transfer":
        opts = [
            ("You are in the transfer portal and this program is on your list, so you are reaching out.",
             ["coach saw yall might have a spot for me", "whats the situation at my position", "open to talking fr"]),
            ("You want to know about playing time and fit before you make a move.",
             ["coach how real is the playing time", "where would i fit in your scheme"]),
        ]
        return rng.choice(opts)

    if kind == "ad":
        opts = []
        if presser:
            opts.append(("You just saw the coach's post-game press conference. You are the athletic director and you "
                         "text him directly reacting to what he ACTUALLY said in it. If his remarks were measured, you "
                         "are reassured; if they were combative, alarming, profane, or he questioned his own future or "
                         "staff, you are concerned and address that head on. React to his real words, not a generic "
                         "check-in.",
                         ["coach, we should talk about that presser", "you alright? that was a lot up there",
                          "let's connect today, want to make sure we're aligned"]))
        opts.append(("You are checking in with the head coach about the program's trajectory and expectations.",
                     ["got a minute to talk big picture?", "boosters keep asking where we're headed"]))
        if rp:
            opts.append((f"{rp[0]}. You are the AD reaching out after the result.",
                         ["good win, the room noticed", "lets keep stacking these"] if rp[1]
                         else ["we'll regroup, i've got your back", "lets talk when you get a sec"]))
        opts.append(("You want to talk budget and Dynasty Points with the coach.",
                     ["when you get a sec lets talk budget", "want to make sure we spend where it wins"]))
        return rng.choice(opts)

    if kind == "staff":
        opts = []
        if presser:
            opts.append(("You just watched the head coach's post-game press conference. You are a coach on his staff "
                         "texting him about what he said in it (especially if he called out the staff or the players). "
                         "React to his actual remarks.",
                         ["saw the presser coach", "whatever you need from me, i'm on it", "we'll get it cleaned up"]))
        if nxt:
            opts.append((f"You are texting the head coach with a game plan thought for {nxt}.",
                         [f"{nxt} film is jumping out at me", "got a wrinkle i wanna show you", "we can get their edges"]))
        if rp:
            opts.append((f"{rp[0]}. You are reacting as a coach on staff.",
                         ["proud of the room today", "already onto the next"] if rp[1]
                         else ["we'll fix it on the grass monday", "i didnt have them ready, on me"]))
        opts.append(("You have a recruiting update on a target you want to pass along.",
                     ["coach got an update on one of our targets", "momentum might be shifting our way"]))
        opts.append(("You heard your own name come up in some coaching carousel chatter and want to feel out where you stand.",
                     ["coach you got a sec, heard some chatter", "wanted to talk to you before it gets noisy"]))
        return rng.choice(opts)

    if kind == "opp_coach":
        opts = [("You are a rival head coach reaching out, cordial but guarded.",
                 ["good battle out there coach", "always respect what yall do"]),
                ("You heard coaching carousel chatter and are quietly comparing notes with a peer.",
                 ["you hearing all this carousel noise too?", "wild time of year coach"])]
        return rng.choice(opts)

    if kind == "candidate":
        return ("Your name is hot on the coaching carousel and you are touching base with this coach.",
                ["my names getting thrown around coach", "wanted to keep our line open"])

    if kind == "committee":
        return ("As a CFP committee member you are sending a careful, diplomatic note about what the field still needs to prove.",
                ["the room is watching closely, thats all i'll say", "keep stacking the quality wins"])

    if kind == "voter":
        opts = [("You are an awards and poll voter sending a note about the team's resume.",
                 ["the resume is starting to talk coach", "whos your guy for the postseason awards"])]
        if rp:
            opts.append((f"{rp[0]}. You are reacting as a voter weighing the body of work.",
                         ["thats a resume game right there", "noted for my ballot"] if rp[1]
                         else ["that result complicates the resume", "still got a long way to go"]))
        return rng.choice(opts)

    if kind == "analyst":
        return ("You are a recruiting analyst flagging momentum on one of the coach's recruiting battles.",
                ["hearing buzz on one of your targets coach", "might file a prediction soon, anything you can tell me"])

    if kind == "media":
        opts = [(f"You are a reporter fishing for intel or a quote ahead of {nxt}." if nxt
                 else "You are a reporter fishing for intel or a quote.",
                 ["coach quick one for a story", "anything you can give me ahead of saturday"]),
                ("You are chasing a recruiting rumor and want the coach to confirm or steer you.",
                 ["hearing something on the recruiting front", "can you point me one way or the other?"]),
                ("You are working a coaching carousel and hot seat story and want the coach's read.",
                 ["working a carousel piece, you hearing anything?", "wanted to check with you before i run it"])]
        if rp:
            opts.append((f"{rp[0]}. You want the coach's reaction for your story.",
                         ["need your read on the game coach", "whats the message to the room"]))
        return rng.choice(opts)

    return ("You are reaching out to the coach to check in.",
            ["wanted to reach out coach", "hope things are good with the team"])


# --- candidate pool -------------------------------------------------------
def _texted_before(year: int, cid: str) -> bool:
    return any(m.get("from") == "them" for m in msg_store.thread(year, cid))


def _recruit_warmth(rec: dict, program: str, texted_before: bool) -> int:
    interest = int(rec.get("interest") or 0)
    we_lead = (rec.get("leader") or "") == program
    stage = rec.get("stage") or ""
    stages = customization.RECRUIT_STAGES
    sidx = stages.index(stage) if stage in stages else 0
    return (interest // 20) + (3 if we_lead else 0) + sidx + (2 if texted_before else 0)


# Position -> the words a coach uses for it, so a called-out position maps to its
# starter. Multi-word phrases and abbreviations are matched on word boundaries.
_POS_PHRASES = {
    "QB": ["quarterback", "qb"], "RB": ["running back", "tailback", "rb"],
    "WR": ["wide receiver", "receiver", "wideout", "wr"], "TE": ["tight end", "te"],
    "OT": ["offensive line", "o-line", "oline", "left tackle", "right tackle"],
    "OG": ["guard"], "C": ["center"], "EDGE": ["edge", "pass rush"],
    "DT": ["defensive line", "d-line", "dline", "defensive tackle", "interior"],
    "LB": ["linebacker", "lb"], "CB": ["cornerback", "corner", "cb"],
    "S": ["safety"], "K": ["kicker", "kicking"], "P": ["punter"],
}


def _presser_callouts(dynasty: dict, year: int, week: int) -> dict[str, str]:
    """Players the coach singled out in his last press conference, by name or by
    position (a called-out position maps to its current starter), with the reason.
    So 'we have to reevaluate our TE play, especially our starter' makes the starting
    TE reach out."""
    presser = base._latest_presser(year, week)
    if not presser:
        return {}
    low = " ".join(base._presser_quotes(presser, limit=12)).lower()
    if not low.strip():
        return {}
    players = (dynasty.get("roster") or {}).get("key_players") or []
    out: dict[str, str] = {}
    for p in players:  # explicit name mention
        nm = p.get("name")
        if nm and nm.lower() in low:
            out[nm] = "the coach mentioned you by name at his press conference"
    for pos, words in _POS_PHRASES.items():  # a called-out position -> its starter
        if not any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
            continue
        starter = next((p for p in players if p.get("position") == pos
                        and str(p.get("depth_chart_slot", "")).lower().startswith("starting")), None)
        if starter and starter.get("name") and starter["name"] not in out:
            out[starter["name"]] = "the coach called out your position at his press conference"
    return out


# Words that mark a presser as pointed/critical, so the coordinators take notice
# (their units are on the line) rather than only the AD reaching out.
_CRITICAL_WORDS = (
    "horrific", "unacceptable", "embarrassing", "not good enough", "reevaluate", "fire",
    "fired", "sideline", "bench", "gave up", "can't", "cannot", "losing", "lost", "dumb",
    "fucking", "pathetic", "soft", "blame", "have to be better", "no excuse", "$",
)


def _critical_presser(dynasty: dict, year: int, week: int) -> bool:
    """True when the coach's last presser was pointed/negative, so the staff feels
    the heat and the coordinators reach out, not just the AD."""
    p = base._latest_presser(year, week)
    if not p:
        return False
    low = " ".join(base._presser_quotes(p, limit=12)).lower()
    return any(w in low for w in _CRITICAL_WORDS)


def _candidates(dynasty: dict, year: int, week: int) -> list[dict[str, Any]]:
    """Everyone who could plausibly text the coach first this week, each with a
    weight, the topic that frames their text, and an offline opener pool."""
    program = dynasty["team"]["name"]
    last = _last_result(dynasty)
    game_this_week = bool(last) and last.get("week") == week
    presser = _had_presser(dynasty, year, week)
    callouts = _presser_callouts(dynasty, year, week) if presser else {}
    critical = presser and _critical_presser(dynasty, year, week)
    rec = dynasty.get("recruiting") or {}
    recruiting_buzz = bool(rec.get("commits")) or any(
        (t.get("interest") or 0) >= 70 for t in (rec.get("targets") or []))
    rng = random.Random(f"{year}:{week}:inbound")
    pool: dict[str, dict[str, Any]] = {}

    def add(contact: dict | None, kind: str, weight: int, record: dict | None = None):
        if not contact or weight <= 0:
            return
        cid = contact["id"]
        topic, mock = _topic(rng, contact, kind, dynasty, record, presser=presser,
                             game_this_week=game_this_week)
        entry = {"contact": contact, "kind": kind, "category": contact.get("category", "Media"),
                 "weight": weight, "topic": topic, "mock": mock}
        prev = pool.get(cid)
        if not prev or weight > prev["weight"]:
            pool[cid] = entry

    # Curated phone contacts (staff, AD, stars, the beat writer, the insider).
    for c in customization.section("phone_contacts"):
        contact = directory.by_id(c.get("id"))
        if not contact:
            continue
        kind = (contact.get("profile") or {}).get("kind", "contact")
        w = _BASE_WEIGHT.get(kind, 1)
        if game_this_week and kind in ("player", "staff", "ad", "media"):
            w += 2
        if kind == "staff":
            # Coordinators react to the week's real events, not only a brutal presser.
            # A coordinator reliably reaches out after a GAME (win or loss) or a
            # critical presser; the presser and recruiting momentum are softer nudges
            # (recruiting buzz is nearly always present, so it should not make a
            # coordinator a guaranteed top pick every single week).
            if presser:
                w += 2
            if recruiting_buzz:
                w += 2
            is_coord = "coordinator" in (contact.get("role") or "").lower()
            if is_coord and (critical or game_this_week):
                w = max(w, 11 if critical else 8)
        add(contact, kind, w)

    # Players the coach singled out at his press conference reach out, prominently,
    # to own it or quietly push back. A high weight makes the called-out player very
    # likely to text, so naming a position (or a player) draws a real response.
    for nm, reason in callouts.items():
        contact = directory.resolve(nm, "player")
        if not contact:
            continue
        topic = (f"You play for {program} and {reason}. You are texting the coach about it, owning it or "
                 "quietly standing up for yourself. React to what he ACTUALLY said, do not invent quotes.")
        pool[contact["id"]] = {
            "contact": contact, "kind": "player", "category": contact.get("category", "Players"),
            "weight": 12, "topic": topic,
            "mock": ["saw what you said coach", "that's on me, i'll be better", "i hear you, back to work"],
        }

    # The live recruiting board: warm prospects reach out, cold ones rarely do.
    rec = dynasty.get("recruiting") or {}
    board = list(rec.get("commits") or [])
    board += sorted(rec.get("targets") or [], key=lambda r: -(r.get("interest") or 0))[:15]
    for r in board:
        name = r.get("name")
        if not name:
            continue
        contact = directory.resolve(name, "recruit")
        if not contact:
            continue
        warmth = _recruit_warmth(r, program, _texted_before(year, contact["id"]))
        if warmth >= 3:
            add(contact, "recruit", warmth, record=r)

    # A reporter or two from the newsroom (beyond any curated media contacts).
    for r in (customization.section("reporters") or [])[:6]:
        contact = directory.resolve(r.get("name"), "media")
        w = _BASE_WEIGHT["media"] + (1 if game_this_week else 0)
        add(contact, "media", w)

    # The just-played opponent's head coach, if he is a known (hot seat) coach.
    last = _last_result(dynasty)
    if last:
        opp = last.get("opponent")
        for hc in (customization.section("hot_seat_coaches") or []):
            if hc.get("team") == opp and hc.get("coach"):
                contact = directory.resolve(hc["coach"], "opp_coach")
                add(contact, "opp_coach", _BASE_WEIGHT["opp_coach"] + 3)
                break

    # A coaching candidate on the carousel, occasionally.
    for cand in (customization.section("candidates") or [])[:4]:
        add(directory.resolve(cand.get("name"), "candidate"), "candidate", _BASE_WEIGHT["candidate"])

    return list(pool.values())


def _select(candidates: list[dict[str, Any]], year: int, week: int) -> list[dict[str, Any]]:
    """Deterministic, weighted, category-capped pick for the week."""
    rng = random.Random(f"{year}:{week}:inbound:pick")
    remaining = list(candidates)
    count = rng.choice(_WEEK_COUNTS)
    per_cat: dict[str, int] = {}
    chosen: list[dict[str, Any]] = []
    while remaining and len(chosen) < count:
        total = sum(c["weight"] for c in remaining)
        if total <= 0:
            break
        roll = rng.uniform(0, total)
        acc = 0.0
        idx = len(remaining) - 1
        for i, c in enumerate(remaining):
            acc += c["weight"]
            if roll <= acc:
                idx = i
                break
        pick = remaining.pop(idx)
        cat = pick["category"]
        if per_cat.get(cat, 0) >= _CATEGORY_CAP:
            continue
        per_cat[cat] = per_cat.get(cat, 0) + 1
        chosen.append(pick)
    return chosen


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    selected = _select(_candidates(dynasty, year, week), year, week)
    delivered: list[dict[str, Any]] = []
    source = "mock"
    for entry in selected:
        contact = entry["contact"]
        progress.set_sub_step(contact["name"])
        msgs = phone.compose_inbound(contact, dynasty, year=year, week=week, use_llm=use_llm,
                                     topic=entry["topic"], mock_pool=entry["mock"])
        if not msgs:
            continue
        items = [{"from": "them", "text": m, "unread": True} for m in msgs]
        if not msg_store.deliver_inbound(year, week, contact["id"], items):
            continue  # already texted the coach first this week
        if use_llm and base.llm_available():
            source = "llm"
        delivered.append({
            "contact_id": contact["id"], "name": contact["name"],
            "category": contact.get("category", ""), "topic": entry["topic"], "messages": msgs,
        })
    # `phone` is generated right after this module; drop its cached roster so it
    # rebuilds with the new threads (and surfaces anyone who just texted first).
    if delivered:
        cache.clear_module(year, week, phone.MODULE)
    return base.sanitize({"module": MODULE, "source": source, "week": week, "delivered": delivered})
