"""Social feed.

A college-football Twitter/X timeline that lives in the in-app phone next to
Messages. Every media member has an account that posts on its own, week to week,
alongside national online personalities (pundits/analysts, editable like the
reporters), brand/network accounts (ESPN, FOX, On3...), and generated local and
national/rival fans. Posts react to and reference everything the dynasty produced
this week: game results, rankings, the Heisman race, recruiting, the portal, the
hot seat, awards, and the very articles the news modules already generated
(including their bylines). Posts also reference each other through reply and quote
chains.

This module is registered LAST in the pipeline so it can read every other
module's already-cached output for the week and turn it into a social layer. It
reads those siblings the way directory.py does: cache.get_module(...) directly,
best-effort, so it still produces a full timeline grounded in the dynasty save
when a sibling cache is missing.

The engine has four parts, each in its own section below:
  1. accounts   - who has an account this week (derived media + editable
                  personalities/brands + generated recurring/rotating fans)
  2. surface    - the typed list of things worth posting about, plus a compact
                  text brief and a "ref menu" the model picks from by key
  3. selection  - a deterministic, weighted, capped pick of who posts about what
  4. render     - LLM generation in a few clustered calls (with a rich mock
                  fallback), then ids/timestamps/metrics/threading resolved here

Coach interaction is read + like only (no replying, no composing); likes and the
seen marker live in feed_state.py.
"""
from __future__ import annotations

import random
import re
from typing import Any

from .. import cache, customization, directory, llm, narrative, personality, progress, world_events
from . import base

MODULE = "feed"

# Roughly how big a week's timeline is (chosen per week), so it feels like a real
# scrolling feed rather than a handful of posts.
_WEEK_COUNTS = [42, 46, 50, 54]
# How many of the slots are reply/quote chains hanging off the biggest posts.
_REPLY_FRACTION = 0.22

SYSTEM = (
    "You are running the accounts on a college football social media app (a "
    "Twitter/X style feed) for a FICTIONAL dynasty universe. You write short, "
    "punchy posts in the distinct voice of each account: national insiders break "
    "news, pundits fire hot takes, beat writers file notes, brand accounts post "
    "alerts and engagement bait, and fans react with raw emotion and trash talk. "
    "Scope discipline matters: NATIONAL accounts (insiders, analysts, columnists, "
    "networks) post about the WHOLE sport and the best teams, biased toward the "
    "biggest news, not toward any one program; only the LOCAL beat writers and the "
    "home fans are biased toward the user's team, the way a hometown paper is. "
    "Hard rules: write like real social posts (terse, lowercase is fine, @ "
    "mentions are fine) but NEVER use emojis and NEVER use hashtag spam (at most "
    "one tasteful hashtag, and usually none). Never use dashes as punctuation; use "
    "commas or periods. Stay in character and use ONLY the provided facts; never "
    "invent real-world people, results, or rankings."
)


# =========================================================================
# small helpers
# =========================================================================
def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name or "").lower()) or "acct"


def _handle(name: str) -> str:
    return _slug(name)


def _initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", str(name or "")) if p]
    return ("".join(p[0] for p in parts[:2]) or (name or "?")[:2]).upper()


def _last_word(name: str) -> str:
    parts = [p for p in re.split(r"\s+", str(name or "")) if p]
    return parts[-1] if parts else (name or "")


def _team_word(name: str, nickname: str = "") -> str:
    """A short fan-friendly word for a program, e.g. 'Cornhuskers' -> 'Husker'."""
    word = nickname or _last_word(name)
    if len(word) > 4 and word.lower().endswith("s"):
        word = word[:-1]
    return word or "Team"


# =========================================================================
# 1. accounts
# =========================================================================
# Posting weight per account kind (drives selection + engagement scale).
_KIND_WEIGHT = {
    "brand": 5, "insider": 5, "personality": 4, "reporter": 4,
    "analyst": 3, "columnist": 2, "beat": 3, "local_fan": 3, "national_fan": 2,
}

# Engagement scale (base like count range) per kind.
_KIND_ENGAGEMENT = {
    "brand": (900, 7000), "insider": (500, 4200), "personality": (350, 3200),
    "reporter": (140, 1600), "analyst": (120, 1400), "columnist": (140, 1500),
    "beat": (80, 900), "local_fan": (3, 320), "national_fan": (4, 500),
}

# Which kinds of event each archetype tends to post about (mock ref selection).
_ARCHETYPE_REF_WEIGHTS = {
    "brand": {"game": 7, "ranking": 5, "recruit": 2, "portal": 2, "hot_seat": 1, "article": 1},
    "insider": {"hot_seat": 5, "portal": 4, "article": 4, "recruit": 2, "game": 2},
    "reporter": {"article": 4, "game": 3, "portal": 2, "recruit": 2, "ranking": 1},
    "beat": {"game": 4, "article": 3, "recruit": 2, "portal": 1},
    "personality": {"game": 4, "ranking": 4, "hot_seat": 2, "article": 1},
    "analyst": {"recruit": 6, "portal": 3, "article": 1},
    "columnist": {"ranking": 4, "game": 3, "hot_seat": 1, "article": 1},
    "local_fan": {"game": 6, "recruit": 3, "ranking": 2, "portal": 1},
    "national_fan": {"game": 5, "ranking": 2, "hot_seat": 2, "recruit": 1},
    "default": {"game": 4, "ranking": 2, "article": 1},
}

# How many posts may attach the same event, so nothing gets echoed by everyone.
_REF_CAPS = {"game": 5, "ranking": 3, "recruit": 2, "portal": 2, "hot_seat": 2,
             "article": 2, "confrace": 3}

# Scope bias per account: (national multiplier, program multiplier) applied to a
# ref's base archetype weight. National voices lean hard to the national scene and
# only rarely touch the user's program; local beat writers and home fans do the
# opposite; rival/neutral fans tilt national but still love dunking on the user.
def _scope_mult(acct: dict) -> dict[str, float]:
    kind = acct["kind"]
    if kind == "local_fan":
        return {"national": 0.4, "program": 1.0}
    if kind == "national_fan":
        return {"national": 1.3, "program": 0.9}
    if acct.get("scope") == "local":  # local beat writer / program insider
        return {"national": 0.3, "program": 1.0}
    return {"national": 1.0, "program": 0.2}  # national media voice

# Fan voice banks (recurring core + rotating extras are drawn from these, seeded).
_FAN_NOUNS = ["Diehard", "Faithful", "Realist", "Truther", "Optimist", "Doomer",
              "Tailgater", "Section", "Booster", "Sicko", "Lifer", "Apologist"]
