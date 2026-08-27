"""News feed.

National and program-specific articles written in distinct fictional outlet
voices. Outlets and reporters carry reliability scores. Coaching-carousel
items are framed as insider reports whose credibility is tracked per reporter,
so some reports prove accurate and others do not over the season.

Outlet names are fictional analogs rather than real brands, so unreliable or
incorrect reporting is never attributed to a real publication.
"""
from __future__ import annotations

import threading
from typing import Any

from .. import cache, customization, llm, narrative, progress, world_events
from . import article_detail, base

MODULE = "news_feed"

# The week's coverage (national + program articles, each with a full reader page,
# plus insider reports) is generated ONCE and cached here, then read by BOTH this
# module and the top-stories slider. Articles are born with their full body, and
# the reader page is built deterministically from that body (no second model call),
# so a week costs one batched news call instead of ~25-30 (a short pass plus a
# per-article expansion plus a separate slider pass).
_COVERAGE_KEY = "_newsroom"

# Single-flight guard for the shared coverage build. The week's coverage is the one
# expensive generation (the national + program passes) read by FOUR consumers: this
# module, the top-stories slider, the feed, and the news-reaction cascade. On a fresh
# week they all miss the `_newsroom` cache at once; without coalescing, each would
# launch its OWN duplicate national+program generation and they would thrash a single
# local model until one hits the read timeout (the cache-stampede that made week-1
# generation crawl). A per-(year, week) lock lets the first caller build it while the
# rest wait, then the double-checked cache hands them the finished result.
_coverage_locks: dict[tuple[int, int], threading.Lock] = {}
_coverage_locks_guard = threading.Lock()


def _coverage_lock(year: int, week: int) -> threading.Lock:
    key = (year, week)
    with _coverage_locks_guard:
        lk = _coverage_locks.get(key)
        if lk is None:
            lk = _coverage_locks[key] = threading.Lock()
        return lk

# Outlets and reporters are user-editable (see customization.py). Read at call
# time so edits in the Customize flow flow straight into bylines and prompts.
# National coverage draws on the national outlets; program coverage on the local
# beat. _outlets() is the combined list the API still hands the frontend.
def _national_outlets():
    return customization.section("media_orgs_national")


def _local_outlets():
    return customization.section("media_orgs_local")


def _outlets():
    return _national_outlets() + _local_outlets()


def _reporters():
    return customization.section("reporters")


def _outlets_desc(outlets) -> str:
    return "\n".join(f'  - {o["name"]} ({o["voice"]}; reliability {o["reliability"]})' for o in outlets)


# The article object shape (shared by both passes). pull_quote and quotes let the
# writer supply the reader-page enrichment in the same pass, so the deterministic
# detail builder wires in real quotes and a pull quote without a second LLM call.
_ARTICLE_SHAPE = (
    'Each article object: {"outlet", "reporter", "reliability" (0-100), "category", '
    '"headline", "dek" (one-line summary), "body", "pull_quote" (a punchy one-sentence '
    'quote pulled from the story, or null), "quotes" (array of {"speaker", "role", '
    '"text"}), "timestamp" (e.g. "3h ago")}.\n'
    'The "body" is the FULL article: 3 to 4 substantial paragraphs separated by blank '
    "lines, specific and in-depth (name the teams, scores, ranks, records, and stats), the "
    "way a feature on a major site reads. It is shown to the reader as-is, so make it "
    "complete, not a teaser."
)

_INSIDER_SHAPE = (
    'Each insider_report object: {"outlet", "reporter", "reliability" (0-100), "category" '
    '("Coaching carousel"), "headline", "dek", "body", "timestamp", "claim" (the rumor), '
    '"confidence" (0-100), "credibility" (reporter track record 0-100), "status" (one of: '
    "developing, corroborated, disputed)}."
)

SYSTEM = (
    "You are the beat writer desk covering ONE college football program for its local "
    "outlets, each with its own voice and reliability. Write tight, substantive, "
    "believable articles grounded in the program's actual data (its record, ranking, last "
    "result, next opponent, roster, recruiting board, and what the coach has said on the "
    "record). Every paragraph carries a specific fact. Never use dashes as punctuation; use "
    "commas or periods, never dashes."
)

