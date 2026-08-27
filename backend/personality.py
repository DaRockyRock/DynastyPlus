"""Personality engine.

Every person in the dynasty universe - coaches, players, recruits, transfers,
media, committee members - carries a set of 1-100 trait sliders plus a written
biography. The sliders shape how a person talks, how they interact with the
coach, and what motivates them; the bio gives them backstory and character that
an LLM agent can lean on to behave consistently.

Two generation modes:
  * generated - fictional people (your roster, recruits, staff, the carousel).
    Sliders are randomized; a recruit gets one the moment they hit your board,
    and every roster player gets one automatically. Seeded by name so the same
    person is stable across reads, but distinct from everyone else.
  * fixed - real people (the CFP committee, the media). Their sliders and bios
    are authored once from research and stay the same every time (still fully
    editable in the Customize flow).

This module is a leaf: it depends only on the standard library (plus a lazy,
optional LLM call used only on explicit generation, never on read).
"""
from __future__ import annotations

import random
from typing import Any

# The trait set. Each is a 1-100 slider with a labelled low and high pole so the
# editor and the LLM both understand what the number means.
PERSONALITY_TRAITS: list[dict[str, str]] = [
    {"key": "confidence", "label": "Confidence", "low": "Humble", "high": "Brash"},
    {"key": "competitiveness", "label": "Competitiveness", "low": "Easygoing", "high": "Relentless"},
    {"key": "loyalty", "label": "Loyalty", "low": "Mercenary", "high": "Ride or Die"},
    {"key": "composure", "label": "Composure", "low": "Volatile", "high": "Unflappable"},
    {"key": "charisma", "label": "Charisma", "low": "Reserved", "high": "Magnetic"},
    {"key": "ambition", "label": "Ambition", "low": "Content", "high": "Driven"},
    {"key": "ego", "label": "Ego", "low": "Team-First", "high": "Spotlight"},
]
TRAIT_KEYS = [t["key"] for t in PERSONALITY_TRAITS]


def default_traits() -> dict[str, int]:
    return {k: 50 for k in TRAIT_KEYS}


def _seed_int(s: str | None) -> int | None:
    if not s:
        return None
    return sum((i + 1) * ord(c) for i, c in enumerate(s))


def random_traits(seed: str | None = None) -> dict[str, int]:
    """Random 1-100 sliders. With a seed (a person's name) the draw is stable,
    so the same person reads the same every time but differs from everyone else."""
    rng = random.Random(_seed_int(seed)) if seed else random.Random()
    return {k: rng.randint(8, 96) for k in TRAIT_KEYS}


# --- biography generation -------------------------------------------------
# Verb-phrase banks keyed by trait; the subject is the person's first name.
_BANK: dict[str, dict[str, list[str]]] = {
    "confidence": {
        "high": ["carries himself with real swagger", "never lacks for belief in his own game",
                 "talks like someone who fully expects to win"],
        "low": ["lets his play do the talking", "carries a quiet, unbothered kind of confidence"],
    },
    "competitiveness": {
        "high": ["treats every rep like the fourth quarter of a rivalry", "hates losing more than he enjoys winning",
                 "competes at everything, on the field and off it"],
        "low": ["keeps an even keel whether he is up or down", "rarely lets the scoreboard rattle his routine"],
    },
    "loyalty": {
        "high": ["values the people who believed in him first", "is the type to run through a wall for his guys"],
        "low": ["keeps his options open and bets on himself", "is quick to chase the better situation"],
    },
    "composure": {
        "high": ["never speeds up when the lights get bright", "is almost impossible to rattle"],
        "low": ["wears his emotions on his sleeve", "rides the highs and the lows hard"],
    },
    "charisma": {
        "high": ["lights up a locker room", "draws people in without seeming to try"],
        "low": ["keeps to a tight circle", "is quiet and lets others do the talking"],
    },
    "ambition": {
        "high": ["already has his eyes on the next level", "is restless for whatever comes next"],
        "low": ["is happy to let the work speak over time", "is in no rush, trusting the long game"],
    },
    "ego": {
        "high": ["believes he should be the centerpiece", "wants the ball and the moment"],
        "low": ["would rather win than be noticed", "puts the team in front of the headlines"],
    },
}