_FAN_FIRST = ["Big", "Old", "Coach", "Uncle", "Tunnel", "Couch", "Lot", "Press"]
_LOCAL_ARCHES = [
    "an euphoric believer who rides every high",
    "a doom-and-gloom worrier who panics after any mistake",
    "a level-headed realist who tries to calm the timeline down",
    "a stats nerd who quotes the box score and efficiency numbers",
    "a recruiting obsessive who lives on the board and visit news",
    "a grizzled lifer who has seen every era and keeps perspective",
    "a hot-take fan who wants someone fired every week",
    "a wholesome superfan who just loves the team unconditionally",
]
_NATIONAL_ARCHES = [
    "a rival fan who trolls the program at every opportunity",
    "a neutral national fan with cold, detached takes",
    "a bettor who frames everything through the spread and the over",
    "a chaos-loving fan who roots for upsets and drama",
    "a smug fan of a blue-blood who looks down on everyone",
    "a meme-minded poster who dunks for the engagement",
]


def _media_accounts() -> list[dict[str, Any]]:
    """Accounts derived from the existing media-flavor stores: byline reporters,
    recruiting analysts, award voters, plus the curated Media phone contacts. These
    are textable (tapping the author opens the same DM thread as Messages)."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(name, handle, outlet, kind, lean, image="", text_kind="media", scope="national"):
        if not name or name in seen:
            return
        seen.add(name)
        out.append({
            "id": f"media:{_slug(name)}", "name": name, "handle": handle or _handle(name),
            "avatar": _initials(name), "image": image, "verified": True, "kind": kind,
            "lean": lean or "", "scope": scope, "textable": True, "text_kind": text_kind,
            "team_espn_id": None,
        })

    for r in customization.section("reporters"):
        beat = (r.get("beat") or "").lower()
        scope = (r.get("scope") or "national").lower()
        kind = "insider" if beat == "carousel" else ("beat" if scope == "local" else "reporter")
        lean = f"{r.get('outlet','')} {beat} reporter. {r.get('bio','')}".strip()
        add(r.get("name"), _handle(r.get("name", "")), r.get("outlet"), kind, lean, r.get("image", ""), "media", scope)
    for p in customization.section("online_personalities"):
        add(p.get("name"), p.get("handle"), p.get("outlet"), "personality", p.get("lean") or p.get("bio"),
            p.get("image", ""), "media", (p.get("scope") or "national").lower())
    for a in customization.section("recruiting_analysts"):
        add(a.get("name"), _handle(a.get("name", "")), a.get("outlet"), "analyst",
            f"recruiting analyst, {a.get('outlet','')}. {a.get('lean','')}".strip(), "", "analyst")
    for v in customization.section("award_voters"):
        add(v.get("name"), _handle(v.get("name", "")), v.get("outlet"), "columnist",
            f"national columnist and awards voter, {v.get('outlet','')}. {v.get('lean','')}".strip(), "", "voter")
    for c in customization.section("phone_contacts"):
        if c.get("category") == "Media":
            scope = (c.get("media_scope") or "").lower()
            kind = "insider" if "insider" in (c.get("role") or "").lower() else "beat"
            add(c.get("name"), _handle(c.get("name", "")), c.get("outlet"), kind,
                f"{c.get('role','')}. {c.get('personality','')}".strip(), c.get("image", ""), "media",
                scope or "national")
    return out


def _brand_accounts() -> list[dict[str, Any]]:
    out = []
    for b in customization.section("brand_accounts"):
        name = b.get("name")
        if not name:
            continue
        out.append({
            "id": f"brand:{_slug(b.get('handle') or name)}", "name": name,
            "handle": b.get("handle") or _handle(name), "avatar": _initials(name),
            "image": b.get("image", ""), "verified": True, "kind": "brand",
            "lean": b.get("voice", ""), "scope": "national", "textable": False,
            "text_kind": None, "team_espn_id": None,
        })
    return out


def _fan_account(rng: random.Random, *, local: bool, team_word: str, team_espn_id, idx: int) -> dict[str, Any]:
    arches = _LOCAL_ARCHES if local else _NATIONAL_ARCHES
    arche = arches[idx % len(arches)]
    noun = rng.choice(_FAN_NOUNS)
    style = rng.randint(0, 2)
    if style == 0:
        display = f"{team_word} {noun}"
        handle = f"{_slug(team_word)}{_slug(noun)}{rng.randint(2, 99)}"
    elif style == 1:
        display = f"{rng.choice(_FAN_FIRST)} {team_word} {noun}".strip()
        handle = f"{_slug(team_word)}{rng.randint(10, 99)}{_slug(noun)}"
    else:
        display = f"{noun} in the {team_word} section"
        handle = f"{_slug(noun)}_{_slug(team_word)}{rng.randint(1, 30)}"
    kind = "local_fan" if local else "national_fan"
    return {
        "id": f"fan:{'l' if local else 'n'}:{idx}:{_slug(handle)}", "name": display, "handle": handle,
        "avatar": _initials(team_word), "image": "", "verified": False, "kind": kind,
        "lean": arche, "scope": "national", "textable": False, "text_kind": None,
        "team_espn_id": team_espn_id, "fan_of": team_word,
    }


def _fan_accounts(dynasty: dict, year: int, week: int) -> list[dict[str, Any]]:
    """Recurring core (stable all season, seeded by year) plus rotating extras
    (seeded per week). Local fans root for the program; national fans are rival
    or neutral national accounts."""
    team = dynasty.get("team", {}) or {}
    team_word = _team_word(team.get("name", ""), team.get("nickname", ""))
    team_id = team.get("espn_id")
    rivals = [r for r in (dynasty.get("rivals") or []) if r.get("name")]

    core = random.Random(f"{year}:feed:fans")
    extra = random.Random(f"{year}:{week}:feed:fans")
    out: list[dict[str, Any]] = []

    # Recurring core: 5 locals + 3 nationals, identical every week of the season.
    for i in range(5):
        out.append(_fan_account(core, local=True, team_word=team_word, team_espn_id=team_id, idx=i))
    for i in range(3):
        rv = rivals[i % len(rivals)] if rivals else None
        rw = _team_word(rv.get("name", "")) if rv else "National"
        out.append(_fan_account(core, local=False, team_word=rw,
                                team_espn_id=(rv.get("espn_id") if rv else None), idx=i))
    # Rotating extras: a few fresh faces this week.
    for i in range(extra.randint(3, 5)):
        out.append(_fan_account(extra, local=True, team_word=team_word, team_espn_id=team_id, idx=5 + i))
    for i in range(extra.randint(2, 4)):
        rv = rivals[(3 + i) % len(rivals)] if rivals else None
        rw = _team_word(rv.get("name", "")) if rv else "National"
        out.append(_fan_account(extra, local=False, team_word=rw,
                                team_espn_id=(rv.get("espn_id") if rv else None), idx=3 + i))
    return out


def _accounts(dynasty: dict, year: int, week: int) -> list[dict[str, Any]]:
    return _media_accounts() + _brand_accounts() + _fan_accounts(dynasty, year, week)


# =========================================================================
# 2. surface (postable events + ref menu + text brief)
# =========================================================================
def _cached(year: int, week: int, module: str) -> Any:
    try:
        return cache.get_module(year, week, module)
    except Exception:
        return None


def _articles(year: int, week: int) -> list[tuple[str, dict[str, Any]]]:
    """Full article objects from this week's news cache, each tagged with the scope
    it was filed under (so a national writer quotes a national piece and a beat
    writer quotes a program piece). Returns (scope, article) pairs. Best-effort."""
    out: list[tuple[str, dict[str, Any]]] = []
    feed = _cached(year, week, "news_feed") or {}
    # The news feed already separates other-program coverage (national + the
    # coaching carousel) from the user's program coverage; mirror that split here.
    for key, scope in (("national", "national"), ("insider_reports", "national"), ("program", "program")):
        for a in feed.get(key, []) or []:
            if a.get("headline"):
                out.append((scope, a))
    stories = _cached(year, week, "top_stories") or {}
    for s in stories.get("stories", []) or []:
        if s.get("headline"):
            scope = "program" if (s.get("category") in ("Program", "Recruiting", "Rivalry")) else "national"
            out.append((scope, s))
    return out


def _surface(dynasty: dict, year: int, week: int) -> dict[str, Any]:
    """Typed postable events keyed for the ref menu, plus a compact text brief."""
    refs: dict[str, dict[str, Any]] = {}
    team = dynasty.get("team", {}) or {}
    sched = dynasty.get("schedule", {}) or {}
    recent = sched.get("recent_results") or []
    last = recent[0] if recent else None
    up = sched.get("upcoming") or {}
    nat = dynasty.get("national", {}) or {}

    if last and last.get("score"):
        refs["game"] = {
            "type": "game", "scope": "program", "label": "FINAL",
            "us": team.get("school") or team.get("name"),
            "us_espn_id": team.get("espn_id"), "them": last.get("opponent"),
            "them_espn_id": last.get("opponent_espn_id"), "score": last.get("score"),
            "result": last.get("result"), "home": last.get("home"),
            "rank_matchup": last.get("rank_matchup"),
        }
    if up.get("opponent"):
        refs["next"] = {
            "type": "game", "scope": "program", "label": "UP NEXT",
            "us": team.get("school") or team.get("name"),
            "us_espn_id": team.get("espn_id"), "them": up.get("opponent"),
            "them_espn_id": up.get("opponent_espn_id"), "score": None,
            "spread": up.get("spread"), "tv": up.get("tv"), "home": up.get("home"),
            "opponent_rank": up.get("opponent_rank"),
        }
    ap = nat.get("ap_top25") or []
    if ap:
        refs["rank"] = {"type": "ranking", "scope": "national", "label": "AP Top 25", "items": [
            {"rank": e.get("rank"), "team": e.get("team"), "espn_id": e.get("espn_id"),
             "record": e.get("record")}
            for e in ap[:10]]}
    cfp = nat.get("cfp_top12") or []
    if cfp:
        refs["cfp"] = {"type": "ranking", "scope": "national", "label": "Playoff projection", "items": [
            {"rank": e.get("rank"), "team": e.get("team"), "espn_id": e.get("espn_id")}
            for e in cfp[:8]]}
    heis = nat.get("heisman_frontrunners") or []
    if heis:
        refs["heisman"] = {"type": "ranking", "scope": "national", "label": "Heisman watch", "items": [
            {"rank": i + 1, "team": h.get("team"), "name": h.get("name"), "position": h.get("position")}
            for i, h in enumerate(heis[:5])]}
    # Conference races are national fodder for the better leagues (the user's own
    # league is covered, but the top of every standings table is a national story).
    standings = dynasty.get("conference_standings") or []
    if standings:
        refs["confrace"] = {"type": "confrace", "scope": "national", "label": "Conference race",
                            "teams": [{"team": s.get("team"), "espn_id": s.get("espn_id"),
                                       "overall": s.get("overall")} for s in standings[:6]]}

    rec = dynasty.get("recruiting", {}) or {}
    board = sorted((rec.get("targets") or []), key=lambda r: -(r.get("interest") or 0))
    commits = rec.get("commits") or []
    for i, r in enumerate((commits[:3] + board[:4])[:5]):
        refs[f"recruit:{i}"] = {
            "type": "recruit", "scope": "program", "name": r.get("name"), "stars": r.get("stars"),
            "position": r.get("position"), "hometown": r.get("hometown"),
            "status": "commit" if r in commits else "target",
            "interest": r.get("interest"), "leader": r.get("leader"),
        }

    portal = dynasty.get("transfer_portal", {}) or {}
    pout = (portal.get("outgoing") or [])
    if pout:
        p0 = pout[0]
        refs["portal"] = {"type": "portal", "scope": "program", "name": p0.get("name"),
                          "position": p0.get("position"), "to": p0.get("to"), "direction": "out"}

    hs = _cached(year, week, "hot_seat") or {}
    hs_board = hs.get("board") or customization.section("hot_seat_coaches") or []
    if hs_board:
        h0 = hs_board[0]
        refs["hotseat"] = {"type": "hot_seat", "scope": "national", "coach": h0.get("coach"),
                           "team": h0.get("team"), "heat": h0.get("heat"), "note": h0.get("note")}

    arts = _articles(year, week)
    for i, (scope, a) in enumerate(arts[:12]):
        refs[f"art:{i}"] = {
            "type": "article", "scope": scope, "headline": a.get("headline"), "outlet": a.get("outlet"),
            "reporter": a.get("reporter") or _byline_name(a.get("byline", "")),
            "category": a.get("category"), "accent": a.get("accent"), "article": a,
        }

    return {"refs": refs, "articles": [a for _, a in arts]}


def _byline_name(byline: str) -> str:
    return (byline.split(",", 1)[0] if byline else "").strip()


def _national_landscape(dynasty: dict) -> list[str]:
    """A grounded snapshot of the broader sport (OTHER programs), so national
    voices have the top of the polls, the playoff and Heisman races, and the
    league races to talk about instead of defaulting to the user's team."""
    nat = dynasty.get("national", {}) or {}
    team_name = (dynasty.get("team", {}) or {}).get("name")
    lines: list[str] = []
    ap = [r for r in (nat.get("ap_top25") or []) if r.get("team")][:10]
    if ap:
        lines.append("AP top 10: " + ", ".join(
            f"{r['rank']}. {r['team']}" + (f" ({r['record']})" if r.get("record") and r["record"] != "0-0" else "")
            for r in ap))
    cfp = [r for r in (nat.get("cfp_top12") or []) if r.get("team")][:6]
    if cfp:
        lines.append("Playoff projection top 6: " + ", ".join(f"{r['rank']}. {r['team']}" for r in cfp))
    heis = [h for h in (nat.get("heisman_frontrunners") or []) if h.get("name")][:5]
    if heis:
        lines.append("Heisman frontrunners: " + ", ".join(
            f"{h['name']} ({h.get('team', '')}, {h.get('position', '')})".replace(", )", ")") for h in heis))
    standings = [s for s in (dynasty.get("conference_standings") or []) if s.get("team")][:6]
    if standings:
        conf = (dynasty.get("team", {}) or {}).get("conference") or "the user's conference"
        lines.append(f"{conf} race (the user's league): " + ", ".join(s["team"] for s in standings))
    if team_name:
        lines.append(f"(The user's program, {team_name}, is only a NATIONAL story if it appears above.)")
    return lines


