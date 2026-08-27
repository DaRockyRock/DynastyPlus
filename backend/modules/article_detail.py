"""On-demand article expansion.

Given a feed article (or a top story) plus the dynasty state, produces a full
article page: body sections, an optional pull quote, a mix of coach/player/
analyst quotes, game and team stats, and betting lines/futures. Each article
gets a SUBSET of these elements (varied by category and a stable hash of the
headline) so detail pages read like real journalism rather than a template.
"""
from __future__ import annotations

import re
from typing import Any

from .. import llm
from . import base

_STOPWORDS = {
    "the", "a", "an", "to", "of", "and", "we", "our", "is", "it", "that", "this",
    "for", "on", "in", "was", "were", "be", "but", "not", "have", "has", "had",
    "they", "them", "you", "i", "with", "at", "as", "are", "im", "weve",
}


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _STOPWORDS}


def _coach_said(year: int) -> list[str]:
    """Everything the coach actually said this season: his post-game press
    conference answers and his own lines in text threads with media. Used to verify
    that a coach quote in an article is real and not fabricated by the model."""
    lines: list[str] = []
    try:
        from .. import interview
        for p in interview.completed(year):
            for t in p.get("turns", []):
                for k in ("answer", "follow_up_answer"):
                    if t.get(k):
                        lines.append(t[k])
    except Exception:
        pass
    try:
        from .. import directory, messages
        for cid, items in messages.threads(year).items():
            contact = directory.by_id(cid)
            if contact and (contact.get("profile") or {}).get("kind") in directory._MEDIA_KINDS:
                for it in items:
                    if it.get("from") == "me" and it.get("text"):
                        lines.append(it["text"])
    except Exception:
        pass
    return lines


def _faithful_to_real(quote: str, real_lines: list[str]) -> bool:
    """True when a quote is a faithful rendering of something the coach actually
    said (high content-word overlap with one real utterance), tolerating light
    paraphrase but rejecting an invented quote."""
    qt = _content_words(quote)
    if not qt:
        return False
    need = max(3, int(0.5 * len(qt)))
    for r in real_lines:
        if len(qt & _content_words(r)) >= need:
            return True
    return False


def _strip_unreal_coach_quotes(quotes: list[dict], dynasty: dict, year: int,
                               about_user: bool) -> list[dict]:
    """Drop any quote attributed to the user's head coach unless the article is
    about his program AND the quote faithfully matches something he actually said.
    This is the deterministic guarantee that the coach is never fabricated or quoted
    in an unrelated national story, regardless of what the model returns."""
    coach = ((dynasty.get("team") or {}).get("head_coach") or {}).get("name", "").lower()
    reals = _coach_said(year) if about_user else []
    out = []
    for q in quotes or []:
        if not isinstance(q, dict):
            continue
        speaker = (q.get("speaker") or "").lower()
        role = (q.get("role") or "").lower()
        is_coach = (coach and coach in speaker) or "head coach" in role
        if is_coach and (not about_user or not _faithful_to_real(q.get("text", ""), reals)):
            continue  # fabricated, stale-into-irrelevant, or on a non-user story: drop it
        out.append(q)
    return out


def _hash(text: str) -> int:
    return sum(ord(c) for c in (text or "x"))


def _split_byline(byline: str) -> tuple[str, str]:
    # "Dana Reyes, The Press Box" -> ("Dana Reyes", "The Press Box")
    if not byline:
        return "", ""
    parts = [p.strip() for p in byline.split(",", 1)]
    return (parts[0], parts[1] if len(parts) > 1 else "")


def _context_paragraphs(dynasty: dict, category: str) -> list[str]:
    t = dynasty["team"]
    up = dynasty["schedule"]["upcoming"]
    rec = t["record"]["overall"]
    paras = [
        (f"At {rec}, {t['name']} have built their case on substance. The next test comes "
         f"{'at home against' if up['home'] else 'on the road at'} {up['opponent']} "
         f"({up.get('kickoff', 'Saturday')}, {up.get('tv', 'national TV')}), a game that could "
         f"swing the {'playoff math' if 'CFP' in category else 'rest of the season'}."),
        (f"Head coach {t['head_coach']['name']} has leaned on a {t['stats']['points_per_game']} "
         f"points-per-game offense and a defense surrendering just {t['stats']['points_allowed']} "
         f"per night, a balance that travels in November."),
    ]
    return paras


