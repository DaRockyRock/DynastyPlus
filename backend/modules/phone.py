"""Phone screen.

In-app messaging UI. The coach can text anyone in the dynasty universe, not just
a curated roster: recruits, players, his own staff, opposing/hot-seat coaches,
media, committee members, candidates, analysts and voters. Any name hovered in
the app resolves through `directory` to a textable contact (see directory.py).

Each contact carries a personality profile (sliders + bio) and a `profile`
({kind, section, record}) the reply engine uses to build a relationship and role
aware "knowledge brief": a far-along in-state recruit who has texted before knows
the staff and talks warm; a cold out-of-state recruit barely knows the program; a
coach knows recruiting/results/schedule; a reporter knows the pieces they have
written. Insiders (your own staff/players/AD) see the full dynasty context; every
outsider gets only public facts plus what the coach has told them in the thread.

Replies read like real texting: usually one message, sometimes more, and they
remember the conversation so far. The LLM generates them in character (with a
mock fallback so the UI works offline).

Some contacts carry an `entity` link into the NIL/budget engine (budget.py) so
the coach can make NIL offers and spend recruiting hours from inside the chat.

`generate(...)` returns the contact roster (curated + anyone already texted) and
the category list for the tabs. `reply(...)` produces a single in-character
response (and applies any action).
"""
from __future__ import annotations

import random
import re
from typing import Any

from .. import budget, customization, directory, inbox, llm, narrative, personality
from .. import messages as msg_store
from . import base

MODULE = "phone"

# Tab order for the on-screen category filter.
CATEGORIES = customization.CONTACT_CATEGORIES

# Profile kinds that are "in the building" and see the full dynasty context.
# Everyone else gets a small public-facing context (see _scoped_context).
_INSIDER_KINDS = {"staff", "ad", "player"}


def _board_recruits(dynasty: dict | None, year: int | None = None) -> dict[str, dict]:
    """The user's recruiting board keyed by name, with their board rank. When a
    simulated season is active this is the live national-class slice (from the
    dynasty object); otherwise it is the customization board.

    When `year` is supplied, the full national class is appended as a fallback so
    any prospect on the national board (not just the coach's targets/commits) gets
    stars, position, and rank in the phone."""
    rec = (dynasty or {}).get("recruiting") or {}
    rows = (rec.get("targets") or []) + (rec.get("commits") or [])
    out: dict[str, dict] = {}
    for i, r in enumerate(rows):
        r = dict(r)
        r.setdefault("our_board_rank", i + 1)
        out[r.get("name")] = r
    if year is not None:
        from ..sim import recruiting as sim_recruiting
        for r in sim_recruiting.national_list(year):
            name = r.get("name")
            if name and name not in out:
                out[name] = r
    return out


def _enrich_contacts(contacts: list[dict], dynasty: dict | None = None, year: int | None = None) -> list[dict]:
    """Attach contact_meta to each contact so the UI can show category-specific identity info."""
    board = _board_recruits(dynasty, year)
    # Game data (roster + identity) comes from the dynasty save, not the store.
    players = (dynasty or {}).get("roster", {}).get("key_players", []) or []
    team = (dynasty or {}).get("team", {}) or {}

    result = []
    for contact in contacts:
        c = dict(contact)
        entity = contact.get("entity") or {}
        kind = entity.get("kind", "none")
        name = entity.get("name", "")

        if kind == "recruit" and name:
            rec = board.get(name)
            if rec:
                c["contact_meta"] = {
                    "position": rec.get("position", ""),
                    "stars": rec.get("stars", 0),
                    "national_rank": rec.get("national_rank"),
                    "our_board_rank": rec.get("our_board_rank"),
                    "expected_nil": rec.get("expected_nil", 0),
                    "stage": rec.get("stage", ""),
                    "leader": rec.get("leader", ""),
                }

        elif kind == "player" and name:
            player = next((p for p in players if p.get("name") == name), None)
            if player:
                c["contact_meta"] = {
                    "position": player.get("position", ""),
                    "depth_chart_slot": player.get("depth_chart_slot", ""),
                    "current_nil": player.get("current_nil", 0),
                }

        elif kind == "budget":
            c["contact_meta"] = {"school": team.get("school", "")}

        result.append(c)
    return result


def enrich_one(contact: dict, dynasty: dict | None = None, year: int | None = None) -> dict:
    """Single-contact version of _enrich_contacts (for the resolve endpoint)."""
    return _enrich_contacts([contact], dynasty, year)[0]


# Contacts are user-editable (see customization.py); read at call time.
def _contacts():
    return customization.section("phone_contacts")


SYSTEM = (
    "You are role-playing a single person texting with a college football head "
    "coach (the user) inside a phone messaging app. Stay fully in character per "
    "the profile and what that person plausibly knows. Text like a real person: "
    "usually a single short message, sometimes two, only occasionally three. Never "
    "narrate, never break character. Never use dashes as punctuation; use commas "
    "or periods, never dashes."
)