def _brief(dynasty: dict, surface: dict, year: int, week: int) -> str:
    """A compact, scannable brief of the postable surface, split into NATIONAL
    events (the broader sport, other programs) and PROGRAM events (the user's
    team), with the ref keys the model attaches to a post."""
    season = dynasty.get("season", {}) or {}
    team = (dynasty.get("team", {}) or {}).get("name") or "the user's program"
    lines = [f"WEEK: {season.get('week_label', 'this week')} of the {season.get('year', '')} season. "
             f"The user's program is {team}."]

    landscape = _national_landscape(dynasty)
    if landscape:
        lines.append("\nNATIONAL LANDSCAPE (the broader sport, OTHER programs):")
        lines += ["  " + ln for ln in landscape]

    def render(key: str, ref: dict) -> str | None:
        t = ref["type"]
        if t == "game":
            sc = ref.get("score") or ref.get("spread") or ""
            return f"  [{key}] {ref['label']}: {ref['us']} vs {ref['them']} {sc}".rstrip()
        if t == "ranking":
            top = ", ".join(f"{it.get('rank')}. {it.get('name') or it.get('team')}" for it in ref["items"][:5])
            return f"  [{key}] {ref['label']}: {top}"
        if t == "confrace":
            return f"  [{key}] {ref['label']}: " + ", ".join(it.get("team", "") for it in ref.get("teams", [])[:5])
        if t == "recruit":
            return (f"  [{key}] {ref.get('stars')}-star {ref.get('position')} {ref.get('name')} "
                    f"({ref.get('status')}, interest {ref.get('interest')}, leader {ref.get('leader')})")
        if t == "portal":
            return f"  [{key}] portal: {ref.get('name')} ({ref.get('position')}) to {ref.get('to')}"
        if t == "hot_seat":
            return f"  [{key}] hot seat: {ref.get('coach')} ({ref.get('team')}), heat {ref.get('heat')}"
        if t == "article":
            return f"  [{key}] article by {ref.get('reporter') or ref.get('outlet')}: \"{ref.get('headline')}\""
        return None

    nat_lines, prog_lines = [], []
    for key, ref in surface["refs"].items():
        rendered = render(key, ref)
        if rendered is None:
            continue
        (nat_lines if ref.get("scope") == "national" else prog_lines).append(rendered)
    if nat_lines:
        lines.append("\nNATIONAL events (other programs, the whole sport), attach a post with its ref key:")
        lines += nat_lines
    if prog_lines:
        lines.append(f"\n{team} PROGRAM events (the user's team), attach a post with its ref key:")
        lines += prog_lines
    body = "\n".join(lines)
    # Lead with the editorial desk's ranked stories + week mood, so the timeline
    # skews to what actually matters and fan posts carry the right tone (best-effort).
    try:
        from .. import editorial
        ed = editorial.feed_brief(dynasty, year, week)
        if ed:
            body = ed + "\n\n" + body
    except Exception:
        pass
    return body


