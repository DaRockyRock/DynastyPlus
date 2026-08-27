"""The world-reaction engine.

When the coach says something the world can hear (a media text, a presser
answer, or a leak out of a private conversation), this engine decides whether
the world reacts and orchestrates a proportional, chained reaction across the
social feed, the news, and the people who text him. It is the piece that turns
"I'm leaving and taking the Alabama job, leak it" into a breaking tweet, a wave
of reactions, and (in later slices) articles and panicked texts, while letting
"one game at a time" pass without a ripple.

Four stages:
  1. classify   - the assignment desk. One cheap judgment (LLM, with a keyword
                  heuristic fallback) of how newsworthy the statement is: a tier
                  (0..3), the coach's intent (leak / confirm / deny / praise...),
                  whether it is on the record, the topic, and a neutral summary.
  2. plan       - tier -> a concrete, tunable budget of reactions.
  3. compose    - render the cascade: the breaking post, reaction quote-posts
                  from other media, and raw fan posts (reusing the feed module's
                  accounts and voice). LLM with a grounded mock fallback.
  4. write      - persist every reaction to the durable world-event log
                  (world_events.py) and patch it straight into this week's cached
                  feed so it surfaces within seconds, then seed narrative memory
                  for the big stories so future weeks remember.

SLICE 1 covers the feed reaction (tweets). Articles, inbound texts, and the
full fan/rival meltdown ride later slices on the same spine.
"""
from __future__ import annotations

import hashlib
import random
import re
import threading
from typing import Any

from . import cache, customization, directory, llm, narrative, world_events
from . import messages as msg_store
from .modules import article_detail, base, feed, news_feed, phone

# A statement under this tier does not move the world (just a persona note).
_MIN_TIER = 1

# tier -> reaction budget. Tunable. fans split local/national; `dogpile` is how
# many fan posts pile directly onto the breaking post as replies (a visible
# meltdown thread) rather than standing alone in the timeline.
_PLAN = {
    1: {"reactions": 1, "fans_local": 1, "fans_nat": 0, "dogpile": 0},
    2: {"reactions": 3, "fans_local": 2, "fans_nat": 1, "dogpile": 1},
    3: {"reactions": 5, "fans_local": 4, "fans_nat": 4, "dogpile": 3},
}

# Engagement scale per account kind; lifted by tier (breaking news travels).
_ENGAGE = {
    "insider": (1500, 9000), "personality": (1200, 7000), "reporter": (500, 3500),
    "beat": (300, 2200), "analyst": (300, 2200), "columnist": (400, 2600),
    "brand": (2000, 12000), "local_fan": (20, 1200), "national_fan": (30, 1800),
}

# Media-ish profile kinds (mirrors directory._MEDIA_KINDS) so we know who can
# break a story and whose persona memory to update.
_MEDIA_KINDS = {"media", "analyst", "voter", "committee"}

# One background reaction at a time touches the cached feed; the event log has its
# own lock. A reaction is keyed to a specific (deterministic) statement, so this
# only serializes the read-modify-write of the cache, never drops work.
_feed_lock = threading.Lock()


# =========================================================================
# entry points
# =========================================================================
def react_async(contact: dict, message: str, dynasty: dict, *, year: int, week: int,
                channel: str, use_llm: bool, inbound: bool = True, min_tier: int | None = None) -> None:
    """Fire-and-forget reaction so the texting endpoint returns immediately. The
    coach sees the reply land; the world's tweets follow a beat later (the frontend
    notices via the world-version bump on /api/state and refreshes the feed)."""
    def _run() -> None:
        try:
            react(contact, message, dynasty, year=year, week=week, channel=channel,
                  use_llm=use_llm, inbound=inbound, min_tier=min_tier)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


# Channels that are PUBLIC and on the record (a press conference). Public remarks
# are fair game for the whole media universe and are never reported anonymously.
_PUBLIC_CHANNELS = {"Press conference"}


def _is_media_statement(contact: dict | None, channel: str) -> bool:
    """True when the coach is talking TO the media (a reporter), so a leak/quote is
    a legitimate scoop. Private shop talk with his own staff/players is not."""
    contact = contact or {}
    return (channel == "Media" or (contact.get("profile") or {}).get("kind") in _MEDIA_KINDS
            or contact.get("category") == "Media")


def react(contact: dict, message: str, dynasty: dict, *, year: int, week: int,
          channel: str, use_llm: bool, inbound: bool = True, min_tier: int | None = None) -> dict[str, Any]:
    """Judge a coach statement and, when it is newsworthy, write the cascade.
    Returns a small outcome dict ({tier, events, ...}); the durable result is the
    world-event log + the patched feed cache.

    `inbound` controls whether touched people text the coach back. The weekly
    presser cascade sets it False so the (presser-aware) weekly inbound owns those
    personal texts and the coach is not double-texted about the same moment."""
    message = (message or "").strip()
    if not message:
        return {"tier": 0}

    public = channel in _PUBLIC_CHANNELS

    # Cheap pre-filter: pure conversational filler ("ok thanks coach", "lol") never
    # moves the world, so skip the classifier call entirely. Conservative by design
    # (only obvious filler matches), so a real statement always reaches the classifier.
    # A public statement (a presser) is never filler, so it is exempt.
    if not public and _is_trivial(message):
        return {"tier": 0, "skipped": "trivial"}

    assessment = classify(contact, message, dynasty, year=year, week=week, use_llm=use_llm, public=public)
    tier = _coerce_tier(assessment.get("tier"))

    # Guardrail against a small model over-rating. The keyword heuristic is the
    # CEILING for any statement that is not a deliberate leak to a reporter: routine
    # coachspeak does not move the world, and that includes a normal press conference
    # (a coach saying his team competed and they are onto the next week is NOT
    # breaking news). Only a statement the heuristic also reads as real, a firing or
    # departure, a season-ending injury, a transfer/commit, a pointed shot at a
    # player or rival, can rise to a real story and detonate the feed. Media-channel
    # leaks are the one exemption, that is the intended scoop path.
    if not _is_media_statement(contact, channel):
        tier = min(tier, _coerce_tier(_classify_mock(message).get("tier")))
    assessment["tier"] = tier

    # Even a nothing-burger updates the reporter's memory of the coach.
    _note_persona(year, contact, message, channel)

    # A caller can demand a higher bar. The press conference passes min_tier=2 so a
    # routine presser (proud of the guys, onto the next week) never spawns feed
    # posts; only a real story (a meltdown, a firing, an injury) detonates.
    floor = _MIN_TIER if min_tier is None else max(_MIN_TIER, min_tier)
    if tier < floor:
        return {"tier": tier, "assessment": assessment, "events": 0, "below_floor": floor}

    posts = _compose(dynasty, contact, message, assessment, year=year, week=week,
                     channel=channel, use_llm=use_llm, public=public)
    if not posts:
        return {"tier": tier, "assessment": assessment, "events": 0}

    stmt_id = _statement_id(year, week, contact, message)
    origin_id = posts[0]["id"]
    evs: list[dict[str, Any]] = [{
        "id": stmt_id, "type": "coach_statement", "week": week, "tier": tier, "reacts_to": None,
        "payload": {"contact_id": (contact or {}).get("id"), "name": (contact or {}).get("name"),
                    "channel": channel, "text": message, "assessment": assessment},
    }]
    for i, p in enumerate(posts):
        evs.append({
            "id": p["id"], "type": ("quote" if p.get("quote_of") else "tweet"),
            "week": week, "tier": tier,
            "reacts_to": stmt_id if i == 0 else origin_id,
            "payload": p,
        })
    # A real story (tier 2+) also gets written up: the reporter files an article,
    # and a blockbuster (tier 3) leads the top-stories slider.
    news_evs = _compose_news_events(dynasty, contact, message, assessment, posts[0], stmt_id,
                                    year=year, week=week, use_llm=use_llm)
    evs.extend(news_evs)

    # ...and the people it touches reach out: the AD, players, recruits, rivals
    # text the coach reacting to the news (tier 2+). Delivery is event-keyed, so it
    # is deduped per statement and independent of the weekly inbound pass. Skipped
    # for the presser cascade (inbound=False), where the weekly inbound owns the
    # personal texts so the coach is not pinged twice about the same moment.
    inbound_evs = _react_inbound(dynasty, contact, message, assessment, stmt_id,
                                 year=year, week=week, use_llm=use_llm) if inbound else []
    evs.extend(inbound_evs)

    world_events.add_events(year, evs)
    _patch_feed_cache(year, week)
    if news_evs:
        _patch_news_cache(year, week)
    if tier >= 2:
        _seed_narrative(year, week, dynasty, message, assessment)
    return {"tier": tier, "assessment": assessment, "events": len(posts), "articles": len(news_evs),
            "texts": len(inbound_evs), "post_ids": [p["id"] for p in posts]}