def _contact(contact_id: str) -> dict[str, Any] | None:
    """Resolve any contact id (curated or synthetic) to a contact with a profile."""
    return directory.by_id(contact_id)


# --- actions (NIL offers, recruiting hours, budget talk) ------------------
def _apply_action(contact: dict, action: dict, dynasty: dict, *, year: int, week: int) -> dict[str, Any]:
    entity = contact.get("entity") or {}
    atype = action.get("type")
    eid = action.get("entity_id") or budget.entity_id(entity.get("name", ""))

    if atype == "nil_offer":
        kind = action.get("kind") or entity.get("kind")
        amount = int(action.get("amount", 0))
        effect = budget.project_nil_offer(eid, kind, amount, dynasty)
        if not effect.get("error"):
            # Queue the real mutation for the Simulator; the effect is the
            # optimistic (pending) projection shown in the chat.
            inbox.append({"kind": "nil_offer", "entity_id": eid, "entity_kind": kind,
                          "amount": amount, "year": year, "week": week})
        return effect

    if atype == "recruiting_action":
        action_key = action.get("action_key", "")
        effect = budget.project_recruiting_action(eid, action_key, dynasty)
        if not effect.get("error") and effect.get("ok", True):
            inbox.append({"kind": "recruiting_action", "entity_id": eid,
                          "action_key": action_key, "year": year, "week": week})
        return effect

    if atype == "budget_request":
        snap = dynasty.get("budget") or {}
        dp = snap.get("dynasty_points", {})
        nil = snap.get("nil", {})
        return {
            "kind": "budget_request",
            "available_dp": dp.get("available"),
            "total_dp": dp.get("total"),
            "recruiting_available": (nil.get("recruiting") or {}).get("available"),
            "message": "You asked the AD where the NIL and Dynasty Points budget stands.",
        }

    return {"error": "unknown action"}


def _mock_action_reply(contact: dict, action: dict, effect: dict) -> list[str]:
    """An ordered reply pool for an action. _mock_reply trims it to a natural length."""
    atype = action.get("type")

    if atype == "nil_offer":
        amount = int(effect.get("amount", 0))
        expected = int(effect.get("expected", 0)) or 1
        ratio = amount / expected
        if effect.get("entity_kind") == "player":
            if ratio >= 1:
                return ["preciate you coach, that's real", "im locked in here", "lets keep cooking"]
            return ["thats under what im hearing elsewhere coach", "gotta look out for my family", "lets keep talking"]
        # recruit
        if amount == 0:
            return ["wait you pulled my offer?", "thought we were building something here coach"]
        if ratio >= 2:
            return ["yooo thats a serious bag coach", "you just shot to the top of my list fr", "we might need to talk soon"]
        if ratio >= 1:
            return ["appreciate that offer coach", "definitely keeps yall right in it", "gonna talk it over with my family"]
        return ["thats lower than i expected coach", "other schools coming way harder on NIL", "gonna have to think about it"]

    if atype == "recruiting_action":
        if not effect.get("ok", True):
            return []
        table = {
            "send_the_house": ["wow the whole staff?? thats love", "yall showing out fr", "means a lot coach"],
            "schedule_visit": ["bet, lets lock in that visit", "ready to see campus"],
            "hard_sell": ["i hear you coach", "yall make a strong case"],
            "head_coach_visit": ["respect you coming yourself coach", "that hits different"],
            "coordinator_visit": ["always good talking ball with the staff"],
            "send_dm": ["appreciate you checking in coach"],
        }
        return table.get(action.get("action_key"), ["appreciate the love coach"])

    if atype == "budget_request":
        dp = effect.get("available_dp", 0)
        return [f"You're sitting on {dp} Dynasty Points available right now.",
                "Spend it where it wins games. I won't be reopening the checkbook midseason."]

    return ["Got it, thanks coach."]


def _take(seed_key: str, options: list[str]) -> list[str]:
    """Pick a natural number of bubbles from `options` (in priority order), seeded
    so a given exchange is stable. Usually one message, sometimes two, rarely three."""
    options = [o for o in options if o]
    if not options:
        return []
    rng = random.Random(seed_key)
    r = rng.random()
    if r < 0.7 or len(options) == 1:
        n = 1
    elif r < 0.9 or len(options) == 2:
        n = 2
    else:
        n = min(3, len(options))
    return options[:n]