# =========================================================================
# 3. selection
# =========================================================================
def _select(accounts: list[dict[str, Any]], year: int, week: int) -> list[dict[str, Any]]:
    """Weighted, capped pick of which accounts post this week. Bigger accounts are
    likelier and may post more than once; fans fill out the timeline. Deterministic
    per (year, week)."""
    rng = random.Random(f"{year}:{week}:feed:pick")
    target = rng.choice(_WEEK_COUNTS)
    n_replies = int(target * _REPLY_FRACTION)
    n_roots = target - n_replies

    pool = []
    for a in accounts:
        w = _KIND_WEIGHT.get(a["kind"], 1)
        pool.append((a, w))

    chosen: list[dict[str, Any]] = []
    posted: dict[str, int] = {}
    # Every media/brand/personality account posts at least once (they always have
    # something to say); fans are drawn by weight to fill the rest.
    for a in accounts:
        if a["kind"] not in ("local_fan", "national_fan"):
            chosen.append(a)
            posted[a["id"]] = 1
    while len(chosen) < n_roots and pool:
        total = sum(w for _, w in pool)
        roll = rng.uniform(0, total)
        acc = 0.0
        pick = pool[-1][0]
        for a, w in pool:
            acc += w
            if roll <= acc:
                pick = a
                break
        if posted.get(pick["id"], 0) >= (3 if pick["kind"] == "brand" else 2):
            # cap repeats; allow brands/insiders to post a little more
            pool = [(a, w) for a, w in pool if a["id"] != pick["id"]]
            continue
        chosen.append(pick)
        posted[pick["id"]] = posted.get(pick["id"], 0) + 1
    return chosen[:n_roots]


# =========================================================================
# 4. render (LLM clustered generation + mock fallback)
# =========================================================================
def _group_task(group: str, team: str) -> str:
    """The scope-specific instruction for a cluster of root posts. National voices
    are pushed toward the broader sport and the best teams; local beat voices and
    home fans stay on the user's program; rival/neutral fans work the other side."""
    if group == "national_press":
        return (
            "These accounts are NATIONAL voices: insiders, on-air analysts, national "
            "columnists, and network/brand accounts. They are NOT beat writers for "
            f"{team}. Write ONE post for each, in its own voice, about the BIGGEST "
            "stories in the sport and the BEST teams: the top of the polls, the "
            "playoff and Heisman races, marquee matchups, conference races, and "
            "national coaching news, drawing on the NATIONAL LANDSCAPE and NATIONAL "
            f"events above. Do NOT default to {team}. Most of these posts must be "
            f"about OTHER programs. Only mention {team} when they are genuinely a "
            "national story (they appear in the rankings, just had a result that moves "
            "the national picture, or are the subject of a national coaching or portal "
            f"story), and let at most one or two accounts touch {team} at all. Spread "
            "the accounts across DIFFERENT teams and storylines: do not have everyone "
            "react to the same subject. Attach a NATIONAL ref via ref_key when one fits.")
    if group == "local_press":
        return (
            f"These accounts are LOCAL beat writers and program insiders who cover "
            f"{team} specifically. Write ONE post for each, in its own voice, ABOUT "
            f"{team}: the latest game, the quarterback room and depth-chart battles, "
            "recruiting and the board, the locker room, injuries, and the upcoming "
            "opponent, the way a hometown newspaper beat writer posts. Vary the angle "
            f"each one takes. Attach a {team} PROGRAM ref via ref_key when one fits.")
    if group == "national_fan":
        return (
            f"These accounts are rival and neutral national fans. Write ONE post for "
            "each, in its own voice: trash talk and trolling aimed at the favored "
            "teams or the user's program, hot takes on the national scene, and bettor "
            "or chaos energy. Keep it raw and short, lowercase is fine. Attach a ref "
            "via ref_key when one fits.")
    # local_fan (default home-crowd voice)
    return (
        f"These accounts are die-hard {team} fans. Write ONE post for each, in its "
        f"own voice, reacting emotionally to {team}'s week: the game, the QB battle, "
        "recruiting, and the upcoming opponent. Hype, panic, gallows humor, and blind "
        "faith. Keep it raw and short, lowercase is fine. Attach a PROGRAM ref via "
        "ref_key when one fits.")