# =========================================================================
# 1. classify (assignment desk)
# =========================================================================
_CLASSIFY_SYSTEM = (
    "You are the assignment editor for a college football media universe. You read "
    "what a head coach just said to someone and judge ONLY how newsworthy it is and "
    "what kind of statement it is. You never write articles or posts. Be conservative: "
    "routine coachspeak (cliches, motivation, vague optimism, normal game talk) is NOT "
    "news. Real news is a job/firing/retirement, a serious injury or suspension, a "
    "transfer or recruiting decision, a pointed shot at a player or rival, or a genuine "
    "confirmation or denial of something big."
)


def classify(contact: dict, message: str, dynasty: dict, *, year: int, week: int,
             use_llm: bool, public: bool = False) -> dict[str, Any]:
    if use_llm and base.llm_available():
        try:
            return _classify_llm(contact, message, dynasty, year, week, public=public)
        except Exception:
            pass
    return _classify_mock(message)


def _classify_llm(contact: dict, message: str, dynasty: dict, year: int, week: int,
                  *, public: bool = False) -> dict[str, Any]:
    coach = ((dynasty.get("team") or {}).get("head_coach") or {}).get("name") or "the head coach"
    if public:
        source_line = (
            f"{coach} (head coach of {(dynasty.get('team') or {}).get('name')}) said this PUBLICLY, on the "
            f"record, at his post-game press conference:\n\n\"{message}\"\n\n"
            "These remarks are public, so the whole media universe can react to them. Judge how newsworthy "
            "they are.")
    else:
        who = f"{(contact or {}).get('name', 'someone')} ({(contact or {}).get('role', '')}, {(contact or {}).get('category', '')})"
        source_line = (
            f"{coach} (head coach of {(dynasty.get('team') or {}).get('name')}) just sent this private "
            f"message to {who}:\n\n\"{message}\"\n\n")
    prompt = (
        source_line +
        "Judge it. Return STRICT JSON:\n"
        '{"tier": 0|1|2|3, "intent": "leak|confirm|deny|no_comment|praise|criticism|off_hand|info", '
        '"on_record": true|false, "anonymous": true|false, '
        '"topic": "carousel|injury|portal|recruiting|performance|player|opponent|controversy|general", '
        '"sentiment": "positive|negative|neutral", "subjects": ["names or things implicated"], '
        '"summary": "one neutral sentence describing the newsworthy claim, or empty if none"}\n\n'
        "tier 0 = not news (ignore it). 1 = minor beat note. 2 = a real story. 3 = blockbuster "
        "(a coach leaving/being fired, a star out for the year, a shocking decision). A coach simply "
        "expressing confidence or expectations about his own player or an upcoming game is normal game "
        "talk: tier 0, or at most tier 1, never a real story. If he asks for it to be leaked or put out, "
        "set intent=leak, on_record=false, anonymous=true. If he says off the record, on_record=false. "
        "JSON only."
    )
    res = llm.generate_json(_CLASSIFY_SYSTEM, prompt, grounding=base.reactive_grounding(dynasty, year, week),
                            max_tokens=400, temperature=0.2)
    if not isinstance(res, dict):
        return _classify_mock(message)
    res["tier"] = _coerce_tier(res.get("tier"))
    res.setdefault("intent", "info")
    res.setdefault("topic", "general")
    res.setdefault("sentiment", "neutral")
    res.setdefault("subjects", [])
    res.setdefault("on_record", True)
    res.setdefault("anonymous", res.get("intent") == "leak")
    res.setdefault("summary", "")
    return res


def _classify_mock(message: str) -> dict[str, Any]:
    """A keyword heuristic so the cascade still shapes-works with the LLM off (the
    default dev path). Conservative: only clear signals move the world."""
    m = message.lower()

    def has(*ks: str) -> bool:
        return any(k in m for k in ks)

    intent, on_record, anonymous = "info", True, False
    if has("leak", "break this", "put it out", "get it out there", "run with it", "report it"):
        intent, on_record, anonymous = "leak", False, True
    if has("off the record", "between us", "dont print", "don't print", "keep this quiet"):
        on_record = False

    topic, tier, sentiment = "general", 0, "neutral"
    if has("leaving", "step down", "stepping down", "step away", "retire", "retiring", "resign") \
            or ("taking the" in m and "job" in m) or ("accept" in m and "job" in m) \
            or has("fired", "let go", "relieved of", "out as head") \
            or has("won't be coaching", "wont be coaching", "not be coaching here",
                   "not be here long", "might be done", "won't be here long"):
        topic, tier, sentiment = "carousel", 3, "negative"
    elif has("out for the season", "season-ending", "torn", "acl", "surgery", "done for the year",
             "suspend", "suspension", "arrested", "dismissed from"):
        topic, tier, sentiment = "injury", 2, "negative"
    elif has("transfer", "portal", "decommit", "entering the"):
        topic, tier, sentiment = "portal", 2, "negative"
    elif has("commit", "committed", "flip", "pledged", "signing day"):
        topic, tier, sentiment = "recruiting", 2, "positive"
    elif has("fire the staff", "fire the whole staff", "fire my staff", "firing the staff", "blow it up") \
            or has("benched", "demote", "unacceptable", "embarrassing", "not good enough",
                   "have to be better"):
        topic, tier, sentiment = "performance", 2, "negative"
    elif has("proud", "played great", "special", "stepped up", "unbelievable", "dominant",
             "statement win", "balling out"):
        topic, tier, sentiment = "performance", 1, "positive"

    if intent == "leak" and tier < 2:
        tier = 2  # an explicit leak request is itself a signal something is up

    return {"tier": tier, "intent": intent, "on_record": on_record, "anonymous": anonymous,
            "topic": topic, "sentiment": sentiment, "subjects": [], "summary": _mock_summary(topic, message)}


def _mock_summary(topic: str, message: str) -> str:
    return {
        "carousel": "the head coach is expected to leave for another job",
        "injury": "a significant injury or availability situation in the program",
        "portal": "transfer portal movement around the program",
        "recruiting": "a recruiting development for the program",
        "performance": "the coach's pointed read on the team's performance",
    }.get(topic, "")


def _coerce_tier(v: Any) -> int:
    try:
        return max(0, min(3, int(v)))
    except (TypeError, ValueError):
        return 0


# Pure-filler words. A short message made up only of these is conversational
# noise (acknowledgements, greetings, pleasantries) and is dropped before the
# classifier runs. Kept deliberately small so anything with real content (a name,
# a verb like "leaving", "out", "committed") falls through to classification.
_FILLER = {
    "ok", "okay", "k", "kk", "yes", "no", "yep", "yeah", "nah", "sure", "thanks",
    "thank", "ty", "cool", "lol", "haha", "lmao", "bet", "word", "facts", "fr",
    "yessir", "got", "it", "sounds", "good", "great", "nice", "perfect", "love",
    "appreciate", "preciate", "you", "coach", "yo", "hey", "hi", "hello", "morning",
    "later", "peace", "np", "done", "copy", "agreed", "true", "right", "exactly",
    "same", "a", "the", "to", "for", "and", "u", "im", "i'm", "we", "all", "of",
}


def _is_trivial(message: str) -> bool:
    """True for pure conversational filler that should never trigger a reaction."""
    s = message.strip().lower()
    if len(s) <= 3:
        return True
    toks = re.findall(r"[a-z']+", s)
    if not toks:
        return True  # punctuation / emoji only
    return len(toks) <= 6 and all(t in _FILLER for t in toks)


# =========================================================================
# 3. compose (the cascade, reusing the feed's accounts + voice)
# =========================================================================
def _compose(dynasty: dict, contact: dict, message: str, assessment: dict, *,
             year: int, week: int, channel: str, use_llm: bool, public: bool = False) -> list[dict[str, Any]]:
    plan = _PLAN.get(assessment["tier"], _PLAN[1])
    accounts = feed._accounts(dynasty, year, week)
    origin = _origin_author(contact, accounts, channel)

    media = [a for a in accounts
             if a["kind"] in ("insider", "reporter", "personality", "analyst", "columnist", "beat")
             and a["id"] != origin["id"]]
    local_fans = [a for a in accounts if a["kind"] == "local_fan"]
    nat_fans = [a for a in accounts if a["kind"] == "national_fan"]

    stmt_id = _statement_id(year, week, contact, message)
    rng = random.Random(stmt_id + ":pick")
    rng.shuffle(media)
    rng.shuffle(local_fans)
    rng.shuffle(nat_fans)
    react_media = media[: plan["reactions"]]
    fan_accts = local_fans[: plan["fans_local"]] + nat_fans[: plan["fans_nat"]]

    content: dict[str, Any] | None = None
    if use_llm and base.llm_available():
        try:
            content = _compose_llm(dynasty, contact, message, assessment, origin,
                                   react_media, fan_accts, year, week, public=public)
        except Exception:
            content = None
    if not content:
        content = _compose_mock(dynasty, contact, message, assessment, origin, react_media, fan_accts)

    # A coach statement only breaks when it is genuinely combustible (tier 3): a leak,
    # a firing-watch quote, a presser that detonates. An ordinary newsworthy remark
    # (tier 2) still hits the timeline, but not as breaking news.
    return _assemble(content, assessment, origin, react_media, fan_accts, stmt_id,
                     dogpile=plan.get("dogpile", 0),
                     breaking=assessment.get("tier", 0) >= 3)