def _quote_pool(dynasty: dict, reporter: str, outlet: str) -> dict[str, dict[str, Any]]:
    # NOTE: the head coach is the user. We never fabricate a quote from him. His
    # quotes only ever come from his real text messages with media and his
    # post-game press conference remarks, which the LLM path sees in news_context.
    # The mock pool therefore quotes only other people (players, coordinators,
    # recruits, insiders), who are fictional characters in this universe.
    t = dynasty["team"]
    players = dynasty["roster"]["key_players"]
    qb = players[0]
    edge = next((p for p in players if p["position"] in ("EDGE", "DT", "LB")), players[-1])
    staff = dynasty["coaching_staff"]
    oc = next((c for c in staff if "Offensive" in c["role"]), None)
    up = dynasty["schedule"]["upcoming"]["opponent"]
    target = (dynasty["recruiting"]["targets"] or [{}])[0]

    return {
        "player": {"speaker": qb["name"], "role": f"{qb['position']}, {t['school']}",
                   "text": (f"\"I just try to take care of the ball and let the offense operate. The "
                            f"line has been incredible and the guys on the outside make my job easy.\"")},
        "defense": {"speaker": edge["name"], "role": f"{edge['position']}, {t['school']}",
                    "text": ("\"We take it personally up front. If we set the edge and get off "
                             "blocks, everything else takes care of itself.\"")},
        "coordinator": {"speaker": oc["name"] if oc else "the offensive staff",
                        "role": (oc["role"] + ", " + t["school"]) if oc else t["school"],
                        "text": ("\"We want to play fast and make them defend the whole field. "
                                 "Tempo is a weapon when your guys are in great shape.\"")},
        "insider": {"speaker": reporter or "League sources", "role": outlet or "national insider",
                    "text": ("\"People around the program will tell you the temperature is real. "
                             "Whether it boils over before bowl season is the open question.\"")},
        "recruit": {"speaker": target.get("name", "The five-star target"),
                    "role": f"{target.get('position', 'prospect')} commit watch",
                    "text": ("\"The visit felt different. They are building something and they made "
                             "it clear where I fit. I have a big decision coming.\"")},
    }


def _stats(dynasty: dict) -> list[dict[str, str]]:
    t = dynasty["team"]
    s = t["stats"]
    players = dynasty["roster"]["key_players"]
    qb = players[0]
    rb = next((p for p in players if p["position"] == "RB"), None)
    rows = [
        {"label": "Points per game", "value": str(s["points_per_game"])},
        {"label": "Points allowed", "value": str(s["points_allowed"])},
        {"label": "Total offense", "value": f"{s['yards_per_game']} ypg"},
        {"label": "Turnover margin", "value": f"+{s['turnover_margin']}" if s["turnover_margin"] > 0 else str(s["turnover_margin"])},
        {"label": f"{qb['name']} ({qb['position']})", "value": qb["stat_line"]},
    ]
    if rb:
        rows.append({"label": f"{rb['name']} ({rb['position']})", "value": rb["stat_line"]})
    return rows


def _betting(dynasty: dict, category: str, want_game: bool, want_futures: bool) -> dict[str, Any] | None:
    t = dynasty["team"]
    up = dynasty["schedule"]["upcoming"]
    game = None
    if want_game:
        game = {
            "matchup": f"{t['abbreviation']} vs {up.get('opponent_abbr', up['opponent'])}",
            "spread": up.get("spread", "PK"),
            "total": "O/U 52.5",
            "moneyline": "-260 / +210",
        }
    futures: list[dict[str, str]] = []
    if want_futures:
        qb = dynasty["roster"]["key_players"][0]
        if category == "Heisman watch":
            futures = [
                {"label": f"{qb['name']} - Heisman", "value": "+650"},
                {"label": f"{qb['name']} - first-team All-Big Ten", "value": "-180"},
            ]
        elif category == "Coaching carousel":
            futures = [
                {"label": "Job opens before bowls", "value": "+140"},
                {"label": "Field includes a sitting P4 coach", "value": "+260"},
            ]
        else:
            futures = [
                {"label": f"{t['school']} to make the Playoff", "value": "-135"},
                {"label": f"{t['school']} to win the conference", "value": "+320"},
            ]
    if not game and not futures:
        return None
    return {"game": game, "futures": futures}