def _llm_cluster(dynasty: dict, accounts: list[dict[str, Any]], surface: dict, brief: str,
                 context: str, year: int, week: int, *, group: str = "local_fan",
                 root_posts: list[dict] | None = None) -> list[dict]:
    """One LLM call for a set of accounts. With root_posts supplied this is the
    reply/quote pass (each returned post replies to or quotes a real root id);
    otherwise `group` selects the scope-specific instruction for the cluster."""
    team = (dynasty.get("team", {}) or {}).get("name") or "the user's program"
    roster = "\n".join(
        f"  [{a['id']}] @{a['handle']} ({a['name']}, {a['kind']}, {a.get('scope', 'national')}): {a.get('lean','')}"[:240]
        for a in accounts)
    if root_posts is not None:
        roots_txt = "\n".join(f"  [{p['id']}] @{p['handle']}: {p['text']}" for p in root_posts[:24])
        task = (
            "Write reply and quote posts reacting to existing posts on the timeline. "
            "Each new post must set either reply_to or quote_of to one of these real "
            "post ids:\n" + roots_txt + "\n\nMostly fan reactions (agreement, trolling, "
            "jokes, panic, hype) and the occasional pointed reply from another account.")
    else:
        task = _group_task(group, team)
    prompt = (
        f"{brief}\n\nACCOUNTS:\n{roster}\n\n{task}\n\n"
        'Return STRICT JSON: {"posts": [ {"author_id": "<id from roster>", '
        '"text": "the post", "ref_key": "<event key or empty>", '
        '"reply_to": "<post id or empty>", "quote_of": "<post id or empty>"} ] }. '
        "Keep posts short (one or two sentences). No emojis, no hashtag spam, no dashes "
        "as punctuation. JSON only.")
    res = llm.generate_json(SYSTEM, prompt, cached_context=context,
                            grounding=base.reactive_grounding(dynasty, year, week), max_tokens=4096, temperature=0.8)
    posts = res.get("posts") if isinstance(res, dict) else res
    return posts if isinstance(posts, list) else []


def _by_id(accounts: list[dict[str, Any]]) -> dict[str, dict]:
    return {a["id"]: a for a in accounts}


def _attach_author(raw: dict, acct: dict) -> dict:
    return {
        "author_id": acct["id"], "author_name": acct["name"], "handle": acct["handle"],
        "avatar": acct["avatar"], "image": acct.get("image", ""), "verified": acct.get("verified", False),
        "kind": acct["kind"], "team_espn_id": acct.get("team_espn_id"),
        "textable": acct.get("textable", False), "text_kind": acct.get("text_kind"),
        "text": str(raw.get("text") or "").strip(),
        "ref_key": raw.get("ref_key") or raw.get("ref") or "",
        "reply_to": raw.get("reply_to") or "",
        "quote_of": raw.get("quote_of") or "",
    }


def _generate_llm(dynasty: dict, accounts: list[dict], surface: dict, year: int, week: int) -> list[dict]:
    context = base.news_context(dynasty, year, week)
    brief = _brief(dynasty, surface, year, week)
    by_id = _by_id(accounts)
    selected = _select(accounts, year, week)

    # Beat writers (scope == local) cover the user's program; everyone else
    # (insiders, analysts, columnists, network/brand accounts) is a national voice.
    press = [a for a in selected if a["kind"] not in ("local_fan", "national_fan")]
    nat_press = [a for a in press if a.get("scope") != "local"]
    local_press = [a for a in press if a.get("scope") == "local"]
    locals_ = [a for a in selected if a["kind"] == "local_fan"]
    nats = [a for a in selected if a["kind"] == "national_fan"]

    groups = [
        (nat_press, "national_press", "National media posts"),
        (local_press, "local_press", "Local beat posts"),
        (locals_, "local_fan", "Local fan posts"),
        (nats, "national_fan", "National fan posts"),
    ]
    roots: list[dict] = []
    for accts, group, label in groups:
        if not accts:
            continue
        progress.set_sub_step(label)
        try:
            for raw in _llm_cluster(dynasty, accts, surface, brief, context, year, week, group=group):
                acct = by_id.get(raw.get("author_id"))
                if acct and raw.get("text"):
                    roots.append(_attach_author(raw, acct))
        except Exception:
            continue
    if not roots:
        raise ValueError("feed LLM produced no posts")

    roots = _finalize_roots(roots, surface, year, week)

    # Reply/quote pass: fan accounts reacting to the biggest root posts.
    rng = random.Random(f"{year}:{week}:feed:replychoice")
    fan_accts = [a for a in accounts if a["kind"] in ("local_fan", "national_fan")]
    rng.shuffle(fan_accts)
    n_replies = int(len(roots) * _REPLY_FRACTION) + 2
    repliers = fan_accts[:max(4, n_replies)]
    hot = sorted(roots, key=lambda p: -(p["metrics"]["likes"]))[:14]
    progress.set_sub_step("Fan reactions")
    replies: list[dict] = []
    try:
        for raw in _llm_cluster(dynasty, repliers, surface, brief, context, year, week, root_posts=hot):
            acct = by_id.get(raw.get("author_id"))
            parent = raw.get("reply_to") or raw.get("quote_of")
            if acct and raw.get("text") and parent in {p["id"] for p in roots}:
                replies.append(_attach_author(raw, acct))
    except Exception:
        replies = []
    return _merge_replies(roots, replies, surface, year, week)