SYSTEM_NATIONAL = (
    "You are the national desk of a college football media network, writing the week's "
    "national coverage from several outlets, each with its own voice and reliability. You "
    "cover the WHOLE sport: the title and playoff race, marquee games and upsets between "
    "ranked teams, the Heisman race, the statistical leaders, conference races, and the "
    "coaching carousel. Ground every article in the national landscape you are given (real "
    "teams, scores, records, ranks, and stats from THIS fictional universe). Lead with the "
    "biggest thing that actually happened. Never write generic filler like 'the picture is "
    "taking shape'; every paragraph must carry a specific team, score, record, or stat. "
    "Coaching-carousel items are insider reports: some prove right, some wrong, each carries "
    "a credibility score. Never use dashes as punctuation; use commas or periods, never dashes."
)


def _national_prompt(dynasty: dict, *, has_carousel: bool = True) -> str:
    team = dynasty["team"]["name"]
    no_scores = ""
    if base.is_season_open(dynasty):
        no_scores = (
            "No games have been played yet this season: every team is 0-0. Do NOT state any final "
            "score and do NOT say a team beat, crushed, defeated, edged, or topped another. Write "
            "season previews and expectations only.\n")
    # Only ask for carousel/insider content when the rundown actually surfaced hot
    # seats; an unconditional ask makes a small model INVENT a firing to satisfy it.
    carousel_thread = (
        "and the coaching carousel (ground every carousel claim in the hot-seat coaches listed in "
        "the brief, never invent a coach)" if has_carousel else
        "(there is NO coaching-carousel news this week: return \"insider_reports\": [] and write "
        "no rumor or hot-seat content)")
    return (
        f"Write the NATIONAL news feed for {dynasty['season']['week_label']}. This is coverage of "
        f"the WHOLE sport, NOT {team} (the user's program has its own separate section). Use the "
        "NATIONAL LANDSCAPE brief above as your source of truth.\n\n"
        "Across the articles, cover the biggest threads: lead with the most newsworthy result or "
        "storyline (an upset or a ranked clash if one happened), then the playoff and title race, "
        "the Heisman race (only when the brief lists contenders, citing their actual numbers), a "
        f"marquee game between OTHER ranked teams, {carousel_thread}.\n\n"
        f"National outlets available:\n{_outlets_desc(_national_outlets())}\n\n"
        "Return STRICT JSON with this shape:\n"
        "{\n"
        '  "national": [ 3 to 4 national articles ],\n'
        '  "insider_reports": [ up to 3 coaching-carousel insider items ]\n'
        "}\n"
        + _ARTICLE_SHAPE + "\n"
        "For `quotes`, use fictional analysts, players, or OTHER programs' head coaches (named in "
        f"the context); NEVER the {team} head coach.\n"
        f"Do NOT write about {team}, its coach, players, game, or recruits anywhere.\n"
        "CRITICAL, this is a FICTIONAL universe: NEVER name a real-life coach or player (no real "
        "Big Ten, SEC, or any conference coaches or players). When a story refers to another "
        "program's head coach, use the EXACT fictional name the brief gives for that team (each team "
        "in the brief has its coach in parentheses); if you do not have a name, write 'the head "
        "coach' or 'the staff'.\n"
        + no_scores +
        "NEVER invent a player, statistic, or score. Name an individual player ONLY when he appears "
        "in the brief (its Heisman race, statistical leaders, or polls); if the brief lists none "
        "(early in the season), write about teams and matchups, not invented star players or stats.\n"
        "When the brief lists a game as a PREVIEW (not yet played), do NOT invent a score, a winner, "
        "or any play that happened; write a forward-looking preview of the matchup.\n"
        + _INSIDER_SHAPE + " Output JSON only."
    )


