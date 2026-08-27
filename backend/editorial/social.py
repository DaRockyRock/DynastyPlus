"""Per-beat social timeline: tweets driven by the rundown.

The same inversion as the news: the editorial brain decides what the timeline is
about (the scored rundown) and code assembles it; the model only writes short
posts. Anchor posts (a persona breaking/taking each top story, plus a debate
counter-take on the lead) are one focused LLM call each (robust on a small model,
unlike the old batched clusters); the fan volume is mood-shaded templates (cheap,
grounded, never wrong). Posts come out in the feed's `_attach_author` shape so the
feed reuses its own id/metric/timestamp/threading machinery.
"""
from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .. import llm
from . import personas, profile
from .briefs import build_rundown
from .state import extract

SYSTEM_POST = (
    "You run an account on a college football social app in a FICTIONAL universe. "
    "Write ONE short post (one or two sentences, lowercase is fine, terse like a real "
    "tweet). No emojis, no hashtag spam, never use dashes as punctuation. Stay in the "
    "account's voice. Use ONLY the facts given and invent nothing. Output JSON: "
    '{"text": "..."}.')


def _slug(name: str) -> str:
    return "".join(c for c in (name or "").lower() if c.isalnum())


def _handle(name: str) -> str:
    return _slug(name)[:18] or "account"


def _initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


def _author(card, kind: str) -> dict[str, Any]:
    return {"author_id": f"persona:{_slug(card.name)}", "author_name": card.name,
            "handle": _handle(card.name), "avatar": _initials(card.name), "image": "",
            "verified": True, "kind": kind, "team_espn_id": None, "textable": True,
            "text_kind": "media"}


def _fan_author(handle: str, kind: str, espn_id) -> dict[str, Any]:
    return {"author_id": f"fan:{handle}", "author_name": handle, "handle": handle,
            "avatar": _initials(handle.replace("_", " ")), "image": "", "verified": False,
            "kind": kind, "team_espn_id": espn_id, "textable": False, "text_kind": None}


def _post(author: dict, text: str) -> dict[str, Any]:
    return {**author, "text": text.strip(), "ref_key": "", "reply_to": "", "quote_of": "",
            "source": "social"}


# --- mood-shaded, TOPIC-aware fan templates (the robust volume) -------------
# Each references {topic} (a short phrase for the specific story) so same-mood fans
# react to DIFFERENT stories instead of echoing each other, and {tw} (team nickname).
_MOOD_BUCKET = {"euphoric": "up", "confident": "up", "steady": "mid",
                "anxious": "down", "grim": "down"}
_HOME_FAN = {
    "up":   ["{topic} and the {tw} faithful are FED. this is the year",
             "love what {topic} says about this {tw} team", "{topic}? the {tw} are different this year, i mean it",
             "screenshot this: {topic} is how the {tw} season turns"],
    "mid":  ["cautiously optimistic on {topic} for the {tw}", "{topic}... just want the {tw} to handle business",
             "{tw} fan here, {topic} has my attention", "not overreacting to {topic} yet but i like it"],
    "down": ["{topic} and here we go again with the {tw}", "{topic} wont fix what ails the {tw}",
             "trying to stay calm about {topic} but the {tw} test me every year",
             "wake me when the {tw} actually deliver on {topic}"],
}
_RIVAL_FAN = ["{tw} fans hyping {topic} already, adorable", "{topic}? the {tw} delusion stays undefeated",
              "ranking {topic} for the {tw} i see, cute", "every year its {topic} for the {tw}, every november nothing",
              "imagine being a {tw} fan excited about {topic} lol"]
_NEUTRAL_FAN = ["{topic} is the sneaky one to watch", "bettors are gonna love {topic}",
                "{topic} could decide the whole race", "circle {topic} on the calendar",
                "people are sleeping on {topic}", "the line on {topic} feels off to me",
                "{topic} has trap game energy", "quietly {topic} is the best thing on the slate"]


def _team_word(name: str) -> str:
    return (name or "").split()[-1] if name else "the team"