def _origin_author(contact: dict, accounts: list[dict], channel: str) -> dict[str, Any]:
    """Who breaks the story. A media contact breaks it himself (Klatt tweets); a
    leak out of a private channel, or a public press conference, is carried by a
    national insider/personality quoting it."""
    contact = contact or {}
    if channel in _PUBLIC_CHANNELS:
        media = [a for a in accounts if a["kind"] in ("insider", "personality", "reporter")]
        return media[0] if media else _author_from_contact({"name": "Insider"})
    is_media = channel == "Media" or (contact.get("profile") or {}).get("kind") in _MEDIA_KINDS \
        or contact.get("category") == "Media"
    if is_media and contact.get("name"):
        match = next((a for a in accounts if a["name"] == contact["name"]), None)
        return match or _author_from_contact(contact)
    insiders = [a for a in accounts if a["kind"] == "insider"] \
        or [a for a in accounts if a["kind"] in ("reporter", "personality")]
    return insiders[0] if insiders else _author_from_contact(contact or {"name": "Insider"})


def _author_from_contact(contact: dict) -> dict[str, Any]:
    name = contact.get("name") or "Reporter"
    return {
        "id": f"media:{feed._slug(name)}", "name": name, "handle": feed._handle(name),
        "avatar": feed._initials(name), "image": contact.get("image", ""), "verified": True,
        "kind": "insider", "scope": "national", "textable": True, "text_kind": "media",
        "team_espn_id": None,
    }


def _assemble(content: dict, assessment: dict, origin: dict, react_media: list[dict],
              fan_accts: list[dict], stmt_id: str, *, dogpile: int = 0,
              breaking: bool = False) -> list[dict[str, Any]]:
    tier = assessment["tier"]
    break_text = (content.get("break") or "").strip()
    if not break_text:
        return []
    by_id = content.get("by_id") or {}

    # Stamp the whole cascade into a tiny window at the very top of the timeline
    # (well under the feed's own minimum age) so the breaking moment reads as one
    # burst that "just happened", ahead of the week's earlier posts.
    def _hours(i: int) -> float:
        return round(0.02 + i * 0.01, 3)

    origin_pid = f"{stmt_id}:0"
    # The BREAKING banner is reserved for genuinely big news (the caller decides via
    # `breaking`). Routine stories (a recruiting visit, normal game talk) still post
    # to the timeline in real time, just as an ordinary tweet.
    origin_post = _post(origin, break_text, pid=origin_pid, hours=_hours(0), tier=tier, breaking=breaking)
    posts = [origin_post]
    quoted = {"author_name": origin["name"], "handle": origin["handle"], "avatar": origin["avatar"],
              "verified": origin.get("verified", False), "text": origin_post["text"],
              "image": origin.get("image", "")}

    i = 1
    for a in react_media:
        txt = (by_id.get(a["id"]) or "").strip()
        if not txt:
            continue
        posts.append(_post(a, txt, pid=f"{stmt_id}:{i}", hours=_hours(i),
                           tier=tier, quote_of=origin_pid, quoted=quoted))
        i += 1
    j = 0
    for a in fan_accts:
        txt = (by_id.get(a["id"]) or "").strip()
        if not txt:
            continue
        # The first `dogpile` fans pile onto the breaking post as a reply thread;
        # the rest stand alone in the timeline.
        reply_to = origin_pid if j < dogpile else None
        posts.append(_post(a, txt, pid=f"{stmt_id}:{i}", hours=_hours(i), tier=tier, reply_to=reply_to))
        i += 1
        j += 1
    return posts


def _clean_text(text: str, handle: str = "") -> str:
    """Final hygiene on a generated post before it hits the timeline. Strips a
    leading self-@mention (the app already shows the author's @handle, so a post
    that opens by quoting its own handle, e.g. "@klatt Sources tell me...", reads
    as a glitch) and runs the shared sanitizer (HTML/embed markup, dashes, emojis),
    which world posts otherwise bypass (they are patched straight into the cache)."""
    s = str(text or "").strip()
    if handle:
        s = re.sub(rf"^\s*@{re.escape(handle)}\b[\s:]*", "", s, flags=re.IGNORECASE).strip()
    return base.sanitize(s)


def _post(acct: dict, text: str, *, pid: str, hours: float, tier: int, breaking: bool = False,
          quote_of: str | None = None, quoted: dict | None = None,
          reply_to: str | None = None) -> dict[str, Any]:
    return {
        "id": pid,
        "author_id": acct["id"], "author_name": acct["name"], "handle": acct["handle"],
        "avatar": acct["avatar"], "image": acct.get("image", ""), "verified": acct.get("verified", False),
        "kind": acct["kind"], "team_espn_id": acct.get("team_espn_id"),
        "textable": acct.get("textable", False), "text_kind": acct.get("text_kind"),
        "text": _clean_text(text, acct.get("handle", "")),
        "ref": None, "reply_to": reply_to, "quote_of": quote_of, "quoted": quoted,
        "breaking": bool(breaking),
        "hours_ago": hours, "ts": round(1_000_000 - hours, 4), "timestamp": _label(hours),
        "metrics": _metrics(acct["kind"], tier, pid),
    }


def _label(hours: float) -> str:
    if hours < 1:
        return "now"
    if hours < 24:
        return f"{int(round(hours))}h ago"
    return f"{int(hours // 24)}d ago"


def _metrics(kind: str, tier: int, seed: str) -> dict[str, int]:
    lo, hi = _ENGAGE.get(kind, (50, 800))
    rng = random.Random(seed + ":m")
    likes = int(rng.randint(lo, hi) * (1.0 + 0.6 * tier))
    reposts = int(likes * rng.uniform(0.14, 0.34))
    replies = int(likes * rng.uniform(0.08, 0.22))
    return {"likes": likes, "reposts": reposts, "replies": replies}


# --- LLM composition ------------------------------------------------------
def _compose_llm(dynasty: dict, contact: dict, message: str, assessment: dict, origin: dict,
                 react_media: list[dict], fan_accts: list[dict], year: int, week: int,
                 *, public: bool = False) -> dict[str, Any]:
    coach = ((dynasty.get("team") or {}).get("head_coach") or {}).get("name") or "the coach"
    roster = react_media + fan_accts
    roster_txt = "\n".join(
        f"  [{a['id']}] @{a['handle']} ({a['name']}, {a['kind']}, {a.get('scope', 'national')}): {a.get('lean', '')}"[:220]
        for a in roster)
    anon = (not public) and (assessment.get("anonymous") or assessment.get("intent") == "leak")
    if public:
        statement_line = (
            f"{coach} said this PUBLICLY, on the record, at his post-game press conference: \"{message}\".\n")
        sourcing = (f"Quote or paraphrase {coach}'s actual public remarks and attribute them to him by name. "
                    "These are on the record, so no anonymous sourcing.")
    else:
        statement_line = (
            f"{coach} just privately told {(contact or {}).get('name', 'a reporter')} "
            f"({(contact or {}).get('role', '')}): \"{message}\".\n")
        sourcing = ("Report it with anonymous sourcing, phrased in your own natural words, and do NOT name "
                    f"{coach} as your source or quote him." if anon else
                    f"You may attribute it to {coach} and quote what he told you.")
    prompt = (
        statement_line +
        f"Editor's read: tier {assessment['tier']} {assessment.get('topic')}, "
        f"{assessment.get('summary') or 'newsworthy'}.\n\n"
        f"Write the moment this hits the timeline.\n"
        f"1) THE BREAK: one post from {origin['name']} breaking the news. {sourcing}\n"
        f"2) REACTIONS: one post from EACH account below, in its own voice, reacting to the break "
        f"(media add reporting or analysis, fans react raw). Use the account's id.\n{roster_txt}\n\n"
        'Return STRICT JSON: {"break": "<the breaking post>", '
        '"posts": [{"author_id": "<id from the list>", "text": "<post>"}]}. '
        "Each value is the post BODY only: do NOT begin a post with the author's own @handle or name "
        "(the app already shows who posted it), and write plain text only (no HTML, no embed code, no "
        "surrounding quotation marks). Short, punchy, real social voice. No emojis, no hashtag spam, "
        "no dashes as punctuation. JSON only."
    )
    res = llm.generate_json(feed.SYSTEM, prompt, cached_context=base.news_context(dynasty, year, week),
                            grounding=base.reactive_grounding(dynasty, year, week), max_tokens=1400, temperature=0.8)
    if not isinstance(res, dict):
        return {}
    by_id: dict[str, str] = {}
    for p in res.get("posts") or []:
        if isinstance(p, dict) and p.get("author_id") and p.get("text"):
            by_id[p["author_id"]] = str(p["text"]).strip()
    return {"break": str(res.get("break") or "").strip(), "by_id": by_id}