def _program_prompt(dynasty: dict) -> str:
    team = dynasty["team"]["name"]
    opener = ""
    if base.is_season_open(dynasty):
        opener = (
            "This is the SEASON OPENER, before any games have been played, so the feed is offseason / "
            "season-preview coverage, not recaps. Lead with the current landscape: the coaching "
            "situation (if the head coach is in his FIRST season, make that the headline story, "
            "including how last season ended and the new direction), preseason expectations, key "
            "returners, and the recruiting class. Use these grounded facts:\n"
            + base.season_landscape(dynasty) + "\n\n")
    return (
        f"Write the PROGRAM news feed for {dynasty['season']['week_label']}, covering {team} (the "
        "user's program). " + opener
        + "Cover the things actually happening with this program: the last result and what it means, "
        "the next opponent and the matchup, the players driving the season, and the recruiting board.\n\n"
        f"Local/program outlets available:\n{_outlets_desc(_local_outlets())}\n\n"
        'Return STRICT JSON with this shape:\n{\n  "program": [ up to 4 articles about ' + team + " ]\n}\n"
        + _ARTICLE_SHAPE + "\n"
        "For `quotes`, you may quote players, coordinators, and analysts (all fictional). Quote the "
        "head coach ONLY with words he actually said that appear in the provided context (his media "
        "texts or post-game press conference); otherwise do not put quotation marks around his words. "
        "Output JSON only."
    )


def _article(outlet: str, reporter: str, reliability: int, category: str,
             headline: str, dek: str, body: str, ts: str) -> dict[str, Any]:
    return {
        "outlet": outlet, "reporter": reporter, "reliability": reliability,
        "category": category, "accent": base.accent_for(category),
        "headline": headline, "dek": dek, "body": body, "timestamp": ts,
    }


def _wl(rec: str) -> tuple[int, int]:
    try:
        w, l = str(rec).split("-")[:2]
        return int(w), int(l)
    except (ValueError, AttributeError):
        return 0, 0


def _biggest_result(dynasty: dict) -> dict[str, Any] | None:
    """The single most newsworthy non-user final on this week's scoreboard (an upset
    or a ranked clash), for the mock national lead. None when nothing has been played."""
    sb = (dynasty.get("national") or {}).get("scoreboard") or []
    best, best_sig = None, -1
    for g in sb:
        if g.get("status") != "final" or g.get("user"):
            continue
        if g.get("home_score") is None or g.get("away_score") is None:
            continue
        home, away = g.get("home") or {}, g.get("away") or {}
        hs, as_ = g["home_score"], g["away_score"]
        win, lose, ws, ls = (home, away, hs, as_) if hs >= as_ else (away, home, as_, hs)
        wr, lr = win.get("rank"), lose.get("rank")
        upset = bool(lr) and (not wr or wr > lr + 4)
        sig = (100 - (wr + lr)) if (wr and lr) else (80 - lr if upset else (40 - (wr or lr or 25) if (wr or lr) else 5))
        if sig > best_sig:
            best_sig = sig
            best = {
                "winner": f"No. {wr} {win.get('name')}" if wr else win.get("name"),
                "loser": f"No. {lr} {lose.get('name')}" if lr else lose.get("name"),
                "score": f"{ws}-{ls}", "upset": upset,
            }
    return best