def _pick_unseen(pool: list[str], seed: str, seen: set[str], **fmt) -> str:
    """The first pool entry (walking from a seeded start) not already used this week.
    Returns '' when the pool is exhausted for these fmt args: fewer, varied posts beat
    many identical ones."""
    h = int(hashlib.sha1(seed.encode()).hexdigest(), 16)
    for off in range(len(pool)):
        cand = pool[(h + off) % len(pool)].format(**fmt)
        if cand not in seen:
            seen.add(cand)
            return cand
    return ""


# --- reaction texts for the world cascade (news_reactions) ------------------
# Media reactions to a broken story: topic-aware so five stories never produce the
# same line, LLM-voiced when the cascade budget allows, deduped across the week.
_MEDIA_TAKES = [
    "told {topic} has real legs, worth watching this week",
    "the {topic} chatter is not going away. people around the program keep confirming it",
    "checked around on {topic} tonight, the reporting holds up",
    "what i am hearing on {topic} lines up with the byline",
    "{topic} is worth your attention. more in my notebook tomorrow",
    "keeping my ear to the ground on {topic}. something is there",
    "my read: {topic} matters more than people realize",
    "sources have been consistent on {topic} for days now",
]


def story_topic(story: dict, dynasty: dict) -> str:
    """A short grounded phrase for a news story ('the Cromwell recruitment'), so
    cascade reactions reference the SPECIFIC story instead of generic filler."""
    from . import canon as canon_mod
    hay = f"{story.get('headline', '')} {story.get('dek', '')}".lower()
    cat = (story.get("category") or "").lower()
    cn = canon_mod.build(dynasty)
    name = next((e.name for e in cn.people.values()
                 if e.name and len(e.name) > 5 and e.name.lower() in hay), None)
    last = name.split()[-1] if name else ""
    if "recruit" in cat:
        return f"the {last} recruitment" if last else "this recruiting push"
    if "carousel" in cat or "coaching" in cat:
        return f"the {last} situation" if last else "the carousel news"
    if "injur" in cat:
        return "the injury news"
    if "portal" in cat:
        return f"the {last} portal move" if last else "the portal movement"
    return f"the {last} story" if last else "this report"


def media_take(voice: str, topic: str, story: dict, *, seen: set[str], use_llm: bool) -> str:
    """One media account's reaction to a broken story: a focused LLM post in the
    account's voice when budgeted, else a topic-aware deduped template."""
    if use_llm:
        facts = f"{story.get('headline', '')}. {story.get('dek', '')}".strip(". ")
        text = _gen_post("media", voice or "a college football media voice", "",
                         facts, "React to this report as a media member in your own voice: add "
                                "your read, your sourcing, or what it means. One or two sentences.",
                         use_llm=True)
        if text and text not in seen:
            seen.add(text)
            return text
    return _pick_unseen(_MEDIA_TAKES, f"mt:{topic}:{voice[:24]}", seen, topic=topic)


def fan_take(topic: str, sentiment: str, team_word: str, *, local: bool, program: bool,
             seed: str, seen: set[str]) -> str:
    """One fan account's reaction to a broken story: mood from the story's sentiment,
    grounded in the topic, deduped across the week's whole cascade."""
    bucket = {"positive": "up", "negative": "down"}.get(sentiment, "mid")
    if program and local:
        pool = _HOME_FAN[bucket]
    elif program:
        pool = _RIVAL_FAN
    else:
        pool = _NEUTRAL_FAN
    return _pick_unseen(pool, seed, seen, tw=team_word, team_word=team_word, topic=topic)


def _topic(beat: dict) -> str:
    """A short phrase for the specific story, so fan posts ground in it and vary."""
    t = beat.get("type")
    facts = beat.get("facts") or {}
    subs = beat.get("subjects") or []
    last = (subs[0].split()[-1] if subs else "")
    if t in ("recruiting_battle", "commit"):
        return f"the {last} recruitment" if last else "the recruiting board"
    if t == "next_game_preview":
        opp = next((str(v) for k, v in facts.items() if k == "matchup"), "")
        tail = opp.split(" to ")[-1].split(" host ")[-1] if opp else ""
        return f"{_team_word(subs[1]) if len(subs) > 1 else (tail or 'this')} week"
    if t in ("upset", "ranked_clash", "user_result", "blowout"):
        return facts.get("result", "that result")
    if t == "title_race":
        return "the top of the polls"
    if t == "marquee_preview":
        return facts.get("matchup", "the big game")
    if t in ("poll_jump", "poll_fall", "new_number_one"):
        return facts.get("move") or facts.get("change") or "the new poll"
    if t == "hot_seat_watch":
        return f"the {last} situation" if last else "the carousel"
    return (subs[0] if subs else "this week")