def _generic_pool(contact: dict, dynasty: dict) -> list[str]:
    """A varied reply pool for a contact with no hand-written mock lines."""
    kind = (contact.get("profile") or {}).get("kind", "contact")
    up = dynasty["schedule"]["upcoming"]["opponent"]
    pools = {
        "recruit": ["appreciate you reaching out coach", "still taking my time with everything", "what would my role look like there?"],
        "transfer": ["thanks coach, im weighing my options", "whats the depth chart situation look like", "appreciate the interest"],
        "player": ["all good coach", "locked in for saturday", "lets get this one"],
        "staff": ["on it coach", f"{up} prep is looking sharp", "we'll be ready"],
        "opp_coach": ["good to hear from you coach", "always respected your program", "see you out there"],
        "candidate": ["appreciate you coach", "keeping my focus where my feet are for now"],
        "media": ["thanks for the text coach", "anything you can give me on the record?", "ill keep it fair to you"],
        "analyst": ["appreciate the insight coach", "ill factor that into my read"],
        "voter": ["noted coach", "the resume will speak for itself"],
        "committee": ["good to hear from you coach", "you know i cant get into the room talk"],
    }
    return pools.get(kind, ["got it, thanks coach"])


def _mock_reply(contact: dict, message: str, dynasty: dict, action: dict | None = None, effect: dict | None = None) -> list[str]:
    if action and effect:
        if effect.get("error"):
            return []
        pool = _mock_action_reply(contact, action, effect)
    else:
        cid = contact["id"]
        up = dynasty["schedule"]["upcoming"]["opponent"]
        table = {
            "five_star_target": ["appreciate the love coach", f"fired up for the {up} visit this weekend", "gonna be a big decision soon"],
            "recruit_s": ["thanks for reaching out coach", "still taking it slow and weighing my options", "what does my development path look like there?"],
            "oc": ["We're dialed in.", f"Tempo plan is set for {up}. We want to play fast and make them defend the whole field."],
            "dc": ["Front seven is ready.", f"Pressure package is dialed up for {up}. We'll make them earn every yard."],
            "ad": ["Appreciate the update.", "The trajectory speaks for itself. Let's keep building the right way."],
            "star_qb": ["All good coach.", "Just focused on the game plan and taking care of the ball. Team's ready."],
            "rb": ["Feeling fresh coach", "Just give me the rock and I'll do the rest."],
            "insider": ["Hearing things on that job we talked about...", "Can't say more yet. What are YOU hearing on your end?"],
            "beat_writer": ["Thanks coach. Quick one for the story:", f"What's the message to the room ahead of {up}?"],
        }
        pool = table.get(cid) or _generic_pool(contact, dynasty)
    seed = contact["id"] + "|" + (message or "") + "|" + (action.get("type", "") if action else "")
    return _take(seed, pool)


def _persona_text(contact: dict) -> str:
    """Human-readable personality sliders + backstory, for the in-character prompt."""
    traits = contact.get("traits") or {}
    parts = [
        f"{t['label']} {traits[t['key']]}/100 ({t['low']} to {t['high']})"
        for t in personality.PERSONALITY_TRAITS if t["key"] in traits
    ]
    out = ""
    if parts:
        out += " Personality sliders (let these shape tone and motivation): " + ", ".join(parts) + "."
    if contact.get("bio"):
        out += " Backstory: " + contact["bio"]
    return out


# --- relationship + role aware knowledge brief ----------------------------
_STATE_RE = re.compile(r",\s*([A-Za-z]{2})\.?\s*$")  # "Frisco, TX" -> "TX"


def _hometown_state(hometown: str | None) -> str | None:
    m = _STATE_RE.search(hometown or "")
    return m.group(1).upper() if m else None


def _program_state(dynasty: dict) -> str | None:
    """Best-effort program home state: the most common state among the program's
    own commits' hometowns. Returns None if it cannot be determined."""
    counts: dict[str, int] = {}
    for rec in (dynasty.get("recruiting", {}).get("commits") or []):
        st = _hometown_state(rec.get("hometown"))
        if st:
            counts[st] = counts.get(st, 0) + 1
    return max(counts, key=counts.get) if counts else None


def _head_to_head(dynasty: dict, team: str) -> str:
    program = dynasty["team"]["name"]
    for g in dynasty.get("schedule", {}).get("full", []) or []:
        if g.get("opponent") == team and g.get("result"):
            outcome = "win" if g["result"] == "W" else "loss"
            return f"a {g.get('score', '')} {program} {outcome} in Week {g.get('week', '')}".strip()
    return ""