# --- mock composition -----------------------------------------------------
def _compose_mock(dynasty: dict, contact: dict, message: str, assessment: dict, origin: dict,
                  react_media: list[dict], fan_accts: list[dict]) -> dict[str, Any]:
    team = dynasty.get("team", {}) or {}
    coach = (team.get("head_coach") or {}).get("name") or "the coach"
    school = team.get("school") or team.get("name") or "the program"
    word = feed._team_word(team.get("name", ""), team.get("nickname", ""))
    topic = assessment.get("topic", "general")
    dest = _destination(message) if topic == "carousel" else None
    anon = assessment.get("anonymous") or assessment.get("intent") == "leak"
    sentiment = assessment.get("sentiment", "neutral")

    by_id: dict[str, str] = {}
    for a in react_media:
        by_id[a["id"]] = _mock_react(a, topic, coach, school, dest)
    for a in fan_accts:
        by_id[a["id"]] = _mock_fan(a, topic, coach, word, dest, sentiment)
    return {"break": _mock_break(topic, anon, coach, school, dest), "by_id": by_id}


def _destination(message: str) -> str | None:
    for pat in (r"the ([A-Z][A-Za-z&.\-]+(?: [A-Z][A-Za-z&.\-]+)?) job",
                r"\bto ([A-Z][A-Za-z&.\-]+(?: [A-Z][A-Za-z&.\-]+)?)\b"):
        m = re.search(pat, message)
        if m:
            return m.group(1).strip()
    return None


def _mock_break(topic: str, anon: bool, coach: str, school: str, dest: str | None) -> str:
    if topic == "carousel":
        if dest:
            return (f"Sources: {coach} is finalizing a move to {dest} and is expected to leave {school}. "
                    f"A search at {school} would follow." if anon
                    else f"{coach} tells me he is leaving {school} to take the {dest} job. Stunning.")
        return (f"Sources: {coach} is expected to step away from {school}. More to come." if anon
                else f"{coach} tells me he is stepping away from {school}.")
    if topic == "injury":
        return f"Sources: {school} is managing a significant availability situation. Working to confirm specifics."
    if topic == "portal":
        return f"Sources: expecting roster movement at {school}. Keeping an ear to the ground."
    if topic == "recruiting":
        return f"Hearing {school} is trending in a big way on the trail. Recruiting news could be coming."
    if topic == "performance":
        return f"{coach} did not hide from it talking about {school} today. Pointed, honest read on where they are."
    return f"Caught up with {coach} at {school} today. A couple of things worth watching."


def _variant(pool: list[str], acct: dict) -> str:
    """Pick a line from a pool deterministically per account, so several accounts
    of the same kind reacting to one story do not echo each other word for word."""
    pool = [p for p in pool if p]
    if not pool:
        return ""
    h = int(hashlib.sha1((acct.get("id", "") or acct.get("name", "")).encode("utf-8")).hexdigest(), 16)
    return pool[h % len(pool)]


def _mock_react(acct: dict, topic: str, coach: str, school: str, dest: str | None) -> str:
    kind = acct["kind"]
    to = dest or "a bigger job"
    if topic == "carousel":
        if kind in ("insider", "reporter", "beat"):
            return _variant([
                f"Hearing the same on {coach}. If he leaves {school}" + (f" for {dest}" if dest else "")
                + ", expect the dominoes to fall quickly.",
                f"Told a push for {coach} was heating up. Now it sounds close to done.",
                f"{school} sources bracing for {coach} to walk. This is moving fast.",
            ], acct)
        if kind in ("personality", "columnist"):
            return _variant([
                f"If {coach} really walks away from {school}, that reshapes the entire sport.",
                f"Hard to overstate what losing {coach} would mean for {school}. Program-altering.",
                f"{coach} to {to} would be the move of the coaching cycle. Stunner.",
            ], acct)
        if kind == "analyst":
            return _variant([
                f"This rocks every board {coach} was working. Watch the commits over the next 48 hours.",
                f"Recruits are already texting. A {coach} exit could crack {school}'s class wide open.",
            ], acct)
        return f"{coach} to {dest or 'a new job'}? wow."
    if topic == "injury":
        return _variant([
            f"If true, this changes how you have to look at {school} the rest of the way.",
            f"Big availability question for {school} now. Worth tracking who steps in.",
        ], acct)
    if topic == "portal":
        return _variant([
            f"Worth watching how {school} backfills if this is real.",
            f"Portal season at {school} just got more interesting.",
        ], acct)
    if topic == "recruiting":
        return _variant([
            f"Momentum is a real thing on the trail and {school} clearly has it right now.",
            f"{school} is closing. You can feel the board tilting their way.",
        ], acct)
    if topic == "performance":
        return _variant([
            f"Fair read from {coach}. The tape on {school} backs it up.",
            f"{coach} not sugarcoating it. Respect the honesty about {school}.",
        ], acct)
    return f"Keeping an eye on this {school} situation."


def _mock_fan(acct: dict, topic: str, coach: str, word: str, dest: str | None, sentiment: str) -> str:
    local = acct["kind"] == "local_fan"
    if topic == "carousel":
        return _variant([
            f"no no no he cannot leave us, {word} nation is not ok rn",
            f"i refuse to believe coach is gone. somebody tell me this is fake",
            f"if {coach} walks i need a minute. this hurts bad",
        ], acct) if local else _variant([
            f"{word} fans acting shocked lol. {coach} gone and that program is cooked",
            f"imagine being a {word} fan today, couldnt be me",
            f"{coach} bailing on {word} is the funniest thing on my timeline",
        ], acct)
    if sentiment == "positive":
        return (_variant([f"love to hear this from coach, we are so back", "this is the energy i needed today"], acct)
                if local else f"{word} fans hyping themselves up again, every single year")
    if sentiment == "negative":
        return (_variant(["this one hurts. we have to be a lot better", "cannot keep doing this to ourselves man"], acct)
                if local else f"{word} in shambles and i am here for every second of it")
    return ("never a normal week with this team" if local else f"{word} doing {word} things again")


def _mock_react_national(acct: dict) -> str:
    """A generic, subject-free media reaction for a NATIONAL story (about another
    program), so it never names the user's coach or school by mistake."""
    kind = acct["kind"]
    if kind in ("personality", "columnist"):
        return _variant([
            "If this holds up, it reshapes the entire national picture.",
            "Massive development. Hard to overstate the fallout from this one.",
            "This is the kind of news that swings the whole race.",
        ], acct)
    if kind == "analyst":
        return _variant([
            "Watch the ripple effects on the recruiting trail over the next 48 hours.",
            "Boards everywhere just shifted. This one travels.",
        ], acct)
    return _variant([
        "Hearing the same. This moves the national picture in a big way.",
        "Told this was coming. Now it sounds close to done.",
        "Sources confirming pieces of this. Developing fast.",
    ], acct)


def _mock_fan_national(acct: dict) -> str:
    return _variant([
        "the timeline is in shambles over this lmaooo",
        "not me refreshing for updates every five seconds",
        "college football never misses with the chaos man",
        "this sport is unserious and i love it here",
    ], acct)


# =========================================================================
# 3b. compose news (the reporter files the story)
# =========================================================================
# topic -> the news category (and thus accent) a coach-caused article files under.
_ARTICLE_CATEGORY = {
    "carousel": "Coaching carousel", "portal": "Transfer portal", "recruiting": "Recruiting",
    "injury": "Injury", "performance": "Program",
}


def _compose_news_events(dynasty: dict, contact: dict, message: str, assessment: dict,
                         origin_post: dict, stmt_id: str, *, year: int, week: int,
                         use_llm: bool) -> list[dict[str, Any]]:
    """tier 2+ -> the breaking reporter files an article; tier 3 also leads the
    top-stories slider. Each is expanded into a full reader page so it opens like
    any other article."""
    tier = assessment["tier"]
    if tier < 2:
        return []
    article = _build_article(dynasty, contact, message, assessment, origin_post)
    article["id"] = f"{stmt_id}:art"
    # Build the reader page deterministically from the article body (no LLM 'expand'
    # call). The cascade runs in a background thread off a coach statement; an LLM
    # expansion here was costing 40-65s and, when several statements fired, flooded
    # the single local model and starved the foreground press conference.
    try:
        article["detail"] = article_detail.build_detail(article, dynasty)
    except Exception:
        pass
    evs: list[dict[str, Any]] = [{
        "id": article["id"], "type": "article", "week": week, "tier": tier, "reacts_to": stmt_id,
        "payload": {"scope": "program", "article": article},
    }]
    if tier >= 3:
        story = _build_top_story(article)
        story["id"] = f"{stmt_id}:top"
        try:
            story["detail"] = article_detail.build_detail(article, dynasty)
        except Exception:
            pass
        evs.append({"id": story["id"], "type": "top_story", "week": week, "tier": tier,
                    "reacts_to": stmt_id, "payload": {"story": story}})
    return evs


