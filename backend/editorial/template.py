"""Deterministic StoryBrief -> article renderer.

The floor of the tier ladder: with no model (or as the per-beat validation
fallback) this turns a brief's pre-decided facts into a correct, readable article.
It is plainer than model prose but never wrong, because every sentence is a fact
the editorial engine already verified. Same briefs the LLM path uses, so the two
never disagree about what a story is.
"""
from __future__ import annotations

import re
from typing import Any

# Headline templates per candidate type. {0}, {1}... are the brief's ordered facts;
# a missing fact collapses gracefully to the first available line.
_HEADLINES = {
    "title_race":        "{0}",
    "marquee_preview":   "{0}",
    "next_game_preview": "{0}",
    "upset":             "{0}",
    "ranked_clash":      "{0}",
    "blowout":           "{0}",
    "user_result":       "{0}",
    "poll_jump":         "{0}",
    "poll_fall":         "{0}",
    "new_number_one":    "{0}",
    "commit":            "{0}",
    "recruiting_battle": "{0}",
    "hot_seat_watch":    "{0}",
}


def _sentencize(fact: str) -> str:
    f = fact.strip().rstrip(".")
    if not f:
        return ""
    return f[0].upper() + f[1:] + "."


def render(brief: dict[str, Any]) -> dict[str, Any]:
    """Build a complete article dict from a brief. Body is 2-3 short paragraphs
    assembled from the facts, the stakes, and the continuity note."""
    facts: list[str] = [f for f in brief.get("lines") or [] if f]
    persona = brief.get("persona") or {}
    cat = brief.get("category") or "College football"

    headline = (brief.get("headline_hint") or (facts[0] if facts else f"{cat} update")).strip()
    headline = re.sub(r"\s*\([^)]*\)", "", headline).strip()  # drop parentheticals for a cleaner headline
    dek = _sentencize(facts[1]) if len(facts) > 1 else ""

    # Paragraph 1: the lead facts. Paragraph 2: remaining facts + stakes. Closer:
    # the continuity note, when there is one.
    lead = " ".join(_sentencize(f) for f in facts[:2])
    rest = [_sentencize(f) for f in facts[2:]]
    rest += [_sentencize(s) for s in (brief.get("stakes") or [])[:2]]
    paras = [p for p in (lead, " ".join(rest)) if p.strip()]
    note = brief.get("continuity") or ""
    if note:
        paras.append(_sentencize(note))
    body = "\n\n".join(paras) or _sentencize(headline)

    return {
        "outlet": persona.get("outlet"), "reporter": persona.get("reporter"),
        "reliability": persona.get("reliability", 80),
        "category": cat, "headline": headline, "dek": dek, "body": body,
        "pull_quote": None, "quotes": [], "timestamp": brief.get("timestamp", "today"),
        "day_slot": brief.get("day_slot"), "source": "template",
    }


def render_insider(brief: dict[str, Any]) -> dict[str, Any]:
    """An insider/carousel report from a hot_seat_watch brief: same facts, framed as
    an attributed, hedged rumor with a credibility score."""
    facts = [f for f in brief.get("lines") or [] if f]
    persona = brief.get("persona") or {}
    who = facts[0] if facts else "a coaching situation"
    return {
        "outlet": persona.get("outlet"), "reporter": persona.get("reporter"),
        "reliability": persona.get("reliability", 70),
        "category": "Coaching carousel",
        "headline": f"Sources: pressure building around {who}",
        "dek": "An insider read on a heating-up situation.",
        "body": ("People around the program describe rising heat. " + " ".join(
            _sentencize(f) for f in facts[:3]) +
            " Nothing is decided, but the temperature is worth watching."),
        "claim": f"{who} faces a decisive stretch.",
        "confidence": int(persona.get("reliability", 70)),
        "credibility": int(persona.get("reliability", 70)),
        "status": "developing",
        "timestamp": brief.get("timestamp", "today"),
        "day_slot": brief.get("day_slot"), "source": "template",
    }
