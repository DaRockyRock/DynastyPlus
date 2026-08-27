"""Persona Cards: the persistent voices of the media universe.

The difference between "generated content" and "a media world" is that the same
reporters show up week after week with the same voice and the same opinions. A
card carries a voice description (the reporter's bio is the best anchor a small
model can get), a program-lean used to pair opposing voices for debate, a
credibility that moves as their rumors resolve (step 5), and committed takes that
keep them consistent ("you have argued all season the rebuild is real, do not flip
casually"). Identity/voice is rebuilt from the save each tick; the evolving state
(credibility, takes, relationship) is persisted.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from typing import Any

from .. import customization, dynasty_paths

_lock = threading.Lock()


@dataclass
class PersonaCard:
    id: str
    name: str
    outlet: str | None
    scope: str                       # national | local
    voice: str                       # the style anchor (the reporter's bio, ideally)
    reliability: int
    lean: float                      # -1 hard skeptic ... +1 program optimist
    credibility: int = 0             # evolves with rumor outcomes (step 5)
    relationship: int = 0            # -100..100 toward the user program (step 5)
    takes: dict[str, str] = field(default_factory=dict)   # subject -> stance held

    @property
    def archetype(self) -> str:
        if self.lean >= 0.4:
            return "an optimist who buys the upside"
        if self.lean <= -0.4:
            return "a hard-nosed skeptic who needs to be shown"
        return "a measured, just-the-facts voice"


def _seed_lean(name: str) -> float:
    """A stable program-lean per reporter so the cast spans optimists to skeptics
    (and debate has real opposing voices), seeded by name so it never drifts."""
    h = int(hashlib.sha1(("lean:" + name).encode()).hexdigest(), 16) % 1000
    return round((h / 999.0) * 2.0 - 1.0, 2)


def _voice_for(rec: dict) -> str:
    bio = (rec.get("bio") or "").strip()
    if bio:
        return bio
    return (rec.get("voice") or "straight, sourced reporting").strip()


# --- persisted evolving state ----------------------------------------------
def _path():
    return dynasty_paths.sub("personas") / "cards.json"


def _read_state() -> dict[str, Any]:
    p = _path()
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(state: dict[str, Any]) -> None:
    try:
        _path().write_text(json.dumps(state, indent=1), encoding="utf-8")
    except OSError:
        pass


# --- build ------------------------------------------------------------------
def _slug(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum() or c == " ").replace(" ", "-")


def build() -> dict[str, PersonaCard]:
    """The full cast, merging identity (from customization) with persisted state."""
    state = _read_state()
    org_voice = {o["name"]: o.get("voice") for o in customization.section("media_orgs_national") or []}
    org_voice.update({o["name"]: o.get("voice") for o in customization.section("media_orgs_local") or []})
    local_orgs = {o["name"] for o in customization.section("media_orgs_local") or []}

    cards: dict[str, PersonaCard] = {}
    for r in customization.section("reporters") or []:
        name = r.get("name")
        if not name:
            continue
        cid = "persona:" + _slug(name)
        scope = r.get("scope") or ("local" if r.get("outlet") in local_orgs else "national")
        voice = _voice_for(r) if r.get("bio") else (org_voice.get(r.get("outlet")) or _voice_for(r))
        rel = int(r.get("reliability") or 80)
        st = state.get(cid) or {}
        cards[cid] = PersonaCard(
            id=cid, name=name, outlet=r.get("outlet"), scope=scope, voice=voice,
            reliability=rel, lean=_seed_lean(name),
            credibility=int(st.get("credibility", rel)),
            relationship=int(st.get("relationship", 0)),
            takes=dict(st.get("takes") or {}))
    return cards


# --- selection --------------------------------------------------------------
def _pick(cards: list[PersonaCard], seed: str) -> PersonaCard | None:
    if not cards:
        return None
    return cards[int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(cards)]


def byline_for(scope: str, seed: str, registry: dict[str, PersonaCard] | None = None) -> PersonaCard | None:
    """A stable byline for a story: a scope-appropriate reporter chosen by seed, so
    the same story always carries the same name across re-scans."""
    reg = registry or build()
    want = "local" if scope == "program" else "national"
    pool = [c for c in reg.values() if c.scope == want] or list(reg.values())
    return _pick(pool, "byline:" + seed)


def opposing_pair(scope: str, seed: str,
                  registry: dict[str, PersonaCard] | None = None) -> tuple[PersonaCard, PersonaCard] | None:
    """The most optimistic and most skeptical scope-appropriate voices, for a debate.
    Returns None when there are not two distinct leaning voices."""
    reg = registry or build()
    want = "local" if scope == "program" else "national"
    pool = sorted((c for c in reg.values() if c.scope == want), key=lambda c: c.lean)
    if len(pool) < 2:
        pool = sorted(reg.values(), key=lambda c: c.lean)
    if len(pool) < 2 or pool[-1].lean - pool[0].lean < 0.3:
        return None
    return pool[-1], pool[0]          # (optimist, skeptic)


# --- evolving state writes (used by debate now, rumors in step 5) -----------
def record_take(card_id: str, subject: str, stance: str) -> None:
    with _lock:
        state = _read_state()
        row = state.setdefault(card_id, {})
        row.setdefault("takes", {})[subject] = stance
        _write_state(state)


def adjust_credibility(card_id: str, delta: int, base: int = 75) -> None:
    """Move a persona's credibility. `base` seeds the FIRST adjustment from the card's
    built credibility (its reliability), so a reporter does not snap to a default 75
    the first time one of their claims resolves."""
    with _lock:
        state = _read_state()
        row = state.setdefault(card_id, {})
        cur = int(row.get("credibility", base))
        row["credibility"] = max(0, min(100, cur + delta))
        _write_state(state)