def _build_article(dynasty: dict, contact: dict, message: str, assessment: dict,
                   origin_post: dict) -> dict[str, Any]:
    team = dynasty.get("team", {}) or {}
    coach = (team.get("head_coach") or {}).get("name") or "the head coach"
    school = team.get("school") or team.get("name") or "the program"
    rec = (team.get("record") or {}).get("overall") or ""
    topic = assessment.get("topic", "general")
    dest = _destination(message) if topic == "carousel" else None
    # Only a media member gets the byline. When the story came out of a private
    # channel (the coach vented to his OC) or a public presser, the breaking media
    # account carries it, never the non-media person who was talked to/about.
    is_media = ((contact or {}).get("profile") or {}).get("kind") in _MEDIA_KINDS \
        or (contact or {}).get("category") == "Media"
    prof_rec = ((contact or {}).get("profile") or {}).get("record") or {}
    if is_media and (contact or {}).get("name"):
        reporter = contact["name"]
        outlet = contact.get("outlet") or prof_rec.get("outlet") or "national insider"
    else:
        reporter = origin_post.get("author_name") or "League sources"
        outlet = "national insider"
    category = _ARTICLE_CATEGORY.get(topic, "Program")
    headline, dek, body = _article_copy(topic, coach, school, dest, rec)
    return {
        "outlet": outlet, "reporter": reporter, "reliability": 90,
        "category": category, "accent": base.accent_for(category),
        "headline": headline, "dek": dek, "body": body, "timestamp": "now",
    }


def _article_copy(topic: str, coach: str, school: str, dest: str | None, rec: str) -> tuple[str, str, str]:
    rec_phrase = f" ({rec})" if rec else ""
    if topic == "carousel":
        headline = f"{coach} expected to leave {school}" + (f" for {dest}" if dest else "")
        dek = f"Sources say a move is close as {school} braces for a coaching search."
        body = (
            f"{coach} is finalizing a decision that would take him away from {school}, according to "
            "multiple people briefed on the situation"
            + (f", with {dest} prepared to make the hire" if dest else "") + ". "
            f"It would be a stunning turn for a program that sits{rec_phrase} this season.\n\n"
            f"A departure would trigger an immediate search at {school} and throw the recruiting class "
            "into question, with rival staffs already working the board. Nothing has been announced, but "
            "the expectation around the program is that an answer is coming soon.")
        return headline, dek, body
    if topic == "injury":
        headline = f"{school} facing a significant availability question"
        dek = "Sources point to a notable absence as the picture comes into focus."
        body = (f"{school} is managing a significant availability situation, sources said, one that could "
                f"reshape how the team lines up down the stretch{rec_phrase}.\n\n"
                "The staff has not detailed the specifics publicly, but those around the program expect it "
                "to factor into the plan in the coming weeks.")
        return headline, dek, body
    if topic == "portal":
        headline = f"Portal movement expected around {school}"
        dek = "Roster churn is brewing as the window approaches."
        body = (f"Expect movement on the {school} roster, sources said, the kind of churn that reshuffles "
                f"depth and opens snaps{rec_phrase}.\n\n"
                "How the staff backfills will say a lot about the direction of the program from here.")
        return headline, dek, body
    if topic == "recruiting":
        headline = f"{school} surging on the recruiting trail"
        dek = "Momentum is tilting the board as a decision nears."
        body = (f"{school} is closing on the trail, sources said, with the staff's pitch landing at the "
                "right time.\n\nA win here would ripple through the rest of the class, where momentum tends "
                "to compound.")
        return headline, dek, body
    if topic == "performance":
        headline = f"{coach} delivers a pointed message on where {school} stands"
        dek = "An honest, unvarnished read on the state of the team."
        body = (f"{coach} did not hide from it, offering a direct assessment of {school}{rec_phrase} and what "
                "has to change.\n\nThe candor is the story: a program putting its issues on the table rather "
                "than papering over them.")
        return headline, dek, body
    headline = f"{coach} stirs the conversation around {school}"
    dek = "Remarks that are getting attention around the program."
    body = (f"{coach} said something worth noting about {school}{rec_phrase}, and it is making the rounds.\n\n"
            "Whether it amounts to anything is the open question, but it has people talking.")
    return headline, dek, body


def _build_top_story(article: dict) -> dict[str, Any]:
    body = article.get("body") or ""
    lede = body.split("\n\n", 1)[0] if body else article.get("dek", "")
    return {
        "category": article.get("category", "Coaching carousel"),
        "accent": article.get("accent"),
        "headline": article.get("headline", ""),
        "subheadline": article.get("dek", ""),
        "lede": lede,
        "byline": f"{article.get('reporter', 'League sources')}, {article.get('outlet', 'national insider')}",
    }


# =========================================================================
# 3c. compose inbound (the people it touches text the coach back)
# =========================================================================
# topic -> the order people reach out in. The budget (by tier) trims the tail. A
# carousel blockbuster lists two recruits, so the class visibly wavers (two
# different prospects reconsidering), not just one.
_REACTOR_ORDER = {
    "carousel": ["ad", "player", "recruit", "recruit", "rival"],
    "injury": ["ad", "player"],
    "portal": ["player", "ad"],
    "recruiting": ["recruit", "ad"],
    "performance": ["player", "ad"],
    "default": ["ad", "player"],
}

# How likely each touched person is to ACTUALLY text the coach, by tier. A
# blockbuster (a job, a star going down) pulls almost everyone in; a routine
# "real story" (a pointed performance take, a confident comment about a player)
# only sometimes prompts a text, so the coach is not pinged by his QB and AD
# every single time he gives an interview or mentions the team. Rolled per
# (statement, person), so it is stable for a given statement but varies across
# statements and people.
_REACH_CHANCE = {2: 0.35, 3: 0.9}


def _react_inbound(dynasty: dict, contact: dict, message: str, assessment: dict, stmt_id: str,
                   *, year: int, week: int, use_llm: bool) -> list[dict[str, Any]]:
    """tier 2+ -> a few relevant people text the coach reacting to the news. Reuses
    phone.compose_inbound (in-character, LLM with a mock fallback) and delivers
    event-keyed and unread. Returns inbound_text events for the cascade record."""
    tier = assessment["tier"]
    if tier < 2:
        return []
    team = dynasty.get("team", {}) or {}
    coach = (team.get("head_coach") or {}).get("name") or "coach"
    school = team.get("school") or team.get("name") or "the program"
    topic = assessment.get("topic", "general")
    sentiment = assessment.get("sentiment", "neutral")
    dest = _destination(message) if topic == "carousel" else None
    exclude = (contact or {}).get("name")

    budget = 5 if tier >= 3 else 2
    chance = _REACH_CHANCE.get(tier, 0.35)
    order = _REACTOR_ORDER.get(topic, _REACTOR_ORDER["default"])
    delivered_to: set[str] = set()
    kind_idx: dict[str, int] = {}
    evs: list[dict[str, Any]] = []
    for kind in order:
        if len(evs) >= budget:
            break
        idx = kind_idx.get(kind, 0)
        kind_idx[kind] = idx + 1
        person = _resolve_reactor(kind, dynasty, idx)
        if not person or person["id"] in delivered_to or person.get("name") == exclude:
            continue
        # Not everyone reaches out every time: roll a per-person chance so a
        # routine story only sometimes prompts a text. Seeded by the statement and
        # the person, so the outcome is stable across cache rebuilds for one
        # statement but independent for the next interview or mention.
        if random.Random(f"{stmt_id}:{person['id']}:reach").random() > chance:
            continue
        rtopic, mock = _reaction_copy(kind, topic, sentiment, coach, school, dest)
        try:
            msgs = phone.compose_inbound(person, dynasty, year=year, week=week, use_llm=use_llm,
                                         topic=rtopic, mock_pool=mock)
        except Exception:
            msgs = []
        if not msgs:
            continue
        items = [{"from": "them", "text": m, "unread": True} for m in msgs]
        if not msg_store.deliver_inbound(year, week, person["id"], items, key=stmt_id):
            continue
        delivered_to.add(person["id"])
        evs.append({
            "id": f"{stmt_id}:txt:{feed._slug(person['id'])}", "type": "inbound_text",
            "week": week, "tier": tier, "reacts_to": stmt_id,
            "payload": {"contact_id": person["id"], "name": person["name"],
                        "category": person.get("category"), "messages": msgs},
        })
    if evs:
        # Rebuild the phone roster so the new threads (and their unread badges) surface.
        cache.clear_module(year, week, phone.MODULE)
    return evs