_MOTIV = {
    "Brand Exposure": "What moves {first} most is the spotlight and the brand he can build off the field.",
    "Playing Time": "More than anything, {first} wants the ball and a clear path onto the field.",
    "NFL Readiness": "Every decision runs through one question for {first}: does it get him to the NFL?",
    "Development": "{first} is chasing the coaching that turns talent into a career, not the flashiest pitch.",
    "Proximity to Home": "Home matters here; {first} wants the people who raised him close enough to watch.",
    "Championship Culture": "{first} came to win, and measures everything by whether it leads to a ring.",
    "Coaching Stability": "{first} trusts relationships and stability over hype, and remembers who stays.",
}

_YEAR_WORD = {"FR": "freshman", "SO": "sophomore", "JR": "junior", "SR": "senior", "GR": "grad"}


def _context_clause(record: dict, noun: str) -> str | None:
    """A clause that follows the person's name, e.g. 'is a four-star QB out of Texas'."""
    pos = record.get("position")
    if noun == "recruit":
        stars = record.get("stars")
        base = f"is a {stars}-star {pos}" if stars and pos else (f"is a {pos} prospect" if pos else "is a prospect")
        if record.get("hometown"):
            base += f" out of {record['hometown']}"
        return base
    if noun == "player":
        yr = _YEAR_WORD.get(record.get("year") or "", "")
        return f"is a {yr} {pos}".replace("  ", " ").strip() if pos else "is a key contributor"
    if noun == "transfer":
        origin = record.get("from")
        base = f"is a {pos} in the transfer portal" if pos else "is working the transfer portal"
        if origin:
            base += f", in from {origin}"
        return base
    if noun in ("coach", "head coach"):
        return f"is the {record['role']}" if record.get("role") else "is a coach on staff"
    if noun == "coaching candidate":
        return f"is {record['current']}" if record.get("current") else "is a name on the carousel"
    if noun == "committee member":
        return f"serves as {record['role']}" if record.get("role") else "sits on the selection committee"
    if noun in ("reporter", "recruiting analyst", "award voter", "media personality"):
        outlet = record.get("outlet")
        beat = record.get("beat")
        if outlet and beat:
            return f"covers the {beat} beat for {outlet}"
        if outlet:
            return f"writes for {outlet}" if noun != "media personality" else f"is a voice for {outlet}"
        return "is a member of the media"
    if noun == "contact":
        return f"is your {record['role']}" if record.get("role") else None
    return None


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def build_bio(record: dict, *, noun: str, traits: dict[str, int]) -> str:
    """A deterministic, characterful 3-sentence bio assembled from the sliders
    and whatever context the record carries. Free and instant, so it is safe to
    run on every read for fictional people."""
    raw = (record.get("name") or record.get("coach") or "").strip()
    has_name = bool(raw)
    # Display name for the opening line; a noun phrase ("This recruit") stands in
    # until the user fills the name, so a freshly-added person still reads cleanly.
    display = raw if has_name else _cap(f"this {noun}")
    subject = raw.split()[0] if has_name else _cap(f"the {noun}")
    rng = random.Random(_seed_int((raw or noun) + noun))

    ranked = sorted(TRAIT_KEYS, key=lambda k: traits.get(k, 50))
    lo_key, mid_hi_key, hi_key = ranked[0], ranked[-2], ranked[-1]

    sentences: list[str] = []
    ctx = _context_clause(record, noun)
    sentences.append(f"{display} {ctx}." if ctx else f"{display} is part of the program.")

    hi = rng.choice(_BANK[hi_key]["high"])
    if traits.get(mid_hi_key, 0) >= 62 and mid_hi_key != hi_key:
        mid = rng.choice(_BANK[mid_hi_key]["high"])
        sentences.append(f"{subject} {hi} and {mid}.")
    else:
        sentences.append(f"{subject} {hi}.")

    db = record.get("dealbreaker")
    if db in _MOTIV:
        sentences.append(_MOTIV[db].format(first=subject))
    elif traits.get("ambition", 50) >= 72:
        sentences.append(f"{subject} is restless for the next level and is not shy about chasing it.")
    elif traits.get("loyalty", 50) >= 72:
        sentences.append(f"{subject} is fiercely loyal to the people who got him here.")
    elif traits.get("ego", 50) <= 32:
        sentences.append(f"{subject} would rather win quietly than chase the headlines.")
    else:
        sentences.append(f"{subject} is steady, and lets the work pile up over time.")

    if traits.get(lo_key, 50) <= 26:
        sentences.append(_cap(f"{subject} {rng.choice(_BANK[lo_key]['low'])}."))

    return " ".join(sentences)


