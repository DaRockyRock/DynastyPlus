"""Per-beat realization: one focused LLM call per article (or a template).

Replaces the two big batched national/program prompts with one tight brief per
story. The wins: a small model writes far better prose from 5 facts than from a
whole-slate dump; a beat that fails validation is regenerated on its own (not
dropped); and the slate scales to the model (top beats get the model, the rest are
templated within the profile's budget). Beats run concurrently; the static system
prompt is a shared, cacheable prefix.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .. import dynasty_paths, llm
from . import canon as canon_mod
from . import claims as claims_mod
from . import ledger, personas, profile, review, template, validate
from .briefs import build_rundown
from .state import WorldState, extract

# Static system prompt -> shared KV-cache prefix across every beat this week.
SYSTEM_BEAT = (
    "You are a college football reporter writing ONE short article for a fictional "
    "media universe. Use ONLY the facts given. NEVER invent players, statistics, "
    "scores, or coaches, and never name a real-life person. Never use dashes as "
    "punctuation; use commas or periods. Write tight, specific, believable copy in "
    "the outlet's voice, every sentence carrying a fact. Output ONE JSON object."
)

_CATEGORY = {
    "title_race": "CFP watch", "marquee_preview": "Marquee games",
    "next_game_preview": "Matchup preview", "upset": "Upset",
    "ranked_clash": "Marquee games", "blowout": "Around the nation",
    "user_result": "Recap", "poll_jump": "Poll watch", "poll_fall": "Poll watch",
    "new_number_one": "Poll watch", "commit": "Recruiting",
    "recruiting_battle": "Recruiting", "hot_seat_watch": "Coaching carousel",
    "player_spotlight": "Feature", "position_feature": "Feature", "season_retrospective": "Analysis",
}
# Which day of the news week a story type surfaces on (diegetic timeline).
_DAY_SLOT = {
    "title_race": "Mon", "new_number_one": "Sun", "poll_jump": "Sun", "poll_fall": "Sun",
    "user_result": "Sat", "upset": "Sat", "ranked_clash": "Sat", "blowout": "Sat",
    "next_game_preview": "Fri", "marquee_preview": "Fri",
    "recruiting_battle": "Wed", "commit": "Wed", "hot_seat_watch": "Tue",
    "player_spotlight": "Wed", "position_feature": "Thu", "season_retrospective": "Thu",
}
_SLOT_TS = {"Mon": "today", "Tue": "today", "Wed": "2d ago", "Thu": "3d ago",
            "Fri": "4d ago", "Sat": "1d ago", "Sun": "today"}


def _persona(scope: str, seed: str, *, registry=None, card=None) -> dict[str, Any]:
    """Resolve the byline as a Persona Card (consistent voice + committed takes),
    falling back to a generic outlet voice only if the cast is empty."""
    c = card or personas.byline_for(scope, seed, registry)
    if c:
        return {"outlet": c.outlet, "voice": c.voice, "reliability": c.reliability,
                "reporter": c.name, "lean": c.lean, "archetype": c.archetype,
                "card_id": c.id, "takes": c.takes}
    return {"outlet": "National Wire", "voice": "straight news", "reliability": 80,
            "reporter": "Staff", "lean": 0.0, "archetype": "a measured voice", "takes": {}}


def _cast(subjects: list[str], canon: canon_mod.Canon) -> list[str]:
    """Canonical 'you may name' lines for the entities in this story."""
    out: list[str] = []
    for s in subjects:
        ent = canon.find_person(s)
        if ent:
            a = ent.attrs
            extra = ", ".join(str(x) for x in (a.get("position"),
                              (f"{a.get('stars')}-star" if a.get("stars") else None)) if x)
            out.append(f"{ent.name} ({ent.kind}{', ' + extra if extra else ''})")
        elif s in canon.teams:
            cn = canon.teams[s]
            out.append(f"{s} (coach: {_coach_name(canon, s)})" if _coach_name(canon, s) else s)
    return out


def _coach_name(canon: canon_mod.Canon, team: str) -> str | None:
    for e in canon.people.values():
        if e.kind == "coach" and e.attrs.get("team") == team:
            return e.name
    return None


def build_brief(cand: dict, *, scope: str, state: WorldState, canon: canon_mod.Canon,
                rundown: dict, year: int, week: int, max_facts: int,
                personas_reg=None, card=None) -> dict[str, Any]:
    ctype = cand.get("type")
    # "note" is a meta-instruction for the writer (e.g. "NOT PLAYED YET"), handled by
    # `constraints`, so it never becomes a body sentence.
    facts = [str(v) for k, v in (cand.get("facts") or {}).items() if v and k != "note"][:max_facts]
    slot = _DAY_SLOT.get(ctype, "Thu")
    preview = cand.get("phase") == "preview"
    persona = _persona(scope, f"{cand.get('id')}", registry=personas_reg, card=card)
    constraints = []
    if preview or state.season_open:
        constraints.append("This game/season has NOT been played yet: write a forward-looking "
                            "preview, do NOT state a score, a winner, or anything that happened.")
    if state.season_open:
        constraints.append("No games have been played, so cite NO current-season statistics.")
    if week <= 3:
        constraints.append(f"It is WEEK {week}, the very START of the season (early September). "
                            "Never describe a game as late-season, midseason, a stretch-run matchup, "
                            "or a must-win; the season is just beginning.")
    # A standing take this reporter already holds on a subject keeps them consistent
    # week to week (they do not flip casually).
    subjects = cand.get("subjects") or []
    standing = next((persona["takes"][s] for s in subjects if s in (persona.get("takes") or {})), "")
    return {
        "persona": persona,
        "category": _CATEGORY.get(ctype, "College football"),
        "candidate_type": ctype, "scope": scope, "subjects": subjects,
        "headline_hint": facts[0] if facts else None,
        "lines": facts,
        "stakes": [s["text"] for s in (rundown.get("stakes") or [])][:2] if scope == "program" else [],
        "mood": rundown.get("mood") if scope == "program" else "",
        "cast": _cast(subjects, canon),
        # Prefer the arc registry's cross-week note (it knows the saga's length);
        # fall back to the ledger's simpler streak note.
        "continuity": cand.get("arc_note") or ledger.continuity_note(year, week, ctype, subjects),
        "review_angle": cand.get("review_angle"),
        "standing_take": standing,
        "constraints": " ".join(constraints),
        "day_slot": slot, "timestamp": _SLOT_TS.get(slot, "today"),
    }


def _prompt(brief: dict, *, terse: bool) -> str:
    p = brief["persona"]
    blocks = [f"YOU ARE {p['reporter']} of {p['outlet']}, {p.get('archetype', 'a measured voice')}. "
              f"VOICE: {p['voice']} Write in this voice and stay in character."]
    if brief.get("standing_take"):
        blocks.append(f"YOUR STANDING TAKE (stay consistent, do not flip): {brief['standing_take']}")
    if brief.get("review_angle"):
        blocks.append(f"ANGLE (the desk's preferred framing): {brief['review_angle']}")
    if brief.get("mood"):
        blocks.append(f"MOOD this week: {brief['mood']} (let the tone reflect it).")
    blocks.append("FACTS (use ONLY these, add nothing beyond them):\n"
                  + "\n".join(f"  - {f}" for f in brief["lines"]))
    if brief.get("stakes"):
        blocks.append("STAKES (what it means):\n" + "\n".join(f"  - {s}" for s in brief["stakes"]))
    if brief.get("cast"):
        blocks.append("People/teams you may name (and nobody else as a coach):\n"
                      + "\n".join(f"  - {c}" for c in brief["cast"]))
    if brief.get("continuity"):
        blocks.append("CONTINUITY: " + brief["continuity"])
    if brief.get("constraints"):
        blocks.append("CONSTRAINTS: " + brief["constraints"])
    paras = "2" if terse else "3"
    blocks.append(
        f"TASK: Write a {brief['category']} article: a punchy headline (under 12 words), a "
        f"one-line dek, and a {paras}-paragraph body in the reporter's voice. Return ONLY JSON: "
        '{"headline": "...", "dek": "...", "body": "...", "pull_quote": "..." or null, '
        '"quotes": [{"speaker": "...", "role": "...", "text": "..."}]}')
    return "\n\n".join(blocks)


def _merge(brief: dict, gen: dict) -> dict[str, Any]:
    p = brief["persona"]
    return {
        "outlet": p["outlet"], "reporter": p["reporter"], "reliability": p["reliability"],
        "category": brief["category"], "headline": (gen.get("headline") or "").strip(),
        "dek": (gen.get("dek") or "").strip(), "body": gen.get("body") or "",
        "pull_quote": gen.get("pull_quote"), "quotes": gen.get("quotes") or [],
        "timestamp": brief["timestamp"], "day_slot": brief["day_slot"], "source": "llm",
    }


def _realize_one(brief: dict, *, scope: str, canon: canon_mod.Canon, state: WorldState,
                 prof: profile.ModelProfile, use_llm: bool, cove: bool = False) -> dict[str, Any]:
    """One beat: LLM if budgeted and valid (one regenerate on a hard miss), else the
    template. `cove` adds a model self-check on the lead (mid+). Always returns a
    usable article."""
    if not use_llm:
        return template.render(brief)
    terse = prof.tier == "nano"
    for attempt in range(2):
        try:
            gen = llm.generate_json(SYSTEM_BEAT, _prompt(brief, terse=terse),
                                    cached_context=None, max_tokens=520)
        except Exception:
            break
        art = _merge(brief, gen)
        if not art["headline"]:
            continue
        if not validate.passes(art, scope=scope, canon=canon, state=state, label="beat"):
            # a hard miss: tell the next attempt what to avoid, then retry once
            brief = dict(brief, constraints=(brief.get("constraints", "") +
                         " A prior draft contradicted the facts; use ONLY the facts above, "
                         "match every position and star rating exactly, and do not editorialize "
                         "about anyone's job security.").strip())
            continue
        if cove:                       # CoVe-lite: a focused fact self-check on the lead
            bad = review.cove_unsupported(art, brief.get("lines") or [], enabled=True)
            if bad and attempt == 0:
                brief = dict(brief, constraints=(brief.get("constraints", "") +
                             " Remove or correct these unsupported claims: " + ", ".join(bad)
                             + ". Use ONLY the facts above.").strip())
                continue
        return art
    return template.render(brief)   # fell through -> the canon-faithful floor


def realize_coverage(dynasty: dict, year: int, week: int, *,
                     use_llm: bool = True) -> dict[str, Any]:
    """The week's national + program articles and insider reports, realized per beat.
    Deterministic selection (the rundown); only the prose varies with the model."""
    prof = profile.current()
    use_llm = use_llm and prof.tier != "none" and llm.available()
    rundown = build_rundown(dynasty, year, week)
    state = extract(dynasty, year, week)
    canon = canon_mod.build(dynasty)
    preg = personas.build()        # the cast, built once and threaded through every brief

    # hot_seat_watch candidates become claims (the rumor lifecycle), not articles.
    nat_all = [c for c in rundown.get("national") or [] if c.get("type") != "hot_seat_watch"]
    prog_all = rundown.get("program") or []
    nat, prog = nat_all[:4], prog_all[:4]
    # Editorial-review pass (mid+ tiers only): a capable model may reorder, sharpen the
    # angle, or promote one near-miss from the bench. Whitelist-applied, so it can never
    # corrupt the deterministic floor.
    if prof.review_pass:
        nat, prog = review.review_slate(nat, prog, nat_all[4:] + prog_all[4:], enabled=True)
        nat, prog = nat[:5], prog[:5]

    # Build briefs, then realize the top `max_llm_beats` with the model and template
    # the remainder. Jobs are INTERLEAVED program/national so a small budget covers
    # both scopes' leads; ordering them program-first starved the national slate into
    # templates on a nano model (the bland title-race/marquee articles).
    jobs: list[tuple[str, dict]] = []
    for i in range(max(len(prog), len(nat))):
        if i < len(prog):
            jobs.append(("program", prog[i]))
        if i < len(nat):
            jobs.append(("national", nat[i]))
    briefs = [(scope, build_brief(c, scope=scope, state=state, canon=canon, rundown=rundown,
                                  year=year, week=week, max_facts=prof.max_brief_facts,
                                  personas_reg=preg))
              for scope, c in jobs]
    llm_n = prof.max_llm_beats if use_llm else 0

    def run(i_scope_brief):
        i, (scope, brief) = i_scope_brief
        return _realize_one(brief, scope=scope, canon=canon, state=state, prof=prof,
                            use_llm=use_llm and i < llm_n, cove=prof.review_pass and i == 0)

    if use_llm and prof.workers > 1:
        with ThreadPoolExecutor(max_workers=prof.workers) as ex:
            arts = list(ex.map(run, enumerate(briefs)))
    else:
        arts = [run(x) for x in enumerate(briefs)]

    national = [a for (scope, _), a in zip(briefs, arts) if scope == "national"]
    program = [a for (scope, _), a in zip(briefs, arts) if scope == "program"]

    # Debate take: the local beat's most skeptical voice (not the lead's byline) pushes
    # back on the lead program story, so the cast visibly disagrees against the
    # prevailing optimism. One extra beat, only when a distinct skeptic exists.
    if use_llm and prog:
        lead_card = personas.byline_for("program", prog[0].get("id", ""), preg)
        lead_id = lead_card.id if lead_card else None
        skeptics = sorted((c for c in preg.values()
                           if c.scope == "local" and c.id != lead_id and c.lean < 0.2),
                          key=lambda c: c.lean)
        if skeptics:
            skeptic = skeptics[0]
            db = build_brief(prog[0], scope="program", state=state, canon=canon, rundown=rundown,
                             year=year, week=week, max_facts=prof.max_brief_facts,
                             personas_reg=preg, card=skeptic)
            db["category"] = "Counterpoint"
            db["constraints"] = (db.get("constraints", "") + " This is an OPINION column: take the "
                                 "skeptical, contrarian side and push back on the prevailing optimism, "
                                 "while staying grounded in the facts above.").strip()
            debate = _realize_one(db, scope="program", canon=canon, state=state, prof=prof, use_llm=True)
            debate["debate"] = True
            program.append(debate)
            subj = (prog[0].get("subjects") or [None])[0]
            if subj:
                personas.record_take(skeptic.id, subj, "skeptical, wants to see it proven on the field")

    # Insider reports come from the rumor lifecycle (claims): live carousel rumors
    # rendered hedged + attributed, plus resolution beats when a prior claim settles
    # (which also moves the reporter's credibility). Never at season open.
    insiders: list[dict[str, Any]] = []
    cl = claims_mod.for_week(dynasty, year, week, state.season_open, registry=preg)
    for c in cl["resolutions"][:2]:
        insiders.append(c)
    for c in cl["live"][:2]:
        insiders.append(claims_mod.render_insider(c))

    source = "llm" if (use_llm and any(a.get("source") == "llm" for a in national + program)) else "template"
    beats = [{**a, "subjects": b[1].get("subjects"), "type": b[1].get("candidate_type")}
             for b, a in zip(briefs, arts)]
    ledger.record(year, week, beats)
    # Per-week telemetry: how much of the slate the model wrote vs the template floor,
    # for the dev view and the "your model is struggling" surface.
    arts_all = national + program
    tele = {"week": week, "tier": prof.tier, "model": prof.model,
            "beats": len(arts_all), "llm": sum(1 for a in arts_all if a.get("source") == "llm"),
            "template": sum(1 for a in arts_all if a.get("source") == "template"),
            "insiders": len(insiders), "review_pass": prof.review_pass}
    try:
        (dynasty_paths.sub("editorial") / f"{year}_wk{week:02d}_telemetry.json").write_text(
            json.dumps(tele, indent=1), encoding="utf-8")
    except OSError:
        pass
    return {"national": national, "program": program, "insider_reports": insiders, "source": source}