def _resolve_reactor(kind: str, dynasty: dict, idx: int = 0) -> dict | None:
    """Resolve the idx-th person of a given kind. Only `recruit` supplies more than
    one (so a carousel story can show several prospects wavering); everyone else is
    a singleton (idx > 0 yields nothing)."""
    if kind == "ad":
        if idx:
            return None
        for c in customization.section("phone_contacts"):
            if (c.get("entity") or {}).get("kind") == "budget":
                return directory.by_id(c["id"])
        return None
    if kind == "player":
        if idx:
            return None
        players = (dynasty.get("roster") or {}).get("key_players") or []
        return directory.resolve(players[0].get("name"), "player") if players else None
    if kind == "recruit":
        rec = dynasty.get("recruiting") or {}
        pool = (rec.get("commits") or []) + sorted(rec.get("targets") or [],
                                                   key=lambda r: -(r.get("interest") or 0))
        return directory.resolve(pool[idx].get("name"), "recruit") if idx < len(pool) else None
    if kind == "rival":
        if idx:
            return None
        for hc in (customization.section("hot_seat_coaches") or []):
            if hc.get("coach"):
                return directory.resolve(hc["coach"], "opp_coach")
        return None
    return None


def _reaction_copy(kind: str, topic: str, sentiment: str, coach: str, school: str,
                   dest: str | None) -> tuple[str, list[str]]:
    """The framing (why they are texting) + an offline opener pool, per reactor and
    topic. The framing feeds phone.compose_inbound's LLM prompt; the pool is the
    mock fallback."""
    to = f" for {dest}" if dest else ""
    if topic == "carousel":
        if kind == "ad":
            return (f"You are the athletic director and just saw a report that {coach} is leaving {school}{to}. "
                    "You text him directly, alarmed, to find out if it is true and what is happening.",
                    ["coach what is this i'm hearing", f"tell me the report isn't true", "call me, we need to talk now"])
        if kind == "player":
            return (f"You play for {coach} at {school} and just saw the report that he might be leaving. You text "
                    "him, gutted and looking for the truth.",
                    ["coach is it true??", "say it aint so", "we ride with you but whats going on"])
        if kind == "recruit":
            return (f"You are a recruit tied to {school} and just saw the report the coach may leave. You text him "
                    "about what it means for your recruitment.",
                    ["coach i'm seeing the news", "what does this mean for me", "do i need to look elsewhere?"])
        if kind == "rival":
            return (f"You are a rival head coach who saw the report about {coach}. You send a cordial, lightly "
                    "probing note.", ["wild news if true coach", "you good? hit me if you wanna talk"])
    if topic == "injury":
        if kind == "ad":
            return (f"You are the AD and heard about a significant injury or availability situation at {school}. "
                    "You check in with the coach.", ["heard the news, how bad is it", "what do you need from me"])
        return (f"You play at {school} and heard a key teammate may be out. You text the coach about it.",
                ["coach is he gonna be ok", "next man up, we got this", "tough blow but we'll rally"])
    if topic == "portal":
        if kind == "player":
            return (f"You play at {school} and heard about portal movement on the roster. You text the coach.",
                    ["coach what's going on with the roster", "we still good?", "let me know how i can help"])
        return (f"You are the AD and heard about portal movement at {school}. You check in.",
                ["saw the portal chatter, you good on depth?", "let me know if we need to move on NIL"])
    if topic == "recruiting":
        if kind == "recruit":
            return (f"You are a recruit and saw the buzz about {school} surging on the trail. You text the coach, "
                    "fired up.", ["coach the momentum is real", "yall are different fr", "lets keep this going"])
        return (f"You are the AD and saw {school}'s recruiting momentum. You text encouragement.",
                ["love what i'm seeing on the trail", "tell me what you need to close"])
    if topic == "performance":
        if kind == "player":
            if sentiment == "positive":
                return (f"You play at {school} and saw the coach praise the group. You text him, appreciative.",
                        ["preciate you coach", "we eat", "onto the next one"])
            return (f"You play at {school} and saw the coach's pointed comments about the team. You text him, "
                    "owning it.", ["that's on us coach", "we'll be better, i promise", "hold us to it"])
        return (f"You are the AD and saw the coach's comments about {school}. You check in.",
                ["saw your comments, i'm with you", "let me know what you need"])
    return ("You saw the coach is in the news and you reach out to check in.",
            ["saw the news coach", "you good?", "here if you need anything"])


# =========================================================================
# 4. write (persist + surface + remember)
# =========================================================================
def _patch_feed_cache(year: int, week: int) -> None:
    """Fold the new reaction posts into this week's already-cached feed so they
    surface the moment the frontend refreshes, without a full re-roll. A no-op if
    the feed has not been generated yet (it will merge the events on first run)."""
    with _feed_lock:
        content = cache.get_module(year, week, feed.MODULE)
        if not isinstance(content, dict) or "posts" not in content:
            return
        content["posts"] = world_events.merge_feed_posts(content.get("posts") or [], year, week)
        cache.set_module(year, week, feed.MODULE, content)


def _patch_news_cache(year: int, week: int) -> None:
    """Fold coach-caused articles into this week's already-cached news feed and top
    stories so they surface the moment the frontend refreshes. A no-op for a bucket
    that has not been generated yet (it merges the events on its first run)."""
    with _feed_lock:
        nf = cache.get_module(year, week, "news_feed")
        if isinstance(nf, dict):
            cache.set_module(year, week, "news_feed", world_events.merge_news(nf, year, week))
        ts = cache.get_module(year, week, "top_stories")
        if isinstance(ts, dict) and isinstance(ts.get("stories"), list):
            ts["stories"] = world_events.merge_top_stories(ts["stories"], year, week)
            cache.set_module(year, week, "top_stories", ts)


def _seed_narrative(year: int, week: int, dynasty: dict, message: str, assessment: dict) -> None:
    """Record the storyline so it carries across weeks: every generator pulls
    narrative threads into its context, so next week's coverage and texts can
    follow up on an unresolved big statement instead of forgetting it."""
    team = dynasty.get("team", {}) or {}
    coach = (team.get("head_coach") or {}).get("name") or "the head coach"
    school = team.get("school") or team.get("name") or "the program"
    topic = assessment.get("topic", "general")
    if topic == "carousel":
        dest = _destination(message)
        summary = (f"{coach} is reported to be leaving {school}" + (f" for {dest}" if dest else "")
                   + f", a story that broke in week {week} and is still unresolved.")
        category = "Coaching carousel"
    else:
        # Keep the actual remark in the summary so the thread carries real
        # information (and so distinct statements stay distinct rather than
        # collapsing to one generic, repeated line, see narrative.add_thread).
        snippet = " ".join((message or "").split())
        if len(snippet) > 120:
            snippet = snippet[:117].rstrip() + "..."
        gist = (assessment.get("summary") or "").strip()
        summary = (f'{gist} (week {week}): "{snippet}"' if gist
                   else f'Week {week}, {coach} drew attention by saying: "{snippet}"')
        category = _ARTICLE_CATEGORY.get(topic, "Program")
    try:
        narrative.add_thread(year, week=week, category=category, summary=summary,
                             tags=["coach_statement", topic])
    except Exception:
        pass


def _note_persona(year: int, contact: dict, message: str, channel: str) -> None:
    contact = contact or {}
    is_media = channel == "Media" or (contact.get("profile") or {}).get("kind") in _MEDIA_KINDS \
        or contact.get("category") == "Media"
    if not is_media or not contact.get("name"):
        return
    try:
        narrative.update_persona(year, contact["name"],
                                 {"last_take": f"the coach told them: \"{message[:90]}\""})
    except Exception:
        pass


# =========================================================================
# reporter-origin cascade (the world reacts to what the NEWSROOM broke)
# =========================================================================
# react() above fires off something the COACH said. This fires off something a
# REPORTER broke: the week's newsroom coverage (an injury, a portal/recruiting
# move, the coach reportedly leaving, a big national shakeup) detonates the same
# way, the scoop hits the timeline as breaking news, other media and fans pile
# on, and (for stories about the user's program) the people it touches text the
# coach. It reuses the same compose/inbound spine, so the two reaction paths
# render and persist identically.

# How big a national story has to be to draw any reaction at all (the user only
# wants the BIG national news to ripple, not every carousel whisper about another
# program). Lighter than the program plan: media chatter and national fans, no
# local fans (they care about the user's team), no inbound texts.
_NATL_PLAN = {
    2: {"reactions": 2, "fans_local": 0, "fans_nat": 2, "dogpile": 0},
    3: {"reactions": 3, "fans_local": 0, "fans_nat": 3, "dogpile": 1},
}