# --- finalize: ids, refs, timestamps, metrics, threading ------------------
def _post_id(year: int, week: int, handle: str, n: int) -> str:
    return f"{year}:{week}:{_slug(handle)}:{n}"


def _hours_ago(kind: str, ref_type: str, rng: random.Random) -> float:
    """Spread posts across the week. Game reactions cluster postgame (recent),
    previews sit earlier, recruiting/portal scatter across the week."""
    if ref_type == "game":
        return rng.uniform(1, 30)
    if ref_type in ("recruit", "portal", "hot_seat"):
        return rng.uniform(6, 150)
    if kind in ("local_fan", "national_fan"):
        return rng.uniform(2, 120)
    return rng.uniform(2, 96)


def _label(hours: float) -> str:
    if hours < 1:
        return "now"
    if hours < 24:
        return f"{int(round(hours))}h ago"
    return f"{int(hours // 24)}d ago"


def _metrics(kind: str, ref: dict | None, post_id: str) -> dict[str, int]:
    lo, hi = _KIND_ENGAGEMENT.get(kind, (5, 200))
    rng = random.Random(post_id + ":metrics")
    likes = rng.randint(lo, hi)
    # Big events lift engagement; a ranked result or a ranking reveal travels.
    if ref and ref.get("type") == "game" and (ref.get("rank_matchup") or ref.get("result")):
        likes = int(likes * rng.uniform(1.3, 2.4))
    if ref and ref.get("type") == "ranking":
        likes = int(likes * rng.uniform(1.2, 1.8))
    if kind in ("local_fan", "national_fan") and rng.random() < 0.12:
        likes = int(likes * rng.uniform(4, 14))  # the occasional viral fan post
    reposts = int(likes * rng.uniform(0.10, 0.26))
    replies = int(likes * rng.uniform(0.06, 0.20))
    return {"likes": likes, "reposts": reposts, "replies": replies}


def _finalize_roots(roots: list[dict], surface: dict, year: int, week: int) -> list[dict]:
    """Assign stable ids, resolve ref_key -> ref payload, timestamps and metrics.
    Sorted newest first."""
    refs = surface["refs"]
    counter: dict[str, int] = {}
    ts_rng = random.Random(f"{year}:{week}:feed:ts")
    out = []
    for p in roots:
        h = p["handle"]
        n = counter.get(h, 0)
        counter[h] = n + 1
        p["id"] = _post_id(year, week, h, n)
        p["ref"] = refs.get(p.get("ref_key")) if p.get("ref_key") in refs else None
        p.pop("ref_key", None)
        ref_type = p["ref"]["type"] if p.get("ref") else ""
        hours = _hours_ago(p["kind"], ref_type, ts_rng)
        p["hours_ago"] = hours
        p["ts"] = round(1_000_000 - hours, 4)  # synthetic, for sort only (newer = larger)
        p["timestamp"] = _label(hours)
        p["metrics"] = _metrics(p["kind"], p.get("ref"), p["id"])
        p["reply_to"] = p.get("reply_to") or None
        p["quote_of"] = p.get("quote_of") or None
        out.append(p)
    out.sort(key=lambda x: -x["ts"])
    return out


def _merge_replies(roots: list[dict], replies: list[dict], surface: dict, year: int, week: int) -> list[dict]:
    """Stamp replies just after their parent and merge into the timeline."""
    by_id = {p["id"]: p for p in roots}
    counter: dict[str, int] = {}
    for r in replies:
        h = r["handle"]
        n = counter.get(h, 1000)  # reply ids namespaced away from root ids
        counter[h] = n + 1
        r["id"] = _post_id(year, week, h, n)
        parent_id = r.get("reply_to") or r.get("quote_of")
        parent = by_id.get(parent_id)
        r["ref"] = None
        if r.get("quote_of") and parent:
            # carry a slim quoted-post snapshot so the card can render it inline
            r["quoted"] = {"author_name": parent["author_name"], "handle": parent["handle"],
                           "avatar": parent["avatar"], "verified": parent["verified"],
                           "text": parent["text"], "image": parent.get("image", "")}
        base_hours = parent["hours_ago"] if parent else 12
        hours = max(0.2, base_hours - random.Random(r["id"]).uniform(0.2, 2.5))
        r["hours_ago"] = hours
        r["ts"] = round(1_000_000 - hours, 4)
        r["timestamp"] = _label(hours)
        r["metrics"] = _metrics(r["kind"], None, r["id"])
        r.pop("ref_key", None)
    merged = roots + replies
    merged.sort(key=lambda x: -x["ts"])
    return merged