def _fan_posts(beat: dict, mood: str, team: str, user_espn, rng_seed: str, n: int,
               seen: set[str]) -> list[dict]:
    bucket = _MOOD_BUCKET.get(mood, "mid")
    tw = _team_word(team)
    topic = _topic(beat)
    program = beat.get("scope") == "program"
    pool = (_HOME_FAN[bucket] if program else _NEUTRAL_FAN)
    rival_pool = _RIVAL_FAN if program else _NEUTRAL_FAN
    out: list[dict] = []
    for i in range(n):
        h = int(hashlib.sha1(f"{rng_seed}:{i}".encode()).hexdigest(), 16)
        if program and i % 3 == 2:                       # a rival voice every third post
            src, kind, espn = rival_pool, "national_fan", None
        else:
            src, kind = pool, ("local_fan" if program else "national_fan")
            espn = user_espn if program else None
        text = _pick_unseen(src, f"{rng_seed}:{i}", seen, team_word=tw, tw=tw, topic=topic)
        if not text:                 # pool exhausted for this topic: skip rather than echo
            continue
        handle = f"rival_{h % 97}" if src is rival_pool else f"{'fan' if program else 'cfbfan'}_{h % 97}"
        out.append(_post(_fan_author(handle, kind, espn), text))
    return out


# --- anchor posts (one LLM call each, template fallback) --------------------
def _facts(beat: dict) -> str:
    return "; ".join(str(v) for k, v in (beat.get("facts") or {}).items() if v and k != "note")


def _gen_post(handle: str, voice: str, mood: str, facts: str, angle: str, *, use_llm: bool) -> str:
    if use_llm:
        prompt = (f"ACCOUNT: @{handle} (voice: {voice}). MOOD this week: {mood}.\n"
                  f"STORY (use only these facts): {facts}\n{angle}\nWrite the post. JSON only.")
        try:
            res = llm.generate_json(SYSTEM_POST, prompt, max_tokens=160, temperature=0.85)
            txt = (res.get("text") if isinstance(res, dict) else "") or ""
            if txt.strip():
                return txt.strip()
        except Exception:
            pass
    # template fallback: the lead fact, plainly
    lead = facts.split(";")[0].strip()
    return lead.lower() if lead else "worth watching this week"


