"""Universal person directory.

The phone used to text only a curated handful of contacts. This module turns
*any* named person in the dynasty universe into a textable contact, so the coach
can hover any name in the app (a recruit on the board, an opposing coach on the
hot seat, a reporter's byline, a committee member) and start a conversation.

It resolves a name (plus an optional `kind` hint) to a contact in the same shape
the phone screen already consumes (id, name, role, avatar, category, personality,
traits, bio, image, status, entity) and adds a `profile` ({kind, section, record})
that the reply engine uses to build a relationship and role aware context.

Resolution is the single chokepoint that keeps conversation threads from
splitting: a person who is already a curated phone contact (Cam, Antoine, the
coordinators, the AD, the insiders) always resolves back to that curated id, so
hovering their name on a page opens the same thread as the Messages list. Anyone
else gets a stable synthetic id `"<section>:<slug>"`, or `"person:<kind>:<slug>"`
for a name that only appears in generated content and lives in no section.

This module is a leaf: it depends only on customization, personality and cache
(all leaves themselves), so importing it from phone.py introduces no cycle.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import cache, config, customization, messages, personality

# Profile kinds that are members of the media (reporters, analysts, awards
# voters, committee). The coach's conversations with these people feed the news
# generators so articles can quote or allude to what he told them.
_MEDIA_KINDS = {"media", "analyst", "voter", "committee"}

# Persona customization sections that describe textable people, mapped to the
# Messages tab they belong under and the profile `kind` the reply engine keys on.
# Order matters: it is the default search order when a name is ambiguous and no
# `kind` hint is given. head_coach is intentionally absent (that is the user).
_SECTIONS: list[tuple[str, str, str]] = [
    ("targets", "Recruits", "recruit"),
    ("commits", "Recruits", "recruit"),
    ("players", "Players", "player"),
    ("coaching_staff", "Staff", "staff"),
    ("portal_targets", "Recruits", "transfer"),
    ("portal_incoming", "Recruits", "transfer"),
    ("portal_outgoing", "Recruits", "transfer"),
    ("hot_seat_coaches", "Coaches", "opp_coach"),
    ("candidates", "Coaches", "candidate"),
    ("reporters", "Media", "media"),
    ("online_personalities", "Media", "media"),
    ("recruiting_analysts", "Media", "analyst"),
    ("award_voters", "Media", "voter"),
    ("cfp_committee", "Media", "committee"),
]
_SECTION_BY_KEY = {s[0]: s for s in _SECTIONS}

# A `kind` hint from the UI biases which section we search first when a name
# appears in more than one (e.g. Bruce Feldman is both a reporter and a voter).
_KIND_SECTIONS: dict[str, list[str]] = {
    "recruit": ["targets", "commits"],
    "commit": ["commits", "targets"],
    "transfer": ["portal_targets", "portal_incoming", "portal_outgoing"],
    "player": ["players"],
    "staff": ["coaching_staff"],
    "opp_coach": ["hot_seat_coaches"],
    "candidate": ["candidates"],
    "media": ["reporters", "online_personalities"],
    "analyst": ["recruiting_analysts"],
    "voter": ["award_voters"],
    "committee": ["cfp_committee"],
}

# Which kinds map to an entity the NIL/budget engine can actually resolve. Only
# board recruits and roster players are keyed by name in budget.snapshot, and
# staff carry the (nameless) staff marker. Everyone else gets entity kind "none"
# so the in-chat offer bar stays hidden rather than showing a dead button.
_CATEGORY_FOR_KIND = {
    "recruit": "Recruits", "transfer": "Recruits", "player": "Players",
    "staff": "Staff", "ad": "Staff", "opp_coach": "Coaches", "candidate": "Coaches",
    "media": "Media", "analyst": "Media", "voter": "Media", "committee": "Media",
    "contact": "Media",
}


# Game-data sections live in the dynasty save (the Simulator owns them); media
# sections live in the customization store. This maps a directory section key to
# its path inside the dynasty dict so the same `_section_records` call serves both.
_GAME_SECTION_PATHS: dict[str, tuple[str, ...]] = {
    "targets": ("recruiting", "targets"),
    "commits": ("recruiting", "commits"),
    "players": ("roster", "key_players"),
    "coaching_staff": ("coaching_staff",),
    "portal_incoming": ("transfer_portal", "incoming"),
    "portal_outgoing": ("transfer_portal", "outgoing"),
    "portal_targets": ("transfer_portal", "targets"),
}

# Small mtime-keyed cache so the section-search loop reads the save once, not
# once per section. (directory must stay a leaf, so it reads the file directly
# rather than importing pipeline, which would create a cycle.)
_save_cache: dict[str, Any] = {"mtime": None, "data": None}


def _save_dynasty() -> dict[str, Any] | None:
    p = Path(config.SAVE_PATH)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return None
    if _save_cache["mtime"] != mtime:
        try:
            _save_cache["data"] = json.loads(p.read_text())
        except (OSError, ValueError):
            _save_cache["data"] = None
        _save_cache["mtime"] = mtime
    return _save_cache["data"]


def _section_records(sec: str) -> list[dict[str, Any]]:
    """Records for a directory section: game sections from the dynasty save,
    media sections from the customization store."""
    path = _GAME_SECTION_PATHS.get(sec)
    if path is None:
        return customization.section(sec) or []
    node: Any = _save_dynasty()
    for k in path:
        node = node.get(k) if isinstance(node, dict) else None
    return node or []


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def _record_name(record: dict) -> str:
    return (record.get("name") or record.get("coach") or "").strip()


def _initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name) if p]
    return ("".join(p[0] for p in parts[:2]) or name[:2]).upper()


# --- role / personality / status copy by kind -----------------------------
def _role(kind: str, record: dict) -> str:
    pos = record.get("position") or ""
    stars = record.get("stars")
    if kind == "recruit":
        tag = "commit" if (record.get("status") or "").lower().startswith("commit") else "target"
        return f"{stars}-star {pos} {tag}".strip() if stars and pos else f"{pos} recruit".strip() or "Recruit"
    if kind == "transfer":
        origin = record.get("from") or record.get("to")
        return f"{pos} (portal)".strip() + (f", {origin}" if origin else "")
    if kind == "player":
        return record.get("depth_chart_slot") or (f"{pos}".strip() or "Player")
    if kind == "staff":
        return record.get("role") or "Coaching staff"
    if kind == "opp_coach":
        return f"Head Coach, {record.get('team', '')}".strip().rstrip(",")
    if kind == "candidate":
        return record.get("current") or record.get("archetype") or "Coaching candidate"
    if kind == "media":
        beat = record.get("beat")
        outlet = record.get("outlet") or ""
        return (f"{beat} reporter, {outlet}".strip() if beat else outlet or "Reporter").strip(", ")
    if kind == "analyst":
        return f"Recruiting analyst, {record.get('outlet', '')}".strip().rstrip(",")
    if kind == "voter":
        return f"Awards voter, {record.get('outlet', '')}".strip().rstrip(",")
    if kind == "committee":
        return record.get("role") or "CFP committee member"
    return record.get("role") or "Contact"


def _personality(kind: str) -> str:
    return {
        "recruit": "A recruit weighing his options. Texts in short bursts, cares about how he is used and his brand.",
        "transfer": "A player in the transfer portal, sizing up his next move and what a program offers him.",
        "player": "One of your players. Team-first but human, talks ball and his own role.",
        "staff": "A coach on staff. Football-obsessed, talks shop in clipped, confident sentences.",
        "opp_coach": "A head coach at another program. Professional and guarded with a rival, measured in public.",
        "candidate": "A coach whose name surfaces on the carousel. Ambitious, careful about what he says on the record.",
        "media": "A reporter working sources. Friendly but probing, always fishing for the next quote or scoop.",
        "analyst": "A recruiting analyst. Reads the trail, hedges his predictions, trades in momentum and visits.",
        "voter": "An awards voter and columnist. Opinionated, leans on narrative and the body of work.",
        "committee": "A selection committee member. Diplomatic, weighs resumes, careful not to tip the room.",
    }.get(kind, "Texts in a natural, in-character voice.")


def _status(kind: str, record: dict) -> str:
    if kind in ("recruit", "transfer"):
        return record.get("stage") or record.get("status") or ""
    if kind == "player":
        return record.get("note") or ""
    if kind == "opp_coach":
        return record.get("note") or ""
    if kind == "candidate":
        return record.get("why") or ""
    if kind in ("media", "analyst", "voter"):
        return record.get("outlet") or ""
    if kind == "committee":
        return record.get("affiliation") or ""
    return record.get("notable") or ""


def _entity(kind: str, name: str) -> dict[str, str]:
    if kind == "recruit":
        return {"kind": "recruit", "name": name}
    if kind == "player":
        return {"kind": "player", "name": name}
    if kind == "staff":
        return {"kind": "staff", "name": ""}
    return {"kind": "none", "name": ""}


def _contact_from_record(section: str, kind: str, record: dict) -> dict[str, Any]:
    name = _record_name(record)
    category = _CATEGORY_FOR_KIND.get(kind, "Media")
    return {
        "id": f"{section}:{_slug(name)}",
        "name": name,
        "role": _role(kind, record),
        "avatar": _initials(name),
        "category": category,
        "personality": _personality(kind),
        "traits": record.get("traits") or personality.default_traits(),
        "bio": record.get("bio") or "",
        "image": record.get("image", ""),
        "status": _status(kind, record),
        "entity": _entity(kind, name),
        "profile": {"kind": kind, "section": section, "record": record},
    }


def _minimal_contact(name: str, kind: str | None) -> dict[str, Any]:
    """A textable contact for a name that lives in no customization section (for
    example a fictional byline that only appears in a generated article)."""
    kind = kind or "media"
    persona = personality.generate_person({"name": name}, noun="contact")
    return {
        "id": f"person:{kind}:{_slug(name)}",
        "name": name,
        "role": _role(kind, {}),
        "avatar": _initials(name),
        "category": _CATEGORY_FOR_KIND.get(kind, "Media"),
        "personality": _personality(kind),
        "traits": persona.get("traits") or personality.default_traits(),
        "bio": persona.get("bio") or "",
        "image": "",
        "status": "",
        "entity": _entity(kind, name),
        "profile": {"kind": kind, "section": None, "record": {"name": name}},
    }


# --- curated phone-contact reconciliation ----------------------------------
def _curated() -> list[dict[str, Any]]:
    return customization.section("phone_contacts")


def _find_record(name: str, kind: str | None) -> tuple[str, str, dict] | None:
    """First persona record matching `name`, searching kind-preferred sections
    first. Returns (section, kind, record)."""
    order = list(_KIND_SECTIONS.get(kind or "", [])) + [s[0] for s in _SECTIONS]
    seen: set[str] = set()
    for sec in order:
        if sec in seen:
            continue
        seen.add(sec)
        meta = _SECTION_BY_KEY.get(sec)
        if not meta:
            continue
        for record in _section_records(sec):
            if _record_name(record) == name:
                return sec, meta[2], record
    return None


def _curated_profile(contact: dict) -> dict[str, Any]:
    """Attach a {kind, section, record} profile to a curated phone contact so the
    reply engine can frame it. Looks up the linked board/roster record when one
    exists, otherwise leans on the contact itself."""
    ent = contact.get("entity") or {}
    ekind, ename = ent.get("kind"), ent.get("name")
    if ekind == "recruit" and ename:
        for sec in ("targets", "commits"):
            rec = next((r for r in _section_records(sec) if r.get("name") == ename), None)
            if rec:
                return {"kind": "recruit", "section": sec, "record": rec}
        return {"kind": "recruit", "section": None, "record": contact}
    if ekind == "player" and ename:
        rec = next((p for p in _section_records("players") if p.get("name") == ename), None)
        return {"kind": "player", "section": "players", "record": rec or contact}
    if ekind == "staff":
        rec = next((c for c in _section_records("coaching_staff")
                    if c.get("role") and c.get("role") == contact.get("role")), None)
        return {"kind": "staff", "section": "coaching_staff", "record": rec or contact}
    if ekind == "budget":
        return {"kind": "ad", "section": None, "record": contact}
    if contact.get("category") == "Media":
        return {"kind": "media", "section": None, "record": contact}
    return {"kind": "contact", "section": None, "record": contact}


def _with_profile(contact: dict) -> dict[str, Any]:
    out = dict(contact)
    out["profile"] = _curated_profile(contact)
    return out


# --- league coaches (every FBS coach, from the save's coaching directory) ---
def _coach_record(name: str, team: str, entity: dict) -> dict[str, Any]:
    """An opp_coach record shaped like a hot_seat_coaches record, built from a
    league coaching-directory entity, so the reply engine frames it the same way."""
    tenure = entity.get("tenure_years")
    return {
        "name": name, "coach": name, "team": team,
        "record": entity.get("record"), "tenure_years": tenure,
        "note": f"Year {tenure} at {team}." if tenure else "",
        "traits": entity.get("traits") or personality.default_traits(),
    }


def _league_coach_contact(name: str | None = None, slug: str | None = None) -> dict[str, Any] | None:
    """Resolve an opposing head coach from the save's league coaching directory by
    display name or id slug. The user's own coach is excluded (he is the user, not a
    textable rival). Returns an opp_coach contact with id 'coach:<slug>'."""
    data = _save_dynasty() or {}
    for team, c in (data.get("coaches") or {}).items():
        if not isinstance(c, dict) or c.get("is_user"):
            continue
        cname = c.get("name")
        if not cname:
            continue
        if (name is not None and cname == name) or (slug is not None and _slug(cname) == slug):
            return _contact_from_record("coach", "opp_coach", _coach_record(cname, team, c))
    return None


# --- public API ------------------------------------------------------------
def resolve(name: str, kind: str | None = None) -> dict[str, Any] | None:
    """A name (plus optional kind hint) to a textable contact, reconciled against
    the curated phone roster first so existing threads are reused."""
    name = (name or "").strip()
    if not name:
        return None

    curated = _curated()
    # 1. curated link by entity name (recruits/players the coach already texts).
    for c in curated:
        ent = c.get("entity") or {}
        if ent.get("name") and ent["name"] == name:
            return _with_profile(c)
    # 2. curated contact by display name (e.g. a media personality).
    for c in curated:
        if c.get("name") == name:
            return _with_profile(c)

    found = _find_record(name, kind)
    # 3. staff reconciliation: a staff member maps to a curated contact by role,
    # since the curated display name ("Coach Salomone") may differ from the staff
    # record name ("Ricky Salomone").
    if found and found[1] == "staff":
        role = found[2].get("role")
        for c in curated:
            ent = c.get("entity") or {}
            if ent.get("kind") == "staff" and role and c.get("role") == role:
                return _with_profile(c)
    if found:
        return _contact_from_record(found[0], found[1], found[2])

    # 4. an opposing head coach from the league coaching directory (every FBS team
    # has one in the save). Lets the coach text any rival coach by name.
    coach = _league_coach_contact(name=name)
    if coach:
        return coach

    # 5. a name that lives in no section (a generated byline, etc.).
    return _minimal_contact(name, kind)


def by_id(contact_id: str) -> dict[str, Any] | None:
    """Reverse a contact id back to a contact. Curated ids return the curated
    contact; "section:slug" rebuilds from that section; "person:kind:slug" is a
    minimal contact whose display name is recovered from the slug. Returns None
    for a stale id whose person no longer exists."""
    if not contact_id:
        return None
    for c in _curated():
        if c.get("id") == contact_id:
            return _with_profile(c)

    if contact_id.startswith("person:"):
        _, _, rest = contact_id.partition(":")
        kind, _, slug = rest.partition(":")
        name = slug.replace("_", " ").title()
        return _minimal_contact(name, kind or None)

    if contact_id.startswith("coach:"):
        return _league_coach_contact(slug=contact_id.split(":", 1)[1])

    section, _, slug = contact_id.partition(":")
    meta = _SECTION_BY_KEY.get(section)
    if not meta or not slug:
        return None
    for record in _section_records(section):
        if _slug(_record_name(record)) == slug:
            return _contact_from_record(section, meta[2], record)
    return None


def _byline_name(byline: str) -> str:
    return (byline.split(",", 1)[0] if byline else "").strip()


def _recent_weeks(year: int, week: int, n: int = 6) -> list[int]:
    """The most recent cached weeks this season up to `week` (newest first)."""
    return [w["week"] for w in cache.list_cached_weeks()
            if w["year"] == year and w["week"] <= week][:n]


def articles_by(name: str, year: int, week: int, limit: int = 5) -> list[dict[str, Any]]:
    """Recent articles attributed to a reporter, scanning the most recent cached
    weeks (newest first, this season, up to the current week). Best-effort: any
    cache problem yields an empty list rather than breaking a text reply."""
    out: list[dict[str, Any]] = []
    if not name:
        return out
    try:
        for wk in _recent_weeks(year, week):
            feed = cache.get_module(year, wk, "news_feed") or {}
            for key in ("national", "program", "insider_reports"):
                for art in feed.get(key, []) or []:
                    if art.get("reporter") == name:
                        out.append({"week": wk, "headline": art.get("headline", ""),
                                    "category": art.get("category", ""), "outlet": art.get("outlet", "")})
                        if len(out) >= limit:
                            return out
            stories = cache.get_module(year, wk, "top_stories") or {}
            for story in stories.get("stories", []) or []:
                if _byline_name(story.get("byline", "")) == name:
                    out.append({"week": wk, "headline": story.get("headline", ""),
                                "category": story.get("category", ""), "outlet": ""})
                    if len(out) >= limit:
                        return out
    except Exception:
        return out
    return out


def recent_headlines(year: int, week: int, limit: int = 8) -> list[dict[str, Any]]:
    """Recent national + program + insider headlines and top stories (newest
    first). The public news layer anyone could have read. Best-effort."""
    out: list[dict[str, Any]] = []
    try:
        for wk in _recent_weeks(year, week, n=5):
            feed = cache.get_module(year, wk, "news_feed") or {}
            for key in ("national", "program", "insider_reports"):
                for art in feed.get(key, []) or []:
                    if art.get("headline"):
                        out.append({"week": wk, "headline": art["headline"],
                                    "category": art.get("category", ""),
                                    "byline": art.get("reporter") or art.get("outlet", "")})
            stories = cache.get_module(year, wk, "top_stories") or {}
            for story in stories.get("stories", []) or []:
                if story.get("headline"):
                    out.append({"week": wk, "headline": story["headline"],
                                "category": story.get("category", ""),
                                "byline": _byline_name(story.get("byline", ""))})
            if len(out) >= limit * 2:
                break
    except Exception:
        return out[:limit]
    return out[:limit]


def articles_about(name: str, year: int, week: int, limit: int = 4) -> list[dict[str, Any]]:
    """Recent articles that mention a person by name (in the headline, dek, body
    or claim). Lets a recruit or coach plausibly know what is being written about
    them. Best-effort."""
    out: list[dict[str, Any]] = []
    if not name:
        return out
    needle = name.lower()
    try:
        for wk in _recent_weeks(year, week, n=5):
            feed = cache.get_module(year, wk, "news_feed") or {}
            for key in ("national", "program", "insider_reports"):
                for art in feed.get(key, []) or []:
                    blob = " ".join(str(art.get(f, "")) for f in ("headline", "dek", "body", "claim")).lower()
                    if needle in blob:
                        out.append({"week": wk, "headline": art.get("headline", ""), "outlet": art.get("outlet", "")})
                        if len(out) >= limit:
                            return out
            stories = cache.get_module(year, wk, "top_stories") or {}
            for story in stories.get("stories", []) or []:
                blob = " ".join(str(story.get(f, "")) for f in ("headline", "subheadline", "lede")).lower()
                if needle in blob:
                    out.append({"week": wk, "headline": story.get("headline", ""), "outlet": ""})
                    if len(out) >= limit:
                        return out
    except Exception:
        return out
    return out


def media_interviews_block(year: int, *, coach_name: str = "The head coach", max_lines: int = 60) -> str:
    """A transcript of every conversation the coach has had with media members,
    so the news generators can quote him directly or allude to what he told a
    reporter. Reads the live message store (the source of truth), so a reporter's
    knowledge of what the coach said is always current. Returns "" if there are no
    media conversations this season. Best-effort: never breaks news generation."""
    try:
        threads = messages.threads(year)
    except Exception:
        return ""
    blocks: list[str] = []
    for cid, items in threads.items():
        contact = by_id(cid)
        if not contact:
            continue
        if (contact.get("profile") or {}).get("kind", "") not in _MEDIA_KINDS:
            continue
        lines = []
        for it in items[-max_lines:]:
            txt = it.get("text")
            if not txt:
                continue
            who = coach_name if it.get("from") == "me" else contact.get("name", "Reporter")
            lines.append(f"  {who}: {txt}")
        if not lines:
            continue
        role = contact.get("role") or ""
        header = contact.get("name", "Reporter") + (f", {role}" if role else "")
        blocks.append(f"[{header}]\n" + "\n".join(lines))
    if not blocks:
        return ""
    intro = (
        "=== THE COACH ON THE RECORD WITH MEDIA ===\n"
        f"Real text conversations between {coach_name} and media members. You MAY quote "
        f"{coach_name} directly from his own messages (the lines labeled with his name), or "
        "allude to what he told a reporter. Keep any quote faithful to what he actually said, "
        "attribute it to him, and prefer the reporter he spoke with as the byline for a story "
        "built on it. Only use this when it fits the story, and never invent quotes he did not "
        "give.\n\n"
    )
    return intro + "\n\n".join(blocks)


def press_conference_block(year: int, *, coach_name: str = "The head coach",
                           up_to_week: int | None = None, max_pressers: int = 2) -> str:
    """A transcript of the coach's recent POST-GAME PRESS CONFERENCES, so the news
    generators and media texts can quote what he said publicly. Unlike the private
    text threads above, a presser is on the record and fair game for ANY reporter,
    local or national. Reads the interview transcript store directly (kept a leaf,
    so this import never cycles). Returns "" if there are no completed pressers."""
    try:
        from . import interview  # local import: interview is a leaf, avoids a cycle
        pressers = interview.completed(year)
    except Exception:
        return ""
    if up_to_week is not None:
        pressers = [p for p in pressers if p.get("week", 0) <= up_to_week]
    if not pressers:
        return ""
    blocks: list[str] = []
    for p in list(reversed(pressers))[:max_pressers]:  # most recent first
        lines = [f"[Press conference after {p.get('result_line', 'the game')}]"]
        for t in p.get("turns", []):
            rep = t.get("reporter_name", "Reporter")
            lines.append(f"  {rep}: {t.get('question', '')}")
            lines.append(f"  {coach_name}: {t.get('answer', '')}")
            if t.get("follow_up_question"):
                lines.append(f"  {rep}: {t['follow_up_question']}")
                if t.get("follow_up_answer"):
                    lines.append(f"  {coach_name}: {t['follow_up_answer']}")
        blocks.append("\n".join(lines))
    intro = (
        "=== POST-GAME PRESS CONFERENCE (public, on the record) ===\n"
        f"What {coach_name} said publicly at his post-game press conference. These remarks are "
        "public, so ANY reporter, local or national, may quote them directly or reference them in "
        "a story or a text. Keep quotes faithful to what he actually said and attribute them to "
        f"{coach_name}. Never invent quotes he did not give.\n\n"
    )
    return intro + "\n\n".join(blocks)