def _is_about_user(article: dict, dynasty: dict) -> bool:
    """True when the article is actually about the user's program (so it is fair to
    fold in the user's team context, players, stats, and betting). National items
    about OTHER teams get none of that, so the feed does not bend every story back
    to the user's team."""
    t = dynasty.get("team", {}) or {}
    if (article.get("category") or "") == "Program":
        return True
    needles = [t.get("name"), t.get("school"), t.get("nickname")]
    needles += [p.get("name") for p in (dynasty.get("roster", {}) or {}).get("key_players", [])[:6]]
    blob = " ".join(str(article.get(k, "")) for k in ("headline", "dek", "subheadline", "body", "lede")).lower()
    return any(n and n.lower() in blob for n in needles)


def _mock(article: dict, dynasty: dict) -> dict[str, Any]:
    title = article.get("headline", "")
    category = article.get("category", "National")
    dek = article.get("dek") or article.get("subheadline") or ""
    body = article.get("body") or article.get("lede") or ""
    byline_reporter, byline_outlet = _split_byline(article.get("byline", ""))
    reporter = article.get("reporter") or byline_reporter
    outlet = article.get("outlet") or byline_outlet

    about_user = _is_about_user(article, dynasty)
    h = _hash(title)
    sections = [p.strip() for p in str(body).split("\n\n") if p.strip()]

    # Only fold in the user's team context / players / stats / betting when the
    # story is actually about them. A national item about another program keeps
    # just its own body (plus an optional generic pull quote), never the coach.
    quotes: list[dict[str, Any]] = []
    if about_user:
        sections += _context_paragraphs(dynasty, category)
        pool = _quote_pool(dynasty, reporter, outlet)
        by_cat = {
            "CFP watch": ["player", "coordinator"],
            "Program": ["player", "defense"],
            "Heisman watch": ["player", "coordinator"],
            "Coaching carousel": ["insider"],
            "Recruiting": ["recruit", "insider"],
            "Transfer portal": ["insider"],
            "National": ["player"],
        }
        keys = by_cat.get(category, ["player"])
        n_quotes = 1 + (1 if h % 3 == 0 else 0)
        quotes = [pool[k] for k in keys[:max(1, min(n_quotes, len(keys)))]]

    pull_options = {
        "CFP watch": "Resume beats reputation now, and this one is built to last.",
        "Heisman watch": "The tape says he is already there. The narrative is just catching up.",
        "Coaching carousel": "Buyout math and donor patience are the only clocks that matter.",
        "Recruiting": "Close this one and the whole class follows.",
        "Transfer portal": "Continuity is the new currency in roster building.",
        "Program": "Find a way, advance, and turn the page.",
        "National": "November sorts the contenders from the pretenders.",
    }
    pull_quote = pull_options.get(category) if h % 2 == 0 else None

    # Team stats and betting lines are the user's, so only attach them to the
    # user's own stories, never to a national item about another program.
    want_stats = about_user and category in {"CFP watch", "Program", "Heisman watch"} and (h % 3 != 0)
    want_game = about_user and category in {"CFP watch", "Program"} and (h % 2 == 0)
    want_futures = about_user and category in {"CFP watch", "Heisman watch", "Coaching carousel"} and (h % 2 == 1)

    stats = _stats(dynasty) if want_stats else []
    betting = _betting(dynasty, category, want_game, want_futures)

    elements = []
    if quotes: elements.append("quotes")
    if stats: elements.append("stats")
    if betting: elements.append("betting")

    return {
        "title": title, "category": category, "accent": article.get("accent") or base.accent_for(category),
        "dek": dek, "outlet": outlet, "reporter": reporter, "timestamp": article.get("timestamp", ""),
        "sections": sections, "pull_quote": pull_quote,
        "quotes": quotes, "stats": stats, "betting": betting, "elements": elements,
    }