def social_posts(dynasty: dict, year: int, week: int, *, use_llm: bool = True) -> list[dict[str, Any]]:
    """The week's rundown-driven timeline in the feed post shape. Anchors are
    persona-voiced LLM posts (budgeted); fans are mood-shaded templates."""
    prof = profile.current()
    use_llm = use_llm and prof.tier != "none" and llm.available()
    rundown = build_rundown(dynasty, year, week)
    state = extract(dynasty, year, week)
    preg = personas.build()
    team = (dynasty.get("team") or {}).get("name") or "the program"
    user_espn = (dynasty.get("team") or {}).get("espn_id")
    mood = rundown.get("mood", "steady")

    # Scope-balanced slate: top program AND top national beats. A global top-k lets
    # high-scoring recruiting battles crowd out the national picture entirely, which
    # reads as "all my team, no insight into the sport".
    per_scope = {"none": 2, "nano": 3, "small": 3, "mid": 4, "frontier": 5}.get(prof.tier, 3)
    prog_beats_all = sorted(rundown.get("program") or [], key=lambda c: -float(c.get("score") or 0))
    nat_beats_all = sorted(rundown.get("national") or [], key=lambda c: -float(c.get("score") or 0))
    beats = prog_beats_all[:per_scope] + nat_beats_all[:per_scope]
    budget = prof.max_llm_beats if use_llm else 0

    # 1) anchor posts: a persona breaks/takes each top story (LLM up to budget).
    anchor_jobs = []
    for bi, beat in enumerate(beats):
        scope = beat.get("scope", "national")
        card = personas.byline_for(scope, beat.get("id", str(bi)), preg)
        if not card:
            continue
        kind = "beat" if scope == "program" else "reporter"
        angle = ("Break or post your take on this story in your voice."
                 if scope == "national" else "Post a beat-writer note on this in your voice.")
        anchor_jobs.append((bi, beat, card, kind, angle))

    def run_anchor(job):
        bi, beat, card, kind, angle = job
        text = _gen_post(_handle(card.name), card.voice, mood if beat.get("scope") == "program" else "",
                         _facts(beat), angle, use_llm=use_llm and bi < budget)
        return _post(_author(card, kind), text)

    if use_llm and prof.workers > 1:
        with ThreadPoolExecutor(max_workers=prof.workers) as ex:
            anchors = list(ex.map(run_anchor, anchor_jobs))
    else:
        anchors = [run_anchor(j) for j in anchor_jobs]

    posts: list[dict] = list(anchors)

    # 2) a debate counter-take on the LEAD program story from a skeptic pundit.
    prog_beats = [b for b in beats if b.get("scope") == "program"]
    if use_llm and prog_beats:
        lead = prog_beats[0]
        pair = personas.opposing_pair("program", f"social:{year}:{week}", preg)
        if pair:
            skeptic = pair[1]
            text = _gen_post(_handle(skeptic.name), skeptic.voice, mood, _facts(lead),
                             "Give your SKEPTICAL take pushing back on the optimism around this, in your voice.",
                             use_llm=True)
            posts.append(_post(_author(skeptic, "columnist"), text))

    # 3) the national insight layer: personality predictions on the marquee games
    # (against the line) and a columnist's playoff-picture take, so the timeline
    # always carries the sport's bigger picture, not just the user's program.
    from . import ratings as ratings_mod
    for i, mb in enumerate([b for b in nat_beats_all if b.get("type") == "marquee_preview"][:2]):
        facts = mb.get("facts") or {}
        matchup, line = facts.get("matchup") or "", facts.get("line") or ""
        card = personas.byline_for("national", f"pick:{year}:{week}:{i}", preg)
        if not matchup or not card:
            continue
        parsed = ratings_mod.parse_line(line)
        fav = parsed[0] if parsed else ""
        take_dog = (int(hashlib.sha1(f"{year}:{week}:dog:{i}".encode()).hexdigest(), 16) % 10) < 3
        text = ""
        if use_llm:
            text = _gen_post(_handle(card.name), card.voice, "",
                             f"{matchup}; the line is {line or 'not posted yet'}",
                             "Post your PREDICTION for this game with a one-line reason, in your "
                             "voice. Pick a side" + (", and take the underdog" if take_dog else ""),
                             use_llm=True)
        if not text or text == matchup.lower():
            if take_dog and fav:
                text = f"{matchup}: {line}? that is too many points. give me the dog"
            elif fav:
                text = f"{matchup}: the number is {line} and it still is not enough. {fav} covers"
            else:
                text = f"{matchup} is the game of the week. the winner announces itself as a contender"
        posts.append(_post(_author(card, "personality"), text))

    ap = [r for r in ((dynasty.get("national") or {}).get("ap_top25") or []) if r.get("team")]
    if ap:
        card = personas.byline_for("national", f"playoff:{year}:{week}", preg)
        top4 = ", ".join(f"{r['rank']} {r['team']}" for r in ap[:4])
        first_out = ap[4]["team"] if len(ap) > 4 else ""
        if card:
            text = ""
            if use_llm:
                text = _gen_post(_handle(card.name), card.voice, "",
                                 f"AP top four: {top4}" + (f"; first team out: {first_out}" if first_out else ""),
                                 "Post your read on the playoff picture: who is for real and who is "
                                 "most likely to crash the field, in your voice.", use_llm=True)
            if not text:
                text = (f"playoff picture today: {top4}."
                        + (f" {first_out} is the first team out and that will not last" if first_out else ""))
            posts.append(_post(_author(card, "columnist"), text))

    # 4) mood-shaded fan volume referencing the top beats (templated, robust).
    per_beat = {"none": 4, "nano": 5, "small": 6, "mid": 7, "frontier": 8}.get(prof.tier, 5)
    fan_seen: set[str] = set()        # global, so no fan template repeats across the timeline
    for bi, beat in enumerate(beats[:5]):
        posts += _fan_posts(beat, mood, team, user_espn,
                            f"{year}:{week}:{beat.get('id', bi)}", per_beat, fan_seen)

    return posts