# A news category maps to the same topic vocabulary the coach cascade uses, so
# the reaction generators (_mock_react / _mock_fan / _reaction_copy) and the
# inbound reactor order all work unchanged.
_CATEGORY_TOPIC = {
    "Coaching carousel": "carousel", "Injury": "injury", "Transfer portal": "portal",
    "Portal": "portal", "Recruiting": "recruiting", "Program": "performance",
    "Rivalry": "performance",
}

# Cap the cascades a single week can spawn so a chatty newsroom never floods the
# feed and phone. Program stories and bigger stories win the slots.
_MAX_NEWS_CASCADES = 6

_MEDIA_ACCT_KINDS = ("insider", "reporter", "personality", "analyst", "columnist", "beat")


def react_to_coverage(dynasty: dict, *, year: int, week: int, use_llm: bool) -> dict[str, Any]:
    """Read the week's newsroom coverage and, for every story that clears the bar,
    write the reaction cascade: a breaking post from the reporter who broke it,
    media reactions and fan posts, and (program stories only) texts from the AD,
    players, recruits, and rivals. Returns a small outcome dict; the durable result
    is the world-event log, the patched feed cache, and the delivered texts.

    Idempotent: events dedup by id and texts are delivered under a per-story key,
    so re-running the pipeline (prewarm, regenerate, the watcher) never doubles up."""
    # Hold the coach to his word: test any open promises against this week's save and
    # deliver a confrontation text for any he broke (keyed once, editorial promises).
    try:
        from .editorial import promises
        promises.check_due(dynasty, year, week)
    except Exception:
        pass
    try:
        cov = news_feed.coverage(dynasty, year=year, week=week, use_llm=use_llm)
    except Exception:
        return {"events": 0, "texts": [], "stories": []}

    scored = []
    seen_keys: set[tuple] = set()
    for story in _collect_coverage_stories(cov):
        a = _assess_story(story, dynasty)
        if a["tier"] < 2:
            continue
        key = _story_dedup_key(story, a, dynasty)
        if key in seen_keys:
            continue  # near-duplicate coverage (e.g. three articles on the same recruit's visit) reacts once
        seen_keys.add(key)
        scored.append((story, a))
    # Highest-impact first (program before national, then by tier), then cap.
    scored.sort(key=lambda sa: (0 if sa[1]["scope"] == "program" else 1, -sa[1]["tier"]))
    scored = scored[:_MAX_NEWS_CASCADES]

    # One shared context for the whole pass: a week-level seen-set (no two cascade
    # posts repeat, across ALL stories) and a small per-post LLM budget for the
    # media voices, scaled to the connected model.
    try:
        from .editorial import profile as ed_profile
        _budget = {"none": 0, "nano": 4, "small": 6, "mid": 10, "frontier": 12}.get(
            ed_profile.current().tier, 4) if use_llm else 0
    except Exception:
        _budget = 0
    cascade_ctx = {"seen": set(), "llm_budget": _budget}

    all_evs: list[dict[str, Any]] = []
    texts: list[dict[str, Any]] = []
    reacted: list[dict[str, Any]] = []
    for story, a in scored:
        stmt_id = _story_id(year, week, story)
        posts = _compose_story(dynasty, story, a, stmt_id, year=year, week=week, use_llm=use_llm,
                               cascade_ctx=cascade_ctx)
        if not posts:
            continue
        origin_pid = posts[0]["id"]
        for i, p in enumerate(posts):
            all_evs.append({
                "id": p["id"], "type": ("quote" if p.get("quote_of") else "tweet"),
                "week": week, "tier": a["tier"], "reacts_to": None if i == 0 else origin_pid,
                "payload": p,
            })
        # Only stories about the user's program pull people into his texts; a
        # blue-blood shake-up elsewhere is feed chatter, not a personal ping. Hot-seat /
        # carousel stories are the exception: the user IS the coach, so "are you leaving?"
        # texts from the AD, players, and recruits make no sense (that framing belongs to
        # OTHER programs' coaches). The media/feed cascade still runs; the personal texts
        # do not.
        if a["scope"] == "program" and a["topic"] != "carousel":
            story_text = _story_text(story)
            inbound_evs = _react_inbound(dynasty, None, story_text, a, stmt_id,
                                         year=year, week=week, use_llm=use_llm)
            all_evs.extend(inbound_evs)
            texts.extend(e["payload"] for e in inbound_evs)
        reacted.append({"id": stmt_id, "headline": story.get("headline"),
                        "scope": a["scope"], "topic": a["topic"], "tier": a["tier"]})

    if all_evs:
        world_events.add_events(year, all_evs)
        # Fold the breaking posts into the already-cached feed so they surface the
        # moment the frontend refreshes (a no-op when the feed has not been built
        # yet this week, which then merges the events on its first run).
        _patch_feed_cache(year, week)
    return {"events": len(all_evs), "texts": texts, "stories": reacted}


def _collect_coverage_stories(cov: dict) -> list[dict[str, Any]]:
    """The week's stories from the shared newsroom coverage (program + national +
    insider reports), each with a headline. Coach-caused articles are NOT here
    (they live in world_events and already got their own cascade through react),
    so a story is never reacted to twice."""
    out: list[dict[str, Any]] = []
    for key in ("program", "national", "insider_reports"):
        for s in cov.get(key) or []:
            if isinstance(s, dict) and s.get("headline"):
                out.append(s)
    return out


def _story_text(story: dict) -> str:
    return " ".join(str(story.get(k) or "") for k in ("headline", "dek", "body", "claim")).strip()


def _season_ending(hay: str) -> bool:
    return any(k in hay for k in ("season-ending", "out for the season", "out for the year",
                                  "done for the year", "torn", "acl", "lost for the"))


def _big_carousel(story: dict, hay: str) -> bool:
    """True only when a carousel item is a real, near-confirmed move, not idle
    speculation, so generic 'a job could open' whispers about other programs stay
    quiet."""
    status = (story.get("status") or "").lower()
    conf = story.get("confidence")
    if status == "corroborated" or (isinstance(conf, (int, float)) and conf >= 70):
        return True
    strong = ("fired", "out as", "stepping down", "step down", "retiring", "retire",
              "leaving", "has been hired", "agree to terms", "accepts the", "is finalizing")
    weak = ("could", "might", "rumor", "linked", "expected to open", "sooner than expected")
    return any(w in hay for w in strong) and not any(w in hay for w in weak)


def _national_shakeup(hay: str) -> bool:
    """A big national result worth a ripple (a top-five upset, a stunner), kept
    tight so routine national coverage (poll updates, Heisman watch) does not fire."""
    return any(w in hay for w in ("stunner", "stunning upset", "shocker", "massive upset",
                                  "upsets no", "knocks off no", "falls to unranked",
                                  "loses to unranked"))


def _is_preseason(dynasty: dict) -> bool:
    """True before any games have been played (week 1 with no results), when hot-seat
    and carousel speculation should not yet ripple into the world."""
    season = dynasty.get("season") or {}
    recent = (dynasty.get("schedule") or {}).get("recent_results") or []
    return int(season.get("week", 0) or 0) <= 1 and not recent


def _story_dedup_key(story: dict, assessment: dict, dynasty: dict) -> tuple:
    """A coarse identity for a story so near-duplicate coverage (several articles on the
    same recruit's visit, the same hot-seat take) reacts only once. Keyed by scope, topic,
    and the most prominent known person (recruit/commit/player) named in it; falls back to
    a normalized headline prefix when no known entity is mentioned."""
    hay = _story_text(story).lower()
    names: list[str] = []
    rec = dynasty.get("recruiting") or {}
    for grp in ("targets", "commits"):
        for r in rec.get(grp) or []:
            n = (r.get("name") or "").strip().lower()
            if n and n in hay:
                names.append(n)
    for p in (dynasty.get("roster") or {}).get("key_players") or []:
        n = (p.get("name") or "").strip().lower()
        if n and n in hay:
            names.append(n)
    subject = sorted(names)[0] if names else (story.get("headline") or "")[:40].strip().lower()
    return (assessment.get("scope"), assessment.get("topic"), subject)