def _mock(dynasty: dict) -> dict[str, Any]:
    """Dynasty-grounded fallback. Every claim derives from the actual record,
    ranking, latest result, upcoming game, poll, and Heisman board so the feed
    tracks the simulated season instead of a fixed demo narrative."""
    t = dynasty["team"]
    name = t["name"]
    school = t.get("school", name)
    nick = name.split()[-1]
    rec = t["record"]["overall"]
    cfp = t["rankings"].get("cfp")
    ap = t["rankings"].get("ap")
    rank_str = (f"No. {cfp} in the playoff projection" if cfp
                else f"No. {ap} nationally" if ap else "unranked")
    up = dynasty["schedule"]["upcoming"]
    recent = dynasty["schedule"].get("recent_results") or []
    last = recent[0] if recent else None
    qb = dynasty["roster"]["key_players"][0]
    edge = next((p for p in dynasty["roster"]["key_players"] if p["position"] == "EDGE"),
                dynasty["roster"]["key_players"][-1])
    targets = dynasty["recruiting"].get("targets") or []
    commit_target = targets[0] if targets else None

    ap25 = (dynasty.get("national", {}) or {}).get("ap_top25") or []
    top_names = [r.get("team") for r in ap25[:5] if r.get("team")]
    heis = (dynasty.get("national", {}) or {}).get("heisman_frontrunners") or []

    national = []
    # Lead with the week's biggest actual result when games have been played, so the
    # offline feed tracks the season instead of an evergreen "picture is taking shape".
    big = _biggest_result(dynasty)
    if big:
        wn, ln, score, upset = big["winner"], big["loser"], big["score"], big["upset"]
        national.append(_article(
            "The Press Box", "Dana Reyes", 93, "CFP watch",
            (f"{wn} stuns {ln} {score}" if upset else f"{wn} takes down {ln} {score}"),
            (f"An upset shakes up the national picture." if upset
             else f"A marquee result reshapes the top of the polls."),
            (f"{wn} {'pulled off the upset over' if upset else 'handled'} {ln}, winning {score}. "
             f"The result moves the needle on the playoff race and the resume math at the top of the sport. "
             f"{', '.join(top_names[:3]) or 'The contenders'} remain the teams to beat as the schedule hardens."),
            "1h ago"))
    if top_names:
        national.append(_article(
            "The Press Box", "Dana Reyes", 93, "CFP watch",
            f"{top_names[0]} holds the top spot as the race tightens",
            f"{', '.join(top_names[:3])} sit atop the latest national rankings.",
            (f"{top_names[0]} leads the way, with {', '.join(top_names[1:4]) or 'a tight chase pack'} in "
             f"pursuit. Resume and strength of schedule will sort the contenders from the pretenders over "
             f"the next month."),
            "2h ago"))
    if heis:
        h0 = heis[0]
        sl = h0.get("stat_line")
        national.append(_article(
            "Saturday Authority", "Marcus Hale", 89, "Heisman watch",
            f"{h0.get('name')} surges to the front of the Heisman race",
            (f"The {h0.get('team', '')} {h0.get('position', 'standout')} is pacing the field at {sl}." if sl
             else f"The {h0.get('team', '')} {h0.get('position', 'standout')} is pacing the field."),
            (f"{h0.get('name')} of {h0.get('team', '')} has separated himself in the Heisman picture"
             + (f", putting up {sl}. " if sl else ". ")
             + "The production is undeniable, and every week under the lights only strengthens the case."),
            "5h ago"))

    program = []
    if base.is_season_open(dynasty):
        # Season opener: lead with the program's landscape (coaching change, last
        # season, the year ahead) instead of a game recap.
        hc = t.get("head_coach", {}) or {}
        coach = hc.get("name", "the head coach")
        tenure = int(hc.get("tenure_years") or 1)
        hist = dynasty.get("history") or []
        last_h = hist[0] if hist else None
        pred = base.predecessor_coach(dynasty)
        if tenure <= 1:
            headline = f"A new era begins: {coach} takes over at {school}"
            dek = f"The {nick} turn the page after going {last_h['overall'] if last_h else 'through change'} a year ago."
            body = (
                f"{coach} is the new head coach at {name}"
                + (f", replacing {pred}. " if pred else ". ")
                + (f"The program is coming off a {last_h['overall']} season ({(last_h.get('result') or '').lower()}), "
                   f"and the brief is to change direction. " if last_h else "")
                + f"They open the year {rank_str}.\n\n"
                f"All eyes are on how quickly the new staff can put its stamp on the roster.")
        else:
            headline = f"Year {tenure}: {coach} and {school} open {dynasty['season'].get('year')}"
            dek = f"Coming off {last_h['overall'] if last_h else 'last season'}, the {nick} reset their goals."
            body = (
                f"{name} begin year {tenure} under {coach}"
                + (f", a season after going {last_h['overall']} ({(last_h.get('result') or '').lower()}). " if last_h else ". ")
                + f"They enter {rank_str}, with a roster the staff believes can take the next step.")
        program.append(_article("Cornhusker Insider", "Jenna Whitlock", 85, "Program", headline, dek, body, "2h ago"))
    if last:
        won = last.get("result") == "W"
        program.append(_article(
            "Cornhusker Insider", "Jenna Whitlock", 85, "Program",
            f"{school} {'holds off' if won else 'falls to'} {last.get('opponent')} {last.get('score', '')}".strip(),
            f"The {nick} move to {rec} and sit {rank_str}.",
            (f"{name} {'got the job done' if won else 'came up short'} against {last.get('opponent')}, "
             f"{'improving to' if won else 'slipping to'} {rec}. {edge['name']} and the front seven "
             f"{'set the tone' if won else 'kept it close'}.\n\n"
             f"Attention turns to {up.get('opponent')}, {'at home' if up.get('home') else 'on the road'}, "
             f"with the line opening {up.get('spread', 'pick em')}."),
            "1h ago"))
    else:
        program.append(_article(
            "Cornhusker Insider", "Jenna Whitlock", 85, "Program",
            f"{school} set to open {'at home against' if up.get('home') else 'at'} {up.get('opponent')}",
            f"The {nick} begin the year {rank_str}.",
            (f"The season is here. {name} open {'hosting' if up.get('home') else 'traveling to'} "
             f"{up.get('opponent')} on {up.get('tv', 'national TV')}, line {up.get('spread', 'pick em')}. "
             f"{qb['name']} takes the first snaps of what the program hopes is a special run."),
            "1h ago"))

    program.append(_article(
        "Cornhusker Insider", "Jenna Whitlock", 85, "Program",
        f"Preview: {school} vs {up.get('opponent')} this week",
        f"A {up.get('opponent_record', '')} opponent {'visits' if up.get('home') else 'hosts the'} {nick}.",
        (f"{name} ({rec}) face {up.get('opponent')} ({up.get('opponent_record', '')}) "
         f"{'at home' if up.get('home') else 'on the road'} for a {up.get('kickoff', 'weekend')} kickoff on "
         f"{up.get('tv', 'TV')}. The line opened {up.get('spread', 'pick em')}."),
        "4h ago"))

    if commit_target:
        program.append(_article(
            "RecruitWire", "Theo Marsh", 82, "Recruiting",
            f"{commit_target.get('stars')}-star {commit_target.get('position')} {commit_target.get('name')} a key {school} target".strip(),
            f"Interest sits at {commit_target.get('interest')}/100 with {commit_target.get('leader') or 'no clear leader'} out front.",
            (f"{commit_target.get('name')}, out of {commit_target.get('hometown', 'a key region')}, remains a "
             f"priority on the {name} board. The staff is pushing, and every contact this month matters as the "
             f"recruitment heats up."),
            "6h ago"))

    insider_reports = [
        {
            "outlet": "Coaching Confidential", "reporter": "Priya Anand", "reliability": 64,
            "category": "Coaching carousel", "accent": base.accent_for("Coaching carousel"),
            "headline": "Sources: a brand-name SEC job could open sooner than expected",
            "dek": "Donor frustration is mounting after another November fade.",
            "body": ("Multiple people with knowledge of the situation describe a fan base out of patience "
                     "and a booster collective ready to fund a buyout. Nothing is final, and the athletic "
                     "director has not signaled a decision, but the temperature is rising."),
            "timestamp": "3h ago",
            "claim": "A marquee SEC head coach will be out before bowl season.",
            "confidence": 58, "credibility": 64, "status": "developing",
        },
        {
            "outlet": "The Press Box", "reporter": "Dana Reyes", "reliability": 93,
            "category": "Coaching carousel", "accent": base.accent_for("Coaching carousel"),
            "headline": "Reported: search firm retained for a Group of Five opening",
            "dek": "The first confirmed move of the cycle is now official.",
            "body": ("A G5 program has formally retained a search firm and begun building a candidate "
                     "pool. This one is corroborated by multiple independent outlets, a notch above the "
                     "usual carousel speculation."),
            "timestamp": "7h ago",
            "claim": "A Group of Five program has begun a formal coaching search.",
            "confidence": 90, "credibility": 93, "status": "corroborated",
        },
        {
            "outlet": "Coaching Confidential", "reporter": "Priya Anand", "reliability": 64,
            "category": "Coaching carousel", "accent": base.accent_for("Coaching carousel"),
            "headline": "Rumor: a coordinator candidate is drawing midseason interest",
            "dek": "Treat this one with caution given the source's mixed track record.",
            "body": ("A single-source report links a rising assistant to an opening elsewhere. The "
                     "reporter has been wrong on similar items this season, so the credibility score "
                     "reflects the uncertainty."),
            "timestamp": "9h ago",
            "claim": "An assistant will leave for a coordinator role midseason.",
            "confidence": 35, "credibility": 64, "status": "disputed",
        },
    ]

    return {"national": national, "program": program, "insider_reports": insider_reports}