SYSTEM = (
    "You are a senior college football writer expanding a short item into a full "
    "article. Ground everything in the dynasty data and keep the article about its "
    "OWN subject: if it is a national story about another team, do not bend it back "
    "to the user's program or insert the user's players, stats, or betting lines. "
    "Include a realistic mix (not all) of: player quotes, coordinator/analyst/insider "
    "quotes, game/team stats, and betting lines or futures, chosen to fit the story. "
    "CRITICAL: never fabricate a quote from the user's head coach. Quote the head "
    "coach ONLY with words he actually said that appear in the provided context (his "
    "media texts or post-game press conference). If none are provided, do not quote "
    "him at all; quote other people instead. Do not use dashes as punctuation; never use emojis."
)


def _story_team(article: dict, dynasty: dict) -> str | None:
    """The team a national story is primarily about. The subject is whichever known
    team leads the most prominent field, so we scan headline first, then dek, then
    body, and within a field take the EARLIEST-occurring team (tie broken by the more
    specific, longer name). Matched against the AP poll + coaching directory; the
    user's own team is excluded."""
    names: list[str] = []
    seen: set[str] = set()
    for r in (dynasty.get("national", {}) or {}).get("ap_top25") or []:
        if isinstance(r, dict) and r.get("team"):
            names.append(r["team"]); seen.add(r["team"])
    for t in (dynasty.get("coaches") or {}):
        if t not in seen:
            names.append(t); seen.add(t)
    user = (dynasty.get("team") or {}).get("name")
    names = [n for n in names if n and n != user]
    for field in ("headline", "subheadline", "dek", "lede", "body"):
        text = str(article.get(field, "")).lower()
        if not text:
            continue
        best, best_pos = None, None
        for name in names:
            pos = text.find(name.lower())
            if pos < 0:
                continue
            if best_pos is None or pos < best_pos or (pos == best_pos and len(name) > len(best)):
                best, best_pos = name, pos
        if best:
            return best
    return None


def _team_result(team: str, dynasty: dict) -> str | None:
    """`team`'s result on this week's scoreboard, e.g. 'W 31-24 vs Texas Longhorns'."""
    for g in (dynasty.get("national", {}) or {}).get("scoreboard") or []:
        if g.get("status") != "final" or g.get("home_score") is None or g.get("away_score") is None:
            continue
        home, away = g.get("home") or {}, g.get("away") or {}
        if team not in (home.get("name"), away.get("name")):
            continue
        is_home = home.get("name") == team
        us = g["home_score"] if is_home else g["away_score"]
        them = g["away_score"] if is_home else g["home_score"]
        opp = (away if is_home else home).get("name")
        wl = "W" if us > them else ("L" if us < them else "T")
        return f"{wl} {us}-{them} {'vs' if is_home else 'at'} {opp}"
    return None


def _national_stat_rail(article: dict, dynasty: dict) -> list[dict[str, str]]:
    """A deterministic 'By the numbers' rail for a NATIONAL story, so its reader page
    carries real data instead of the empty placeholder. Tied to the team the story
    names (its rank, record, this week's result, head coach) when one is found, plus a
    couple of national anchors (the AP No. 1 and the Heisman leader with his line)."""
    nat = dynasty.get("national", {}) or {}
    rows: list[dict[str, str]] = []
    team = _story_team(article, dynasty)
    has_team_rank = False
    if team:
        ap = next((r for r in (nat.get("ap_top25") or []) if r.get("team") == team), None)
        cinfo = (dynasty.get("coaches") or {}).get(team) or {}
        rank = (ap or {}).get("rank")
        record = (ap or {}).get("record") or cinfo.get("record")
        if rank:
            rows.append({"label": f"{team} AP rank", "value": f"No. {rank}"})
            has_team_rank = True
        if record:
            rows.append({"label": f"{team} record", "value": str(record)})
        res = _team_result(team, dynasty)
        if res:
            rows.append({"label": "This week", "value": res})
        if cinfo.get("name"):
            rows.append({"label": "Head coach", "value": cinfo["name"]})
    ap_top = [r for r in (nat.get("ap_top25") or []) if r.get("team")]
    if ap_top and not has_team_rank:
        rows.append({"label": "AP No. 1", "value": f"{ap_top[0]['team']} ({ap_top[0].get('record', '')})"})
    heis = [h for h in (nat.get("heisman_frontrunners") or []) if h.get("name")]
    if heis:
        h = heis[0]
        rows.append({"label": "Heisman leader",
                     "value": h["name"] + (f", {h['stat_line']}" if h.get("stat_line") else "")})
    return rows[:5]