# --- mock fallback --------------------------------------------------------
def _mock_text(acct: dict, ref: dict | None, dynasty: dict) -> str:
    """A grounded, in-character post for an account given an optional event."""
    team = dynasty.get("team", {}) or {}
    school = team.get("school") or team.get("name") or "the program"
    word = _team_word(team.get("name", ""), team.get("nickname", ""))
    kind = acct["kind"]
    handle = acct["handle"]

    if ref and ref["type"] == "game":
        won = ref.get("result") == "W"
        opp = ref.get("them")
        score = ref.get("score") or ""
        if ref.get("label") == "FINAL":
            if kind == "brand":
                return f"FINAL: {school} {score} {opp}." + (" Statement win." if won else " Upset alert cashes.")
            if kind in ("insider", "reporter", "beat"):
                return (f"{school} takes care of {opp}, {score}. Resume keeps building." if won
                        else f"{school} drops one to {opp}, {score}. Questions to answer this week.")
            if kind == "personality":
                return (f"Told you about {school}. {score} over {opp} is exactly the kind of win that travels in the room."
                        if won else f"{school} just lost the kind of game that lingers. {score} to {opp}. Not good enough.")
            if kind == "local_fan":
                return (f"{word.upper()} BY {score}!! i believe in this team again" if won
                        else f"same old {word.lower()}. {score} to {opp} is unacceptable. somebody has to answer for this")
            if kind == "national_fan":
                return (f"{word} fans acting like beating {opp} {score} means something lol" if won
                        else f"{word} losing to {opp} {score} is the funniest thing on my timeline today")
        else:  # UP NEXT
            spread = ref.get("spread") or "no line yet"
            if kind == "brand":
                return f"UP NEXT: {school} hosts {opp}. Line: {spread}."
            if kind == "local_fan":
                return f"{opp} week. dont overthink it, just win. {word.lower()}s by 2 scores"
            if kind == "national_fan":
                return f"taking {opp} and the points against {school} all day. {spread} is a gift"
            return f"All eyes on {school} and {opp} this week. {spread}."

    if ref and ref["type"] == "ranking":
        items = ref.get("items") or []
        top = items[0] if items else {}
        label = ref.get("label")
        lead = top.get("name") or top.get("team") or ""
        if kind == "brand":
            return f"{label}: {lead} sits on top." + (" Full rankings out now." if "AP" in (label or "") else "")
        if kind == "personality":
            return f"{lead} at the top of the {label} is fair, but the gap behind them is closing fast."
        if kind in ("local_fan", "national_fan"):
            return f"how is {word} not higher in the {label}. disrespect every single week"
        return f"{label} reaction: {lead} leads the way."

    if ref and ref["type"] == "confrace":
        teams = [t.get("team") for t in (ref.get("teams") or []) if t.get("team")]
        lead = teams[0] if teams else "the favorites"
        chase = teams[1] if len(teams) > 1 else "the field"
        if kind == "brand":
            return f"{ref.get('label', 'Conference race')}: {lead} the early favorite, {chase} in pursuit."
        if kind in ("personality", "columnist"):
            return f"{lead} are the team to beat in that league, but do not sleep on {chase}."
        if kind in ("local_fan", "national_fan"):
            return f"{lead} getting all the hype again. we will see how that ages"
        return f"The race to watch: {lead} and {chase} at the top."

    if ref and ref["type"] == "recruit":
        nm = ref.get("name")
        pos = ref.get("position")
        stars = ref.get("stars")
        if ref.get("status") == "commit":
            big = isinstance(stars, int) and stars >= 4
            if kind == "analyst":
                return f"Commitment confirmed: {stars}-star {pos} {nm} is in for {school}. Big get for the class."
            if kind == "brand":
                # "BREAKING" is for a genuinely big commit (4-5 star); routine pledges
                # just get reported.
                return (f"BREAKING: {stars}-star {pos} {nm} commits to {school}." if big
                        else f"{stars}-star {pos} {nm} commits to {school}.")
            if kind == "local_fan":
                return f"WELCOME TO {word.upper()} NATION {nm}. we are so back on the trail"
            return f"{nm} to {school} is a statement on the recruiting trail."
        if kind == "analyst":
            return f"Buzz building on {stars}-star {pos} {nm}. {ref.get('leader') or school} look to be in front, interest {ref.get('interest')}."
        if kind == "local_fan":
            return f"need {nm} in red so bad it hurts. interest at {ref.get('interest')} lets gooo"
        return f"Keep an eye on {stars}-star {pos} {nm}, a real priority for {school}."

    if ref and ref["type"] == "portal":
        return (f"Portal: {ref.get('name')} ({ref.get('position')}) headed to {ref.get('to')}."
                if kind in ("insider", "brand", "reporter")
                else f"losing {ref.get('name')} to the portal stings. depth is gonna be thin")

    if ref and ref["type"] == "hot_seat":
        return (f"Sources: the seat is getting hot for {ref.get('coach')} at {ref.get('team')}. Heat index {ref.get('heat')}."
                if kind in ("insider", "personality", "brand")
                else f"if {ref.get('coach')} can get fired then anybody can. wild times in this sport")

    if ref and ref["type"] == "article":
        head = ref.get("headline")
        by = ref.get("reporter") or ref.get("outlet")
        mine = bool(by) and by == acct.get("name")
        if mine:
            return f"New from me: {head}. Story up now."
        if kind in ("insider", "reporter", "beat", "analyst", "columnist"):
            return f"Strong piece from {by}: {head}. Worth your time."
        if kind == "personality":
            return f"Good read from {by}: {head}. My take in the replies."
        if kind == "brand":
            return f"{head}."
        return f"everyone needs to read this: {head}"

    # No ref: voice-only filler. National voices talk about the national scene
    # (the top team, the chase pack); the beat and the fans stay on the program.
    national_voice = kind not in ("local_fan", "national_fan") and acct.get("scope") != "local"
    if national_voice:
        nat = dynasty.get("national", {}) or {}
        ap = [r for r in (nat.get("ap_top25") or []) if r.get("team")]
        top = ap[0]["team"] if ap else "the favorites"
        chase = ap[1]["team"] if len(ap) > 1 else "the chase pack"
        nat_fillers = {
            "brand": f"It is a great day for college football. {top} sit on top of the polls. Who is coming for them?",
            "insider": "Working a few national jobs and portal threads tonight. More soon.",
            "reporter": f"All eyes on {top} and the top of the polls. The race is wide open behind them.",
            "personality": f"{top} are the team to beat right now, but {chase} are closer than people think. Buckle up.",
            "analyst": "Filing fresh national recruiting and portal notes tonight. A few boards are shifting.",
            "columnist": f"The resume that matters most early belongs to {top}. We will see if it holds up.",
        }
        return nat_fillers.get(kind, f"another loaded week at the top of the sport, {top} leading the way")

    rec = team.get("record", {}).get("overall", "")
    fillers = {
        "brand": f"It is a great day to be a college football fan. {school} ({rec}) back in action this week.",
        "insider": "Working a few things on the carousel and the board. More soon.",
        "reporter": f"Notebook day around {school}. Practice was crisp, mood is up.",
        "beat": f"Quiet news day on the {word} beat. Checking in on a couple of depth chart battles.",
        "personality": f"The thing nobody wants to say about {school} this season: they are exactly who their record says they are.",
        "analyst": "Filing a couple of fresh predictions tonight. Momentum is shifting on a few boards.",
        "columnist": f"The {school} resume is starting to talk. We will see if the committee listens.",
        "local_fan": f"never a normal week being a {word.lower()} fan. love this dumb team",
        "national_fan": f"{word} fans really think this is their year again. every single season man",
    }
    return fillers.get(kind, "another week of college football, lets ride")


def _pick_ref(acct: dict, surface: dict, usage: dict[str, int], rng: random.Random) -> str:
    """Choose which event (if any) an account reacts to, biased by its archetype
    and capped per event so the marquee result and rankings get covered without any
    single article or game being echoed by everyone. Returns a ref key or ''."""
    refs = surface["refs"]
    if not refs:
        return ""
    kind = acct["kind"]
    # Media who wrote a piece this week mostly post their own byline.
    own = [k for k, r in refs.items()
           if r["type"] == "article" and r.get("reporter") and r["reporter"] == acct.get("name")
           and usage.get(k, 0) < 2]
    if own and kind in ("insider", "reporter", "beat", "analyst", "columnist") and rng.random() < 0.85:
        usage[own[0]] = usage.get(own[0], 0) + 1
        return own[0]
    # A healthy share of pure voice-only takes (no reference), like a real feed.
    no_ref = {"brand": 0.15, "local_fan": 0.3, "national_fan": 0.3}.get(kind, 0.45)
    if rng.random() < no_ref:
        return ""
    weights = _ARCHETYPE_REF_WEIGHTS.get(kind, _ARCHETYPE_REF_WEIGHTS["default"])
    scope_mult = _scope_mult(acct)
    pool = []
    for k, r in refs.items():
        cap = _REF_CAPS.get(r["type"], 2)
        if usage.get(k, 0) >= cap:
            continue
        w = weights.get(r["type"], 1)
        # an article the account did not write is lower priority than its own beat
        if r["type"] == "article" and r.get("reporter") != acct.get("name"):
            w = max(1, w - 1)
        # bias by scope: national voices to the national scene, beat to the program
        w = w * scope_mult.get(r.get("scope", "national"), 1.0)
        if w > 0:
            pool.append((k, w))
    if not pool:
        return ""
    total = sum(w for _, w in pool)
    roll = rng.uniform(0, total)
    acc = 0.0
    chosen = pool[-1][0]
    for k, w in pool:
        acc += w
        if roll <= acc:
            chosen = k
            break
    usage[chosen] = usage.get(chosen, 0) + 1
    return chosen