def _record_personas(year: int) -> None:
    """Persist reporter reliability/affiliation so it stays consistent."""
    for r in _reporters():
        narrative.update_persona(year, r["name"], {
            "affiliation": r["outlet"],
            "reliability": r["reliability"],
            "beat": r["beat"],
        })


def _generate_national(dynasty: dict, year: int, week: int) -> dict[str, Any] | None:
    """The dedicated national pass: a non-reactive context (so the user's result,
    presser, and storylines never bleed in) grounded in the rich national brief.
    Returns the national articles + coaching-carousel insider reports, or None on
    failure (the caller falls back to the mock national bucket)."""
    progress.set_sub_step("National coverage")
    try:
        context = base.news_context(dynasty, year, week, reactive=False)
        grounding = base.grounding_facts(dynasty)
        # The editorial engine picks the slate (scored candidates, previews marked,
        # coaches inlined); the legacy save-mined digest is the fallback only.
        has_carousel = True
        try:
            from .. import editorial
            rundown = editorial.build_rundown(dynasty, year, week)
            brief = editorial.national_brief(dynasty, year, week, rundown=rundown)
            has_carousel = any(c.get("type") == "hot_seat_watch" for c in rundown.get("national") or [])
        except Exception:
            brief = base.national_brief(dynasty, year, week)
        if brief:
            grounding += "\n\n" + brief
        return llm.generate_json(SYSTEM_NATIONAL, _national_prompt(dynasty, has_carousel=has_carousel),
                                 cached_context=context, grounding=grounding, max_tokens=4500)
    except Exception:
        return None