def build_bio_llm(record: dict, *, noun: str, traits: dict[str, int]) -> str:
    """Optional richer bio via the LLM. Only called on explicit generation
    (never on read). Falls back to the templated bio on any failure."""
    try:
        from . import llm
        if not llm.available():
            return build_bio(record, noun=noun, traits=traits)
        slider_text = ", ".join(
            f"{t['label']} {traits.get(t['key'], 50)}/100 ({t['low']}<->{t['high']})"
            for t in PERSONALITY_TRAITS
        )
        name = record.get("name") or record.get("coach") or "the person"
        facts = {k: v for k, v in record.items() if k not in ("bio", "traits") and v not in (None, "")}
        system = (
            "You write short, vivid backstory bios for characters in a college football "
            "dynasty simulation. 2-4 sentences, grounded in the given facts and personality "
            "sliders. Give them real character and motivation. Never use dashes as punctuation; use commas, never dashes. "
            "Return only the bio text."
        )
        prompt = (
            f"Person: {name} ({noun}).\nKnown facts: {facts}.\nPersonality: {slider_text}.\n"
            "Write the bio."
        )
        text = llm.generate_text(system, prompt, max_tokens=240)
        text = (text or "").strip()
        return text or build_bio(record, noun=noun, traits=traits)
    except Exception:
        return build_bio(record, noun=noun, traits=traits)


def enrich(record: dict, *, noun: str, mode: str, use_llm: bool = False) -> dict:
    """Ensure a person record has a full `traits` dict and a `bio`.

    generated: randomize missing sliders (seeded by name) and write a bio if none.
    fixed: keep authored sliders, filling any gap with a neutral 50; keep the bio.
    """
    rec = dict(record)
    existing = rec.get("traits") if isinstance(rec.get("traits"), dict) else {}

    if mode == "generated" and (not existing or set(existing) != set(TRAIT_KEYS)):
        base = random_traits(rec.get("name") or rec.get("coach"))
        base.update({k: v for k, v in existing.items() if k in TRAIT_KEYS})
        existing = base

    rec["traits"] = {k: int(existing.get(k, 50)) for k in TRAIT_KEYS}

    if not rec.get("bio"):
        builder = build_bio_llm if use_llm else build_bio
        rec["bio"] = builder(rec, noun=noun, traits=rec["traits"])
    return rec


def generate_person(record: dict, *, noun: str, use_llm: bool = False) -> dict[str, Any]:
    """Fresh persona for a new person (random sliders + a bio). Used when a
    recruit is added to the board or a new person is created in the editor."""
    traits = random_traits(record.get("name") or record.get("coach") or None)
    builder = build_bio_llm if use_llm else build_bio
    bio = builder({**record, "traits": traits}, noun=noun, traits=traits)
    return {"traits": traits, "bio": bio}