def _recruit_brief(record: dict, dynasty: dict, texted_before: bool) -> str:
    program = dynasty["team"]["name"]
    stages = customization.RECRUIT_STAGES
    stage = record.get("stage") or "Open"
    stage_idx = stages.index(stage) if stage in stages else 0
    interest = int(record.get("interest") or 0)
    we_lead = (record.get("leader") or "") == program
    ht = record.get("hometown") or ""
    state = _hometown_state(ht)
    prog_state = _program_state(dynasty)
    in_state = bool(state) and state == prog_state
    warmth = stage_idx * 2 + (2 if we_lead else 0) + (1 if in_state else 0) + (interest // 25) + (2 if texted_before else 0)

    pos = record.get("position") or "athlete"
    stars = record.get("stars")
    where = f" out of {ht}" if ht else ""
    lines = [f"You are {record.get('name')}, a {stars}-star {pos}{where}. The coach texting you is from {program}."]
    if record.get("dealbreaker"):
        lines.append(f"What matters most to you in your decision: {record['dealbreaker']}.")

    rel = []
    rel.append("You have texted this coach before, so pick up naturally and reference your prior conversations."
               if texted_before else "This is the first time this coach has reached out to you directly.")
    if we_lead:
        rel.append(f"{program} is your current leader, so you are warm, engaged and genuinely interested.")
    elif interest >= 55:
        rel.append(f"You like {program} and are paying real attention, but they are not your clear leader yet.")
    elif interest >= 30:
        rel.append(f"{program} is in your mix, but you are noncommittal and still shopping around.")
    else:
        rel.append(f"You are barely considering {program} right now, so you play it cool and a little distant.")
    rel.append("You grew up near this program and have a soft spot for staying home." if in_state
               else "You are from out of state, so you do not know this program intimately.")
    lines.append(" ".join(rel))

    if warmth >= 9:
        lines.append("Because you are far along with this staff, you know the head coach and coordinators by name, you "
                     "remember your visit and what they pitched you (playing time, NIL, development), and you talk like "
                     "someone who can already picture himself there.")
    elif warmth >= 5:
        lines.append("You know the basics about this program (roughly how good they are this year, who the coach is) but "
                     "not the inner details. You only know specifics the coach has actually told you.")
    else:
        lines.append("You know very little about this program beyond its name and reputation. You do NOT know the assistant "
                     "coaches, the scheme or any internal plans unless the coach tells you here. Keep it polite but vague, "
                     "and feel free to ask who is reaching out or what they can offer you.")
    lines.append("These are tendencies, not a script. Let your mood, where you are in the cycle and exactly what the coach "
                 "just said move you. You can be unpredictable, warm one day and guarded the next.")
    return "\n".join(lines)


def _transfer_brief(record: dict, dynasty: dict, texted_before: bool) -> str:
    program = dynasty["team"]["name"]
    origin = record.get("from") or record.get("to")
    pos = record.get("position") or "player"
    where = f" out of {origin}" if origin else ""
    return "\n".join([
        f"You are {record.get('name')}, a {pos} in the transfer portal{where}. The coach texting you is from {program}.",
        ("You have spoken before, so continue the thread naturally." if texted_before
         else "This is a first contact from this staff."),
        "You are evaluating fit, playing time, scheme and NIL. You know your own situation well but only know this program "
        "at a surface level unless the coach fills you in. Be candid about what you are looking for.",
        "These are tendencies, not a script; let the conversation move you.",
    ])


def _player_brief(record: dict, dynasty: dict) -> str:
    up = dynasty["schedule"]["upcoming"]["opponent"]
    pos = record.get("position") or ""
    lines = [f"You are {record.get('name')}, {record.get('depth_chart_slot') or pos} for {dynasty['team']['name']}. You "
             f"are in the building every day, so you know your teammates, the staff, the game plan and the schedule.",
             f"Your next game is against {up}."]
    if record.get("note"):
        lines.append(f"Scouting note on you: {record['note']}.")
    lines.append("Talk like a current player: loose with your coach, honest about your role, your NIL and how the team feels.")
    return "\n".join(lines)


def _staff_brief(kind: str, dynasty: dict) -> str:
    if kind == "ad":
        return ("You are the Athletic Director. You think in budgets, Dynasty Points, facilities and expectations. You "
                "know the program's full situation and speak in measured, big-picture terms about its trajectory.")
    up = dynasty["schedule"]["upcoming"]["opponent"]
    return ("You are a coach on this staff. You know the roster, the recruiting board, the game plan, recent results and "
            f"the schedule cold. The next opponent is {up}. Talk shop with the head coach in clipped, confident football terms.")


def _coach_brief(record: dict, dynasty: dict, kind: str) -> str:
    program = dynasty["team"]["name"]
    if kind == "candidate":
        return (f"You are {record.get('name')}, currently {record.get('current') or 'a coach whose name is on the carousel'}. "
                f"Your name comes up for open jobs. You are ambitious but careful on the record. The coach texting you leads "
                f"{program}. Keep your options, and your cards, close.")
    team = record.get("team") or "your program"
    note = record.get("note") or ""
    lines = [f"You are {record.get('coach') or record.get('name')}, the head coach at {team}. The coach texting you leads "
             f"{program}, a rival program."]
    if record.get("record"):
        lines.append(f"Your team is {record['record']}. {note}".strip())
    h2h = _head_to_head(dynasty, team)
    lines.append(f"On the field this season: {h2h}." if h2h else f"You have not faced {program} on the field this season.")
    lines.append("You know the coaching world and your own situation. Be professional and a little guarded with a rival, "
                 "cordial but careful about what you reveal.")
    return "\n".join(lines)


def _media_brief(contact: dict, dynasty: dict, year: int, week: int) -> str:
    record = (contact.get("profile") or {}).get("record") or {}
    name = contact["name"]
    outlet = record.get("outlet") or contact.get("outlet") or ""
    beat = record.get("beat") or ""
    lines = [f"You are {name}, a member of the media" + (f" for {outlet}" if outlet else "") +
             f". The coach texting you leads {dynasty['team']['name']}."]
    if beat:
        lines.append(f"Your beat: {beat}.")
    arts = directory.articles_by(name, year, week)
    if arts:
        bits = "; ".join(f'"{a["headline"]}" (W{a["week"]})' for a in arts[:4] if a.get("headline"))
        if bits:
            lines.append(f"Pieces you have written this season: {bits}. You can reference your own reporting.")
    else:
        lines.append("Lean on your beat and reputation; you have no recent bylines on record to cite.")
    last_take = (narrative.load(year).get("personas", {}).get(name) or {}).get("last_take")
    if last_take:
        lines.append(f"Your last interaction with this coach: {last_take}.")
    lines.append("You are friendly but always working an angle. Fish for quotes and information, and trade a little to get "
                 "a little. You will not burn your other sources.")
    return "\n".join(lines)


def _committee_brief(record: dict, dynasty: dict) -> str:
    lens = record.get("lens") or record.get("bias") or ""
    lines = [f"You are {record.get('name')}, a College Football Playoff selection committee member ({record.get('role', '')})."]
    if lens:
        lines.append(f"How you weigh the field: {lens}")
    lines.append("You are diplomatic and careful never to reveal the room's deliberations. You can talk in general terms "
                 "about resumes and what teams still need to prove.")
    return "\n".join(lines)


def _knowledge_brief(contact: dict, dynasty: dict, history: list[dict], year: int, week: int) -> str:
    profile = contact.get("profile") or {}
    kind = profile.get("kind", "contact")
    record = profile.get("record") or {}
    texted_before = any(m.get("from") == "them" for m in history)

    if kind == "recruit":
        brief = _recruit_brief(record, dynasty, texted_before)
    elif kind == "transfer":
        brief = _transfer_brief(record, dynasty, texted_before)
    elif kind == "player":
        brief = _player_brief(record, dynasty)
    elif kind in ("staff", "ad"):
        brief = _staff_brief(kind, dynasty)
    elif kind in ("opp_coach", "candidate"):
        brief = _coach_brief(record, dynasty, kind)
    elif kind in ("media", "analyst", "voter"):
        brief = _media_brief(contact, dynasty, year, week)
    elif kind == "committee":
        brief = _committee_brief(record, dynasty)
    else:
        brief = ""

    # Anyone (other than the reporters themselves) may plausibly be aware of what
    # the media has written about them. Offered as available context, not a script.
    if kind not in ("media", "analyst", "voter"):
        about = directory.articles_about(contact.get("name", ""), year, week)
        bits = "; ".join(f'"{a["headline"]}"' for a in about[:3] if a.get("headline"))
        if bits:
            brief += ("\nYou may have seen that the media has written about you lately: " + bits
                      + ". Reference it only if it fits who you are.")
    return brief


def _poll_top(dynasty: dict, key: str, n: int = 5) -> list[str]:
    arr = (dynasty.get("national", {}) or {}).get(key) or []
    out = []
    for i, e in enumerate(arr[:n]):
        if isinstance(e, str):
            out.append(f"{i + 1}. {e}")
        elif isinstance(e, dict):
            out.append(f"{i + 1}. {e.get('team') or e.get('name') or e.get('abbr') or ''}")
    return [s for s in out if s.strip().rstrip(".0123456789 ")]


def _public_brief(dynasty: dict) -> str:
    """The public knowledge layer: polls, the season's big/ranked games, the
    upcoming game, the national poll, and rivalry storylines. What anyone
    following college football could know about the program."""
    t = dynasty["team"]
    up = dynasty["schedule"]["upcoming"]
    rk = t.get("rankings", {}) or {}
    rec = t.get("record", {}).get("overall", "")
    rkbits = ", ".join(f"{k.upper()} #{v}" for k, v in
                       [("cfp", rk.get("cfp")), ("ap", rk.get("ap")), ("coaches", rk.get("coaches"))] if v)
    lines = ["Public knowledge anyone following college football could have:",
             f"- {t['name']} are {rec}" + (f" ({rkbits})" if rkbits else "") + " this season."]
    for g in [g for g in dynasty.get("schedule", {}).get("recent_results", []) or [] if g.get("result")][-4:]:
        ranked = " (ranked opponent)" if g.get("rank") else ""
        outcome = "won" if g["result"] == "W" else "lost"
        lines.append(f"- Week {g.get('week')}: {outcome} {g.get('score', '')} "
                     f"{'vs' if g.get('home') else 'at'} {g.get('opponent', '')}{ranked}.")
    lines.append(f"- Next up: {'home vs' if up.get('home') else 'on the road at'} {up.get('opponent', '')}.")
    poll = _poll_top(dynasty, "ap_top25") or _poll_top(dynasty, "cfp_top12")
    if poll:
        lines.append("- National poll top 5: " + "; ".join(poll) + ".")
    rnotes = [f"{r.get('name')} ({r.get('note')})" for r in (dynasty.get("rivals") or []) if r.get("note")][:2]
    if rnotes:
        lines.append("- Rivalry storylines: " + " | ".join(rnotes) + ".")
    return "\n".join(lines)


def _news_block(year: int, week: int) -> str:
    """Recent national + program news headlines, the public reporting layer."""
    heads = directory.recent_headlines(year, week)
    if not heads:
        return ""
    bits = [f"  - [W{h['week']}] {h['headline']}" + (f" ({h['category']})" if h.get("category") else "")
            for h in heads if h.get("headline")]
    return "Recent national and program news headlines (public reporting):\n" + "\n".join(bits)


def _scoped_context(dynasty: dict, year: int, week: int) -> str:
    """Public-facing context for people outside the program (recruits, opposing
    coaches, media, committee): the public knowledge + reporting layers, never the
    program's internal data. The per-person brief decides how much of this they
    actually lean on."""
    t = dynasty.get("team", {}) or {}
    hc = (t.get("head_coach", {}) or {}).get("name", "the head coach")
    parts = []
    fp = base.flashpoints(dynasty, year, week)
    if fp:
        parts.append(fp)
    parts.append(_public_brief(dynasty))
    news = _news_block(year, week)
    if news:
        parts.append(news)
    presser = directory.press_conference_block(year, coach_name=hc, up_to_week=week)
    if presser:  # the coach's public post-game remarks, quotable in a media text
        parts.append(presser)
    intro = (
        f"You are role-playing one person texting {hc}, the head coach of {t.get('name')} (the user), inside a "
        "FICTIONAL college football dynasty universe. Use ONLY the facts below. NEVER use real-world coaches, "
        "players, or results, even for real teams; the head coach is "
        f"{hc} and nobody else, so address the coach accordingly. Stay in character and only reference what this "
        "person would plausibly know. Never use dashes as punctuation; use commas or periods.\n\n"
        f"=== KEY FACTS ===\n{base.grounding_facts(dynasty)}\n\n"
    )
    return intro + "\n\n".join(parts)


def _render_history(history: list[dict], name: str, limit: int = 30) -> str:
    """The conversation as a transcript so replies have natural flow and lasting
    memory of what was said. Action receipts collapse to a short marker."""
    out: list[str] = []
    for m in history[-limit:]:
        if m.get("kind") == "receipt":
            out.append("Coach: [made an NIL or recruiting offer]")
        elif m.get("text"):
            who = "Coach" if m.get("from") == "me" else name
            out.append(f"{who}: {m['text']}")
    return "\n".join(out)


def _prompt(contact: dict, message: str, action: dict | None, effect: dict | None,
            brief: str, history_text: str) -> str:
    lines = [
        f"You are {contact['name']} ({contact['role']}). Texting style: {contact['personality']}."
        + _persona_text(contact)
    ]
    if brief:
        lines.append("Who you are and what you know right now:\n" + brief)
    if history_text:
        lines.append("Your conversation with this coach so far (oldest first). You always remember everything you "
                     "have texted each other and stay consistent with it:\n" + history_text)
    if effect and not effect.get("error") and effect.get("message"):
        lines.append("The coach just did this in the program's NIL/budget system: " + effect["message"]
                     + " React to it in character.")
    if message:
        lines.append(f'The coach just texted you: "{message}"')
    elif not effect:
        lines.append("The coach just reached out to you (no message text, he is starting the conversation).")
    lines.append('Reply in character as a text message. Ground your reply in what is actually happening right now '
                 '(see the RIGHT NOW section if present). Only reference a game result or a press conference if one '
                 'actually appears there; if the season has not started, do NOT invent a game or remarks the coach '
                 'made. Do NOT recycle earlier messages in this thread or fall back on vague, generic optimism (no '
                 'empty "culture" talk). Usually answer with a SINGLE short message. Sometimes send 2, and only '
                 'occasionally 3 when it genuinely feels natural. Do not pad or repeat yourself. Return STRICT JSON: '
                 '{"messages": ["..."]}. JSON only.')
    return "\n\n".join(lines)


def _inbound_prompt(contact: dict, brief: str, history_text: str, topic: str) -> str:
    """Prompt for an NPC who is texting the coach FIRST (no incoming message)."""
    lines = [
        f"You are {contact['name']} ({contact['role']}). Texting style: {contact['personality']}."
        + _persona_text(contact)
    ]
    if brief:
        lines.append("Who you are and what you know right now:\n" + brief)
    if history_text:
        lines.append("Your conversation with this coach so far (oldest first). You always remember everything you "
                     "have texted each other and stay consistent with it:\n" + history_text)
    lines.append("You are texting this coach FIRST, starting the conversation yourself. He did NOT text you. "
                 "Why you are reaching out right now: " + topic)
    lines.append("Anchor your text in what is ACTUALLY happening (see the RIGHT NOW section above). Only reference a "
                 "game result or a press conference if one actually appears there; if the season has not started, do "
                 "NOT invent a game outcome or any remarks the coach made. React to the real, specific situation and "
                 "its tone. Do NOT repeat earlier messages in this thread and do NOT fall back on vague, generic "
                 "optimism or empty 'culture' lines.")
    lines.append('Open the conversation naturally, the way a real person fires off an unprompted text. Do not reply as '
                 'if answering him and do not wait to be greeted. Usually a SINGLE short message, only occasionally two. '
                 'Return STRICT JSON: {"messages": ["..."]}. JSON only.')
    return "\n\n".join(lines)


def compose_inbound(contact: dict, dynasty: dict, *, year: int, week: int, use_llm: bool,
                    topic: str, mock_pool: list[str] | None = None) -> list[str]:
    """Generate the opening bubbles for a person texting the coach first, in
    character and aware of the conversation so far. Returns sanitized message
    strings (1 to 2). Does NOT persist; the inbound module owns delivery so the
    once-per-week guard lives in one place."""
    cid = contact["id"]
    history = msg_store.thread(year, cid)
    kind = (contact.get("profile") or {}).get("kind", "contact")

    # Same board reconciliation reply() does, so a recruit's stars/stage/interest
    # are accurate even for a national-class prospect in no customization section.
    if kind == "recruit":
        rec = _board_recruits(dynasty, year).get((contact.get("entity") or {}).get("name") or contact.get("name"))
        if rec:
            prof = contact.setdefault("profile", {})
            prof["record"] = {**(prof.get("record") or {}), **rec}

    messages: list[Any] | None = None
    if use_llm and base.llm_available():
        try:
            brief = _knowledge_brief(contact, dynasty, history, year, week)
            history_text = _render_history(history, contact["name"])
            if kind in _INSIDER_KINDS:
                context = base.build_context(dynasty, year, week)
                news = _news_block(year, week)
                if news:
                    context += "\n\n=== RECENT NEWS HEADLINES ===\n" + news
            else:
                context = _scoped_context(dynasty, year, week)
            res = llm.generate_json(SYSTEM, _inbound_prompt(contact, brief, history_text, topic),
                                    cached_context=context, grounding=base.reactive_grounding(dynasty, year, week),
                                    max_tokens=300, temperature=0.7)
            m = res.get("messages") if isinstance(res, dict) else res
            if isinstance(m, list) and m:
                messages = m
        except Exception:
            messages = None
    if messages is None:
        messages = _take(f"{cid}|inbound|{week}", mock_pool or _generic_pool(contact, dynasty))

    messages = [str(m).strip() for m in messages if isinstance(m, (str, int, float)) and str(m).strip()][:2]

    if kind in ("media", "analyst", "voter", "committee"):
        narrative.update_persona(year, contact["name"],
                                 {"last_take": f"texted the coach first in {dynasty['season']['week_label']}"})
    return base.sanitize(messages)


def reply(contact_id: str, message: str, dynasty: dict, *, year: int, week: int,
          use_llm: bool, action: dict | None = None) -> dict[str, Any]:
    contact = _contact(contact_id)
    if not contact:
        return {"error": "unknown contact"}

    effect: dict[str, Any] | None = None
    if action:
        effect = _apply_action(contact, action, dynasty, year=year, week=week)

    history = msg_store.thread(year, contact_id)
    kind = (contact.get("profile") or {}).get("kind", "contact")

    # Unify a recruit with the live board (sim or customization): enrich the
    # record the brief reads so stars/stage/interest/leader are accurate, even
    # for a national-class prospect that lives in no customization section.
    if kind == "recruit":
        rec = _board_recruits(dynasty, year).get((contact.get("entity") or {}).get("name") or contact.get("name"))
        if rec:
            prof = contact.setdefault("profile", {})
            prof["record"] = {**(prof.get("record") or {}), **rec}

    source = "mock"
    if use_llm and base.llm_available():
        try:
            brief = _knowledge_brief(contact, dynasty, history, year, week)
            history_text = _render_history(history, contact["name"])
            if kind in _INSIDER_KINDS:
                context = base.build_context(dynasty, year, week)
                news = _news_block(year, week)
                if news:
                    context += "\n\n=== RECENT NEWS HEADLINES ===\n" + news
            else:
                context = _scoped_context(dynasty, year, week)
            res = llm.generate_json(SYSTEM, _prompt(contact, message, action, effect, brief, history_text),
                                    cached_context=context, grounding=base.reactive_grounding(dynasty, year, week),
                                    max_tokens=600, temperature=0.7)
            messages = res.get("messages") if isinstance(res, dict) else res
            if not isinstance(messages, list) or not messages:
                messages = _mock_reply(contact, message, dynasty, action, effect)
            source = "llm"
        except Exception:
            messages = _mock_reply(contact, message, dynasty, action, effect)
    else:
        messages = _mock_reply(contact, message, dynasty, action, effect)

    messages = [str(m).strip() for m in messages if isinstance(m, (str, int, float)) and str(m).strip()][:5]

    if kind in ("media", "analyst", "voter", "committee"):
        narrative.update_persona(year, contact["name"], {"last_take": f"texted the coach in {dynasty['season']['week_label']}"})

    echo = {k: v for k, v in contact.items() if k != "profile"}
    out: dict[str, Any] = {
        "contact": echo,
        "messages": [{"from": "them", "text": m} for m in messages],
        "source": source,
    }
    if action:
        out["effect"] = effect
        # Authoritative budget from the save; the effect above is the pending
        # projection until the Simulator drains the inbox and rewrites the save.
        out["budget"] = dynasty.get("budget") or budget.snapshot(year, week, dynasty)
    out = base.sanitize(out)

    # Persist the exchange so the conversation survives a reload. The stored
    # order mirrors what the UI renders: the coach's outgoing text, then an
    # action receipt (NIL offer / recruiting move), then the in-character reply.
    record: list[dict[str, Any]] = []
    if message:
        record.append({"from": "me", "text": message})
    if action is not None:
        record.append({"from": "me", "kind": "receipt", "effect": out.get("effect")})
    record.extend(out["messages"])
    msg_store.append(year, contact_id, record)

    return out


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    sim = (dynasty.get("meta") or {}).get("source") == "sim"
    curated = _contacts()
    # In a simulated season the recruiting board is the national-class slice, so
    # drop the stale customization recruit contacts and list the live board.
    if sim:
        curated = [c for c in curated if (c.get("entity") or {}).get("kind") != "recruit"]
    contacts = _enrich_contacts(curated, dynasty, year)
    have = {c["id"] for c in contacts}

    if sim:
        rec = dynasty.get("recruiting") or {}
        board = list(rec.get("commits") or [])
        board += sorted(rec.get("targets") or [], key=lambda r: -(r.get("interest") or 0))[:25]
        for r in board:
            person = directory.resolve(r.get("name"), "recruit")
            if not person:
                continue
            person = enrich_one(person, dynasty, year)
            person.pop("profile", None)
            if person["id"] in have:
                continue
            contacts.append(person)
            have.add(person["id"])

        # The full roster: every player on the team is textable, so the Players tab
        # shows the squad, not just the curated handful (star QB, RB).
        for p in (dynasty.get("roster") or {}).get("key_players") or []:
            person = directory.resolve(p.get("name"), "player")
            if not person:
                continue
            person = enrich_one(person, dynasty, year)
            person.pop("profile", None)
            if person["id"] in have:
                continue
            contacts.append(person)
            have.add(person["id"])

    # Surface anyone the coach has already texted (resolved through the directory)
    # so every conversation shows in the Messages list, just like a real phone.
    for cid in msg_store.threads(year):
        if cid in have:
            continue
        person = directory.by_id(cid)
        if not person:
            continue
        person = enrich_one(person, dynasty, year)
        person.pop("profile", None)
        thread = msg_store.thread(year, cid)
        person["preview"] = next((m.get("text") for m in reversed(thread) if m.get("text")), "")
        contacts.append(person)
        have.add(cid)

    # Every contact who has a live thread (curated, board or texted) shows the
    # real last message and a week marker, so an unprompted text the coach has
    # not opened yet reads like a real Messages list instead of static flavor.
    all_threads = msg_store.threads(year)
    for c in contacts:
        thread = all_threads.get(c["id"])
        if not thread:
            continue
        last = next((m.get("text") for m in reversed(thread) if m.get("text")), "")
        if last:
            c["preview"] = last
            c["time"] = f"Wk {week}"
    return base.sanitize({"module": MODULE, "source": "static", "contacts": contacts, "categories": CATEGORIES})