def _generate_program(dynasty: dict, year: int, week: int) -> dict[str, Any] | None:
    """The program pass: the full reactive context (the coach's words, the last
    result, the live storylines) grounded for the user's team. Returns the program
    articles, or None on failure (the caller falls back to the mock program bucket)."""
    progress.set_sub_step("Program coverage")
    try:
        context = base.news_context(dynasty, year, week)
        grounding = base.reactive_grounding(dynasty, year, week)
        # Mood, stakes, and the scored program slate from the editorial engine.
        try:
            from .. import editorial
            grounding += "\n\n" + editorial.program_brief(dynasty, year, week)
        except Exception:
            pass
        return llm.generate_json(SYSTEM, _program_prompt(dynasty), cached_context=context,
                                 grounding=grounding, max_tokens=4000)
    except Exception:
        return None


def _team_identifiers(dynasty: dict) -> list[tuple[str, str]]:
    """(identifier, canonical-team) pairs for every team in the national landscape:
    full name, abbreviation, and bare nickname (the last word). Sorted longest-first so
    a greedy scan matches "Texas State" before "Texas". Used to catch self-matchup
    headlines a small model sometimes emits ("TCU and TCU Face Off")."""
    nat = dynasty.get("national") or {}
    pairs: dict[str, str] = {}

    def add(name: str | None, canonical: str | None, *, nickname: bool = True) -> None:
        if not name or not canonical:
            return
        pairs.setdefault(name.strip().lower(), canonical)
        if nickname:
            last = name.strip().split()
            if len(last) > 1:
                pairs.setdefault(last[-1].lower(), canonical)

    for key in ("ap_top25", "coaches_top25", "cfp_top12"):
        for r in nat.get(key) or []:
            if isinstance(r, dict):
                add(r.get("team"), r.get("team"))
                add(r.get("abbr"), r.get("team"), nickname=False)
    for g in nat.get("scoreboard") or []:
        for side in ("home", "away"):
            tm = g.get(side) or {}
            add(tm.get("name"), tm.get("name"))
            add(tm.get("abbr"), tm.get("name"), nickname=False)
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))


def _is_self_matchup(headline: str, idents: list[tuple[str, str]]) -> bool:
    """True when the same team is named twice in a headline (a broken matchup line like
    'TCU and TCU Face Off'). Greedy longest-match resolves each mention to its canonical
    team, then flags a repeat, so legitimate pairings ('Texas vs Texas State') are safe."""
    if not headline or not idents:
        return False
    hl = headline.lower()
    seen: list[str] = []
    i = 0
    while i < len(hl):
        matched = None
        for ident, canonical in idents:
            n = len(ident)
            if hl[i:i + n] == ident:
                before_ok = i == 0 or not hl[i - 1].isalnum()
                after_ok = i + n >= len(hl) or not hl[i + n].isalnum()
                if before_ok and after_ok:
                    matched = (canonical, n)
                    break
        if matched:
            seen.append(matched[0])
            i += matched[1]
        else:
            i += 1
    return len(seen) != len(set(seen))