def build_detail(article: dict, dynasty: dict, *, year: int | None = None) -> dict[str, Any]:
    """A reader page built deterministically from an article's (full) body, with NO
    model call: the body IS the article, split into paragraphs, plus the enrichment
    the writer supplied in the same pass (a pull quote and attributed quotes) and a
    data rail. A program story gets the user's team stats + betting; a NATIONAL story
    gets a national stat rail (the team it names, plus poll/Heisman anchors) so its
    reader page carries real data instead of the empty 'more coverage' placeholder.
    Used by the newsroom and the world-reaction engine so a finished article never
    needs a second LLM 'expand'."""
    body = article.get("body") or article.get("lede") or article.get("dek") or ""
    sections = [p.strip() for p in str(body).split("\n\n") if p.strip()]
    category = article.get("category", "National")
    about_user = _is_about_user(article, dynasty)

    # Enrichment the writer produced alongside the body (no second LLM call). The
    # coach is never quoted unless the story is about his program AND the words match
    # something he actually said; other people stay fictional and pass through.
    pull = article.get("pull_quote")
    pull_quote = pull.strip() if isinstance(pull, str) and pull.strip() else None
    quotes = _strip_unreal_coach_quotes(article.get("quotes") or [], dynasty, year or 0, about_user)

    if about_user:
        stats = _stats(dynasty) if category in {"CFP watch", "Program", "Heisman watch"} else []
        want_game = category in {"CFP watch", "Program"}
        want_futures = category in {"Heisman watch", "Coaching carousel", "CFP watch"}
        betting = _betting(dynasty, category, want_game, want_futures)
    else:
        stats = _national_stat_rail(article, dynasty)
        betting = None  # the user's betting lines never belong on a national story

    return {
        "title": article.get("headline", ""), "category": category,
        "accent": article.get("accent") or base.accent_for(category),
        "dek": article.get("dek", ""), "outlet": article.get("outlet", ""),
        "reporter": article.get("reporter", ""), "timestamp": article.get("timestamp", ""),
        "sections": sections, "pull_quote": pull_quote, "quotes": quotes,
        "stats": stats, "betting": betting,
        "elements": [k for k, v in (("quotes", quotes), ("stats", stats), ("betting", betting)) if v],
        "source": "newsroom",
    }


def attach_details(articles: list[dict], dynasty: dict, *, year: int, week: int, use_llm: bool) -> list[dict]:
    """Expand each article in place, attaching a full `detail` page so the reader
    opens instantly instead of generating on click. Pre-generation happens during
    the weekly pipeline run. A single failed expansion is skipped (the reader's
    on-demand /api/article path remains the fallback)."""
    for a in articles:
        if isinstance(a, dict) and "detail" not in a:
            try:
                a["detail"] = expand(a, dynasty, year=year, week=week, use_llm=use_llm)
            except Exception:
                pass
    return articles