def _mock_reply_text(acct: dict, parent: dict, dynasty: dict) -> str:
    """A fan reply/quote that fits the post it answers, keyed off the parent post's
    topic (game, ranking, conference race, recruiting, portal, preview). Replies are
    never a generic line stapled onto an unrelated post; seeded per (account, parent)
    so each is stable but varied."""
    local = acct.get("kind") == "local_fan"
    ref = parent.get("ref") or {}
    rtype = ref.get("type") or ""
    won = ref.get("result") == "W"
    label = (ref.get("label") or "").upper()
    team = dynasty.get("team", {}) or {}
    w_low = _team_word(team.get("name", ""), team.get("nickname", "")).lower()

    if rtype == "game" and label == "FINAL":
        opts = ((["this is the standard now", f"{w_low} football is back", "huge win, dont let up"] if won
                 else ["this one stings bad", "we have to be better than that", "long week ahead"]) if local
                else (["one game in, relax", "the box score flatters them", "fine, they looked good i guess"] if won
                      else ["lol called it", "told everyone they were overrated", "and the panic sets in right on time"]))
    elif rtype == "game":  # preview / up next
        opts = (["nervous about this one ngl", "we win this comfortably", "feels like a trap game"] if local
                else ["im taking the points here", "give me the over", "fading the hype on this one"])
    elif rtype == "ranking":
        opts = (["we are so disrespected in this", "this ranking is a joke", "put some respect on the name"] if local
                else ["this poll is about right", "way too high, prove it first", "preseason polls mean nothing"])
    elif rtype == "confrace":
        opts = (["our year, book it", "we are winning this league", "finally our time"] if local
                else ["that race is wide open", "every fanbase says this every year", "depth wins that league"])
    elif rtype == "recruit":
        opts = (["the staff is COOKING", "huge get, who is next", "recruiting is healing me"] if local
                else ["solid pickup", "we will see if it sticks", "commitment season is chaos"])
    elif rtype == "portal":
        opts = (["we needed that piece badly", "addition by subtraction honestly", "keep working the portal"] if local
                else ["the portal never sleeps", "roster churn is wild now", "good luck with continuity"])
    else:
        opts = (["here for all of it", "lets go, this is the week", "every week with this team"] if local
                else ["college football is so back", "wild season already", "this sport is undefeated"])
    return random.Random(str(acct.get("id", "")) + str(parent.get("id", ""))).choice(opts)


def _mock_posts(dynasty: dict, accounts: list[dict], surface: dict, year: int, week: int) -> list[dict]:
    """A full ~40+ post timeline grounded in the week, with a few reply chains. The
    default path in dev (LLM off), so it must be rich. Events are assigned by an
    archetype-weighted, capped picker so the marquee result and rankings get
    covered while the timeline stays varied (not everyone echoing one article)."""
    selected = _select(accounts, year, week)
    rng = random.Random(f"{year}:{week}:feed:mockrefs")
    usage: dict[str, int] = {}

    roots: list[dict] = []
    for acct in selected:
        ref_key = _pick_ref(acct, surface, usage, rng)
        pick = surface["refs"].get(ref_key) if ref_key else None
        text = _mock_text(acct, pick, dynasty)
        roots.append(_attach_author({"text": text, "ref_key": ref_key}, acct))

    roots = _finalize_roots(roots, surface, year, week)

    # A few fan reply/quote chains off the most-liked posts.
    fan_accts = [a for a in accounts if a["kind"] in ("local_fan", "national_fan")]
    rng.shuffle(fan_accts)
    hot = sorted(roots, key=lambda p: -p["metrics"]["likes"])[:8]
    replies: list[dict] = []
    for i, parent in enumerate(hot):
        if i >= len(fan_accts):
            break
        acct = fan_accts[i]
        is_quote = rng.random() < 0.5
        text = _mock_reply_text(acct, parent, dynasty)
        raw = {"text": text, ("quote_of" if is_quote else "reply_to"): parent["id"]}
        replies.append(_attach_author(raw, acct))
    return _merge_replies(roots, replies, surface, year, week)


# =========================================================================
# persona continuity + entry point
# =========================================================================
def _record_personas(year: int, accounts: list[dict]) -> None:
    """Keep the recurring fan + personality handles consistent across weeks."""
    for a in accounts:
        if a["kind"] in ("local_fan", "national_fan", "personality"):
            try:
                narrative.update_persona(year, a["name"], {"handle": a["handle"], "feed_kind": a["kind"]})
            except Exception:
                pass


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    accounts = _accounts(dynasty, year, week)
    surface = _surface(dynasty, year, week)
    progress.set_sub_step("Building social timeline")
    source = "mock"
    posts: list[dict] = []
    # Primary path: the editorial engine's per-beat social timeline (rundown-driven,
    # persona-voiced, mood-shaded, with a debate take). Robust on small models because
    # each anchor post is its own focused call and the fan volume is templated, unlike
    # the legacy batched clusters. Finalize reuses this module's id/metric/threading.
    if use_llm and base.llm_available():
        try:
            from .. import editorial
            ed = editorial.social_posts(dynasty, year, week)
            if ed:
                posts = _finalize_roots(ed, surface, year, week)  # already in post shape
                source = "llm"
        except Exception:
            posts = []
    if not posts and use_llm and base.llm_available():
        try:
            posts = _generate_llm(dynasty, accounts, surface, year, week)
            source = "llm"
        except Exception:
            posts = _mock_posts(dynasty, accounts, surface, year, week)
            source = "mock"
    if not posts:
        posts = _mock_posts(dynasty, accounts, surface, year, week)
        source = "mock"

    _record_personas(year, accounts)
    # Fold in any coach-caused reactions the world engine logged this week (a
    # reporter breaking what the coach told him, the quote-tweets that followed),
    # so they ride along through a full re-roll, deduped by their stable ids.
    posts = world_events.merge_feed_posts(posts, year, week)
    return base.sanitize({"module": MODULE, "source": source, "week": week, "posts": posts})