def _article_subject_key(item: dict, dynasty: dict) -> str:
    """A coarse identity for an article so the feed never runs two near-identical pieces
    (a small model sometimes emits the same recruit-visit story twice). Keyed by the most
    prominent known person named in it (recruit/commit/player), else a normalized headline."""
    hay = ((item.get("headline") or "") + " " + (item.get("dek") or "")).lower()
    rec = dynasty.get("recruiting") or {}
    names: list[str] = []
    for grp in ("targets", "commits"):
        for r in rec.get(grp) or []:
            n = (r.get("name") or "").strip().lower()
            if n and n in hay:
                names.append(n)
    for p in (dynasty.get("roster") or {}).get("key_players") or []:
        n = (p.get("name") or "").strip().lower()
        if n and n in hay:
            names.append(n)
    cat = (item.get("category") or "").strip().lower()
    if names:
        return f"{cat}|{sorted(names)[0]}"
    return "".join(ch for ch in (item.get("headline") or "").lower() if ch.isalnum())[:48]


def _mentions_user(item: dict, dynasty: dict) -> bool:
    """True when a story names the user's program or coach. National coverage and
    insider reports must never be about the user (the program section owns that);
    a small model sometimes drifts there anyway, so this is the hard gate."""
    t = dynasty.get("team") or {}
    marks = [t.get("name"), t.get("school"), t.get("nickname"),
             ((t.get("head_coach") or {}).get("name"))]
    hay = " ".join(str(item.get(k) or "") for k in ("headline", "dek", "body", "claim")).lower()
    return any(m and str(m).lower() in hay for m in marks)


def _repair_headline(item: dict, idents: list[tuple[str, str]]) -> None:
    """In place: if an article's headline names the same team twice, fall back to its dek
    (the model wrote the real matchup there), so a broken 'TCU and TCU' line never reaches
    the reader. Leaves the article untouched when there is no usable dek to swap in."""
    headline = item.get("headline") or ""
    if not _is_self_matchup(headline, idents):
        return
    dek = (item.get("dek") or "").strip()
    if dek and not _is_self_matchup(dek, idents):
        item["headline"] = dek