def _assess_story(story: dict, dynasty: dict) -> dict[str, Any]:
    """Heuristic newsworthiness for a reporter-broken story: its tier, topic,
    scope (about the user's PROGRAM or NATIONAL), and sentiment. Cheap on purpose,
    no model call, so the weekly pass never floods the local model just to triage."""
    team = dynasty.get("team", {}) or {}
    marks = [str(team.get(k) or "").lower() for k in ("name", "school", "nickname")]
    marks.append(str(((team.get("head_coach") or {}).get("name") or "")).lower())
    hay = _story_text(story).lower()
    program = any(m and m in hay for m in marks)
    scope = "program" if program else (story.get("scope") or "national")

    km = _classify_mock(hay)  # keyword read, reused for topic fallback + sentiment
    topic = _CATEGORY_TOPIC.get(story.get("category") or "") or km.get("topic", "general")
    sentiment = km.get("sentiment", "neutral")

    tier = 0
    if scope == "program":
        if topic == "carousel":
            # A hot-seat / "uncertain future" story about the user's OWN coach is job-
            # security speculation, not a confirmed departure (the user cannot leave
            # himself). In the preseason it is just a preseason take, so keep it below the
            # cascade bar: it can sit in the news feed without detonating the phone and
            # feed before a single game has been played.
            tier = 1 if _is_preseason(dynasty) else 3
        elif topic == "injury":
            tier = 3 if _season_ending(hay) else 2
        elif topic in ("portal", "recruiting"):
            tier = 2
        elif topic == "performance":
            tier = 2 if sentiment == "negative" else 1
        else:
            tier = _coerce_tier(km.get("tier"))
    else:  # national: only the big stuff ripples
        if topic == "carousel" and _big_carousel(story, hay):
            tier = 2
        elif _national_shakeup(hay):
            tier = 2

    return {"tier": tier, "topic": topic, "scope": scope, "sentiment": sentiment,
            "intent": "report", "anonymous": False, "on_record": True,
            "summary": story.get("dek") or story.get("headline") or "", "subjects": []}


def _origin_for_reporter(story: dict, accounts: list[dict]) -> dict[str, Any]:
    """The account that breaks the story is the reporter who wrote it. Match the
    byline to a known feed account; otherwise synthesize a media account for them."""
    name = (story.get("reporter") or "").strip()
    if name:
        match = next((a for a in accounts if a.get("name") == name), None)
        return match or _author_from_contact({"name": name, "outlet": story.get("outlet")})
    insiders = [a for a in accounts if a["kind"] == "insider"] \
        or [a for a in accounts if a["kind"] in ("reporter", "personality")]
    return insiders[0] if insiders else _author_from_contact({"name": "Insider"})


def _article_ref(story: dict, scope: str) -> dict[str, Any]:
    """A feed article-ref (same shape feed._surface builds) so the breaking post
    carries the story and taps through to the full reader page."""
    return {"type": "article", "scope": scope, "headline": story.get("headline"),
            "outlet": story.get("outlet"), "reporter": story.get("reporter"),
            "category": story.get("category"), "accent": story.get("accent"), "article": story}


_BREAKING_DONE_DEAL = re.compile(
    r"\b(is out|has been fired|is fired|fired as|steps down|stepping down|named (?:the )?(?:new )?head coach|"
    r"agrees to|to take the|lands the|hired as|is the new|out as|relieved of)\b", re.IGNORECASE)
_BREAKING_RECRUIT_VERB = re.compile(
    r"\b(commits|committed|commitment|flips|flipped|signs|signed|pledges|decommit)\b", re.IGNORECASE)
# A recruit who has NOT done it yet: a recruiting-status story, not a signing. Catches
# "UNCOMMITTED ... has not signed" (the recruiting-battle dek) so it never reads as a
# signing just because "signed" appears inside a negation.
_NOT_YET = re.compile(
    r"\b(uncommitted|not (?:yet )?(?:signed|committed)|yet to (?:sign|commit|decide)|"
    r"still (?:being recruited|uncommitted|undecided|deciding|weighing)|no decision|hangs in|"
    r"awaits?|weighing|considering|leaning|could (?:commit|sign)|interest \d)\b", re.IGNORECASE)
_BREAKING_TOP_RECRUIT = re.compile(
    r"\b(5[-\s]?star|five[-\s]?star|4[-\s]?star|four[-\s]?star|no\.?\s*1\b|top[-\s]?(?:5|10)|blue[-\s]?chip)\b",
    re.IGNORECASE)
_BREAKING_UPSET = re.compile(r"\b(stuns|stunner|upsets?|shocks|shocker|topples|takes down no)\b", re.IGNORECASE)


def _story_is_breaking(story: dict, assessment: dict) -> bool:
    """True only for genuinely big news: a blockbuster (tier 3: combustible presser,
    confirmed program carousel, season-ending injury), a CONFIRMED coaching move (not
    a rumor), a TOP recruit actually signing/flipping (not interest or a visit), or a
    real upset. Everything else still posts in real time, just not as breaking."""
    tier = assessment.get("tier", 0)
    if tier >= 3:
        return True
    cat = (story.get("category") or "").lower()
    topic = assessment.get("topic", "")
    hay = f"{story.get('headline', '')} {story.get('dek', '')}".strip()
    if "carousel" in cat or topic == "carousel":
        return (story.get("status") == "corroborated") or bool(_BREAKING_DONE_DEAL.search(hay))
    if "recruit" in cat or topic == "recruiting":
        if _NOT_YET.search(hay):
            return False     # he has not committed/signed yet: a status story, not a signing
        return bool(_BREAKING_RECRUIT_VERB.search(hay) and _BREAKING_TOP_RECRUIT.search(hay))
    return bool(_BREAKING_UPSET.search(hay))


def _compose_story(dynasty: dict, story: dict, assessment: dict, stmt_id: str, *,
                   year: int, week: int, use_llm: bool,
                   cascade_ctx: dict | None = None) -> list[dict[str, Any]]:
    """Render the breaking moment for a reporter-broken story: the scoop post from
    its reporter, plus tier-sized media reactions and fan posts. Reaction texts come
    from the editorial social helpers: topic-aware (they reference THIS story), a
    small per-post LLM budget for the media voices, and a week-level seen-set so the
    several stories of a weekly pass never produce identical posts (the old canned
    pools repeated word for word across stories). The reporter's own dek carries the
    break so the post matches the article."""
    scope = assessment["scope"]
    tier = assessment["tier"]
    plan = (_NATL_PLAN if scope == "national" else _PLAN).get(tier, _PLAN[1])
    accounts = feed._accounts(dynasty, year, week)
    origin = _origin_for_reporter(story, accounts)

    media = [a for a in accounts if a["kind"] in _MEDIA_ACCT_KINDS and a["id"] != origin["id"]]
    local_fans = [a for a in accounts if a["kind"] == "local_fan"]
    nat_fans = [a for a in accounts if a["kind"] == "national_fan"]
    rng = random.Random(stmt_id + ":pick")
    rng.shuffle(media)
    rng.shuffle(local_fans)
    rng.shuffle(nat_fans)
    react_media = media[: plan["reactions"]]
    fan_accts = local_fans[: plan["fans_local"]] + nat_fans[: plan["fans_nat"]]

    from .editorial import social as ed_social
    ctx = cascade_ctx if cascade_ctx is not None else {"seen": set(), "llm_budget": 0}
    topic = ed_social.story_topic(story, dynasty)
    sentiment = assessment.get("sentiment", "neutral")
    team = dynasty.get("team", {}) or {}
    word = feed._team_word(team.get("name", ""), team.get("nickname", ""))
    program = scope == "program"

    break_text = (story.get("dek") or story.get("headline") or "").strip()
    by_id: dict[str, str] = {}
    for a in react_media:
        spend = use_llm and ctx.get("llm_budget", 0) > 0
        if spend:
            ctx["llm_budget"] -= 1
        text = ed_social.media_take(a.get("lean") or "", topic, story,
                                    seen=ctx["seen"], use_llm=spend)
        if text:
            by_id[a["id"]] = text
    for a in fan_accts:
        text = ed_social.fan_take(topic, sentiment, word,
                                  local=program and a["kind"] == "local_fan",
                                  program=program, seed=stmt_id + a["id"], seen=ctx["seen"])
        if text:
            by_id[a["id"]] = text
    content = {"break": break_text or "Sources: a development worth watching is breaking.",
               "by_id": by_id}

    posts = _assemble(content, assessment, origin, react_media, fan_accts, stmt_id,
                      dogpile=plan.get("dogpile", 0),
                      breaking=_story_is_breaking(story, assessment))
    if posts:
        # Program/national articles arrive with a reader page; insider reports do
        # not, so build the (deterministic, no-LLM) page on demand. Either way the
        # breaking post taps through to a full article rather than a dead card.
        if not story.get("detail"):
            try:
                story = {**story, "detail": article_detail.build_detail(story, dynasty)}
            except Exception:
                pass
        posts[0]["ref"] = _article_ref(story, scope)
    return posts


def _story_id(year: int, week: int, story: dict) -> str:
    key = story.get("id") or f"{story.get('headline', '')}|{story.get('reporter', '')}"
    h = hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:8]
    return f"{year}:{week}:news:{h}"


# =========================================================================
# id helper
# =========================================================================
def _statement_id(year: int, week: int, contact: dict, message: str) -> str:
    cid = (contact or {}).get("id") or (contact or {}).get("name") or "anon"
    h = hashlib.sha1(f"{cid}|{message}".encode("utf-8")).hexdigest()[:8]
    return f"{year}:{week}:stmt:{h}"