def _strip_user_program(detail: dict, dynasty: dict) -> dict:
    """Hard guarantee for a NATIONAL story: drop any body paragraph that mentions
    the user's program or coach, and drop the user's stats/betting. Without this a
    small model folds the user's result and storylines into an unrelated national
    story (a 'SEC carousel' piece turning into a Nebraska recap)."""
    t = dynasty.get("team", {}) or {}
    raw = [t.get("name"), t.get("school"), t.get("nickname"), (t.get("head_coach") or {}).get("name")]
    # Full phrases plus each significant word, so "Nolte" (last name) and
    # "Cornhuskers"/"Nebraska" (a word of the full name) are all caught.
    needles: set[str] = set()
    for r in raw:
        r = (r or "").strip().lower()
        if len(r) >= 4:
            needles.add(r)
        for w in r.split():
            if len(w) >= 4:
                needles.add(w)
    needles = sorted(needles)
    if needles:
        secs = [s for s in (detail.get("sections") or [])
                if not any(n in str(s).lower() for n in needles)]
        # Keep at least the lede so the article is not emptied out entirely.
        detail["sections"] = secs or (detail.get("sections") or [])[:1]
    detail["stats"] = []      # the user's "by the numbers" never belongs on a national story
    detail["betting"] = None  # nor the user's betting lines
    return detail


def expand(article: dict, dynasty: dict, *, year: int, week: int, use_llm: bool) -> dict[str, Any]:
    source = "mock"
    about_user = _is_about_user(article, dynasty)
    if use_llm and base.llm_available():
        try:
            # A national story (about other teams) gets a NON-reactive context and
            # plain facts, so the user's "RIGHT NOW" result/presser/storylines do
            # not bleed into it; a program story keeps the full reactive context.
            context = base.news_context(dynasty, year, week, reactive=about_user)
            if about_user:
                grounding = base.reactive_grounding(dynasty, year, week)
            else:
                grounding = base.grounding_facts(dynasty)
                brief = base.national_brief(dynasty, year, week)
                if brief:
                    grounding += "\n\n" + brief
            prompt = (
                "Expand this article into a full page. Article JSON:\n"
                + base.json.dumps({k: article.get(k) for k in ("headline", "category", "dek", "subheadline", "body", "lede", "outlet", "reporter", "byline")})
                + "\n\nReturn STRICT JSON with keys: sections (array of paragraph strings), "
                "pull_quote (string or null), quotes (array of {speaker, role, text}), "
                "stats (array of {label, value}), betting ({game:{matchup,spread,total,moneyline}|null, "
                "futures:[{label,value}]} or null). Include only the elements that fit this story. JSON only."
            )
            if not about_user:
                team = (dynasty.get("team") or {}).get("name", "the user's program")
                prompt += (
                    f"\n\nThis is a NATIONAL story about OTHER programs, not about {team}. Write ONLY about its "
                    f"actual subject. Do NOT mention {team}, its coach, its game, its record, its schedule, or its "
                    "recruits anywhere. Never name a real-life coach or player; if you have no fictional name, refer "
                    "to people generically (the head coach, the program)."
                )
            data = llm.generate_json(SYSTEM, prompt, cached_context=context,
                                     grounding=grounding, max_tokens=2200)
            merged = _mock(article, dynasty)
            for key in ("sections", "pull_quote", "quotes", "stats", "betting"):
                if data.get(key) is not None:
                    merged[key] = data[key]
            # Drop stat rows the model left without a real value, so the reader's
            # "By the numbers" rail never shows a "null" line.
            merged["stats"] = [
                s for s in (merged.get("stats") or [])
                if isinstance(s, dict) and s.get("label")
                and str(s.get("value") or "").strip()
                and str(s.get("value")).strip().lower() not in ("null", "none", "undefined")
            ]
            # Hard guarantee: the coach is never fabricated or quoted in a story that
            # is not about his program. Verify any coach quote against what he really
            # said (presser + texts); drop the rest. Other people stay fictional.
            merged["quotes"] = _strip_unreal_coach_quotes(merged.get("quotes"), dynasty, year, about_user)
            # And on a national story, scrub any user-program paragraphs/stats the
            # model slipped in despite the instruction (the deterministic backstop).
            if not about_user:
                merged = _strip_user_program(merged, dynasty)
            merged["elements"] = [k for k in ("quotes", "stats", "betting") if merged.get(k)]
            return base.sanitize(dict(merged, source="llm"))
        except Exception:
            pass
    return base.sanitize(dict(_mock(article, dynasty), source=source))