def coverage(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    """The week's news coverage, generated once and cached, shared by this module and
    the top-stories slider. National and program articles come from two FOCUSED passes
    (so national depth is not squeezed by program coverage for tokens, and the user's
    program never bleeds into a national story). Each article carries a full reader page
    (`detail`) built deterministically from its body, so nothing expands lazily."""
    if not regenerate:
        cached = cache.get_module(year, week, _COVERAGE_KEY)
        if isinstance(cached, dict) and cached.get("program") is not None:
            return cached

    # Coalesce concurrent builders (see _coverage_lock): the first caller generates,
    # the rest block here and pick up the cached result below instead of each running
    # their own national+program passes.
    with _coverage_lock(year, week):
        if not regenerate:
            cached = cache.get_module(year, week, _COVERAGE_KEY)
            if isinstance(cached, dict) and cached.get("program") is not None:
                return cached

        progress.set_sub_step("Writing the week's articles")
        _record_personas(year)
        source = "mock"
        data: dict[str, Any] = {"national": [], "program": [], "insider_reports": []}
        if use_llm and base.llm_available():
            # Primary path: per-beat realization (one focused call per article, scored
            # rundown, canon-validated, templated within the model's budget).
            rc = None
            try:
                from .. import editorial
                rc = editorial.realize_coverage(dynasty, year, week, use_llm=use_llm)
            except Exception:
                rc = None
            if rc and (rc.get("national") or rc.get("program")):
                data["national"] = rc.get("national") or []
                data["program"] = rc.get("program") or []
                data["insider_reports"] = rc.get("insider_reports") or []
                source = rc.get("source", "llm")
            else:
                # Fallback: the older batched national/program passes.
                nat = _generate_national(dynasty, year, week)
                prog = _generate_program(dynasty, year, week)
                if isinstance(nat, dict) and nat.get("national"):
                    data["national"] = nat.get("national") or []
                    data["insider_reports"] = nat.get("insider_reports") or []
                    source = "llm"
                if isinstance(prog, dict) and prog.get("program"):
                    data["program"] = prog.get("program") or []
                    source = "llm"
        # Backfill any empty bucket from the grounded mock (cold start, no API key, or a
        # single failed pass), so the feed is always whole even if one pass fell through.
        # Empty insider reports are CORRECT at season open (no carousel exists yet), so
        # they are only backfilled once the season is underway.
        if not (data["national"] and data["program"] and data["insider_reports"]):
            m = _mock(dynasty)
            data["national"] = data["national"] or m["national"]
            data["program"] = data["program"] or m["program"]
            if not base.is_season_open(dynasty):
                data["insider_reports"] = data["insider_reports"] or m["insider_reports"]

        # The editorial truth layer: a canonical entity index + the world state, so
        # the validator can reject contradictions (wrong stars/position, real-coach
        # leaks, unfounded hot-seat narratives, fabricated season-open stats).
        ed_canon = ed_state = None
        try:
            from .. import editorial
            from ..editorial import canon as _canon, validate as _validate
            ed_canon = _canon.build(dynasty)
            ed_state = editorial.extract_state(dynasty, year, week)
        except Exception:
            _validate = None

        def _ok(item: dict, scope: str) -> bool:
            if _validate is None or ed_canon is None or ed_state is None:
                return True
            return _validate.passes(item, scope=scope, canon=ed_canon, state=ed_state)

        idents = _team_identifiers(dynasty)
        cov: dict[str, Any] = {"source": source, "national": [], "program": [], "insider_reports": []}
        floors = {"national": 2, "program": 2}
        for scope in ("national", "program"):
            seen_subjects: set[str] = set()
            for item in data.get(scope, []) or []:
                if not isinstance(item, dict) or not item.get("headline"):
                    continue
                if scope == "national" and _mentions_user(item, dynasty):
                    continue  # the user's program never appears in national copy
                _repair_headline(item, idents)  # fix self-matchup headlines ("TCU and TCU") first so dedup keys off the real one
                key = _article_subject_key(item, dynasty)
                if key in seen_subjects:
                    continue  # drop a duplicate story (the model sometimes repeats the same recruit-visit piece)
                if not _ok(item, scope):
                    continue  # contradicts the canon / engine state; dropped (step 3 will regenerate it)
                seen_subjects.add(key)
                item.setdefault("accent", base.accent_for(item.get("category", "National")))
                item["scope"] = scope
                item["detail"] = article_detail.build_detail(item, dynasty, year=year)  # full page, no LLM, no lazy
                cov[scope].append(item)
            # if validation thinned a scope below its floor, top up from the grounded
            # mock (which is canon-faithful by construction) so the feed stays whole
            if len(cov[scope]) < floors[scope]:
                for item in _mock(dynasty).get(scope, []) or []:
                    if len(cov[scope]) >= floors[scope]:
                        break
                    key = _article_subject_key(item, dynasty)
                    if key in seen_subjects or not item.get("headline"):
                        continue
                    seen_subjects.add(key)
                    item.setdefault("accent", base.accent_for(item.get("category", "National")))
                    item["scope"] = scope
                    item["detail"] = article_detail.build_detail(item, dynasty, year=year)
                    cov[scope].append(item)
        # Insider carousel rumors do not exist before any games are played; the 3b
        # model emits them anyway despite the prompt, so the gate is deterministic.
        if not base.is_season_open(dynasty):
            for r in data.get("insider_reports", []) or []:
                if isinstance(r, dict) and r.get("headline") and not _mentions_user(r, dynasty) and _ok(r, "national"):
                    r.setdefault("accent", base.accent_for(r.get("category", "Coaching carousel")))
                    cov["insider_reports"].append(r)

        cov = base.sanitize(cov)
        cache.set_module(year, week, _COVERAGE_KEY, cov)
        return cov


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    progress.set_sub_step("National and program news")
    cov = coverage(dynasty, year=year, week=week, use_llm=use_llm, regenerate=regenerate)
    result = {
        "module": MODULE,
        "source": cov.get("source", "mock"),
        "outlets": _outlets(),
        "reporters": _reporters(),
        "national": cov.get("national", []),
        "program": cov.get("program", []),
        "insider_reports": cov.get("insider_reports", []),
    }
    # Fold in any coach-caused articles the world engine filed this week (a reporter
    # writing up what the coach told him), so they ride a full re-roll, deduped by id.
    result = world_events.merge_news(result, year, week)
    return base.sanitize(result)
