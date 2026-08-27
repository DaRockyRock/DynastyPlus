"""Top stories slider.

Five major stories per week. Each story is a headline, subheadline, lede
paragraph, and byline, tagged with one of five categories that each carry an
accent color. Stories must reference actual dynasty data.
"""
from __future__ import annotations

import re
from typing import Any

from .. import conferences, llm, progress, world_events
from . import article_detail, base

MODULE = "top_stories"
CATEGORIES = ["CFP watch", "Coaching carousel", "Recruiting", "Transfer portal", "Heisman watch"]

SYSTEM = (
    "You are the lead editor of a national college football outlet writing the "
    "five biggest stories of the week for a featured homepage slider. Voice: "
    "sharp, modern sports-media, confident but credible. Every story must be "
    "grounded in the provided dynasty data (real records, rankings, players, "
    "recruits, opponents). Never use dashes as punctuation; use commas or periods, never dashes."
)


_SHAPE = (
    'Return STRICT JSON as an OBJECT of this exact shape: {"stories": [ ... exactly 5 '
    "story objects ... ]}. Each story object has keys:\n"
    '  "category" (one of: ' + ", ".join(CATEGORIES) + "),\n"
    '  "scope" ("program" if the story is mainly about the user\'s team, or "national" '
    "for a story about other teams or the national picture),\n"
    '  "headline" (punchy, <= 80 chars),\n'
    '  "subheadline" (one supporting sentence),\n'
    '  "lede" (a single 2-4 sentence opening paragraph),\n'
    '  "byline" (fictional reporter name + fictional outlet, e.g. "Dana Reyes, The Press Box").\n'
    "Use a different category for each story when possible. Use ONLY invented, "
    "fictional reporter and outlet names; never a real publication (no ESPN, "
    "The Athletic, etc.) and never a real-life coach or player. Output JSON only."
)


def _prompt(dynasty: dict) -> str:
    team = dynasty["team"]["name"]
    week = dynasty["season"]["week_label"]
    if base.is_season_open(dynasty):
        intro = (
            f"It is the START of the {dynasty['season']['year']} season for {team}. NO games have been "
            "played yet, so write SEASON-OPENING stories, not game recaps. Frame the year ahead and the "
            "current landscape using these grounded facts:\n\n"
            + base.season_landscape(dynasty) + "\n\n"
            "Across the five stories, cover: the coaching situation (if the head coach is in his FIRST "
            "season, make that a central story, including how last season ended and the new era it "
            "begins), preseason expectations and rankings, key returning players to watch, the incoming "
            "recruiting class, and the marquee or rivalry games on the schedule. The FIRST story must be "
            "about the user's program (scope \"program\"); keep at least one of the others national (scope "
            "\"national\"). Tag every story with a \"scope\".\n\n"
        )
    else:
        intro = (
            f"Write the FIVE top stories for {week} for a NATIONAL homepage slider. The user's program is {team}.\n\n"
            "REQUIRED MIX, follow this exactly:\n"
            f"1. The FIRST story (the lead) must be about {team}, the biggest thing happening with them right now. "
            "Use the RIGHT NOW brief above (the latest result and what the coach said publicly). Set its scope to "
            "\"program\".\n"
            f"2. At least THREE of the other four stories must be NATIONAL, about OTHER teams or the wider sport, "
            f"NOT about {team}: the national title and playoff race, the Heisman picture, the coaching carousel, a "
            "marquee game or an upset between OTHER programs, a top-25 storyline. Lean on the national rankings and "
            "the other teams in the data. Set their scope to \"national\".\n"
            f"Do NOT make every story about {team}. {team} leads the slider, but the rest of the country fills it "
            "out.\n\n"
        )
    return intro + _SHAPE


def _attach_accents(stories: list[dict]) -> list[dict]:
    out = []
    for s in stories:
        cat = s.get("category", "National")
        s["accent"] = base.accent_for(cat)
        out.append(s)
    return out


def _is_program(story: dict, needles: list[str]) -> bool:
    """Whether a story is about the user's program: trust the model's `scope` tag,
    falling back to whether the team's name/school/nickname appears in the copy."""
    scope = (story.get("scope") or "").lower()
    if scope == "program":
        return True
    if scope == "national":
        return False
    blob = " ".join(str(story.get(k, "")) for k in ("headline", "subheadline", "lede")).lower()
    return any(n in blob for n in needles)


# Head-to-head language: with exactly two teams named, any of these turns a story
# into a "matchup" (the slider draws a VS bug) rather than a plain pair.
_MATCHUP_RE = re.compile(
    r"\bvs\.?\b|\bversus\b|\bhosts?\b|\bvisits?\b|\btravels?\b|\bfaces?\b|"
    r"\bmatchup\b|\bshowdown\b|\bclash\b|\bbeats?\b|\bdefeats?\b|\bupsets?\b|"
    r"\bknocks?\s+off\b|\bwin\s+over\b|\bloss\s+to\b|\bfalls?\s+to\b|"
    r"\btakes?\s+down\b|\bedges?\b|\btopples?\b|\b\d{1,2}-\d{1,2}\b"
)


def _conf_needles() -> list[tuple[str, str]]:
    """(needle, canonical conference name) pairs, longest needle first. The bare words
    "American" and "FBS Independents" are too generic to match in prose, so they are
    only reached through distinctive aliases (AAC, etc.)."""
    skip = {"american", "fbs independents"}
    out = [(name.lower(), name) for name in conferences.CONFERENCES if name.lower() not in skip]
    out += [
        ("aac", "American"), ("american athletic", "American"),
        ("c-usa", "Conference USA"), ("cusa", "Conference USA"),
        ("mid-american", "MAC"), ("pac 12", "Pac-12"), ("big-12", "Big 12"),
        ("b1g", "Big Ten"), ("fbs independents", "FBS Independents"),
    ]
    out.sort(key=lambda kv: len(kv[0]), reverse=True)
    return out


def _league_index(dynasty: dict) -> dict[str, dict[str, Any]]:
    """Lowercased team needle -> team info ({espn_id, name, abbr, conference, color,
    logo, is_user}). Built from the user team, the full FBS coaching directory, and
    the AP poll. Each team contributes its full name and its name minus the mascot
    (>= 4 chars) so "Ohio State Buckeyes" and "Ohio State" both resolve."""
    index: dict[str, dict[str, Any]] = {}

    def add(name, eid, abbr=None, conf=None, color=None, logo=None, is_user=False):
        if not name or not eid:
            return
        info = {"espn_id": eid, "name": str(name), "abbr": abbr, "conference": conf,
                "color": color, "logo": logo, "is_user": is_user}
        for v in {str(name).strip(), " ".join(str(name).split()[:-1]).strip()}:
            key = v.lower()
            if len(key) >= 4:
                index.setdefault(key, info)

    team = dynasty.get("team") or {}
    add(team.get("name"), team.get("espn_id"), team.get("abbr"), team.get("conference"),
        team.get("color"), team.get("logo"), is_user=True)
    for tname, c in (dynasty.get("coaches") or {}).items():
        if isinstance(c, dict):
            add(c.get("team") or tname, c.get("espn_id"), c.get("abbr"), c.get("conference"))
    for r in (dynasty.get("national", {}) or {}).get("ap_top25") or []:
        if isinstance(r, dict):
            add(r.get("team"), r.get("espn_id"), r.get("abbr"))
    return index


def _teams_in(blob: str, index: dict[str, dict[str, Any]], cap: int = 6) -> list[dict[str, Any]]:
    """Teams named in `blob`, ordered by first appearance, deduped by espn_id, capped.
    Longest needles match first and consume their span, so "Ohio" inside "Ohio State"
    never double-counts as Ohio (Bobcats)."""
    consumed = [False] * len(blob)
    found: dict[Any, tuple[int, dict[str, Any]]] = {}
    for needle in sorted(index, key=len, reverse=True):
        info = index[needle]
        for m in re.finditer(r"\b" + re.escape(needle) + r"\b", blob):
            s, e = m.start(), m.end()
            if any(consumed[s:e]):
                continue
            for i in range(s, e):
                consumed[i] = True
            eid = info["espn_id"]
            if eid not in found or s < found[eid][0]:
                found[eid] = (s, info)
    ordered = [info for _, info in sorted(found.values(), key=lambda kv: kv[0])]
    return ordered[:cap]


def _conf_in(blob: str, needles: list[tuple[str, str]]) -> dict[str, Any] | None:
    """The conference named earliest in `blob`, as {id, name}, or None."""
    best: tuple[int, dict[str, Any]] | None = None
    for needle, canon in needles:
        m = re.search(r"\b" + re.escape(needle) + r"\b", blob)
        if not m or (best is not None and m.start() >= best[0]):
            continue
        rec = conferences.resolve(canon)
        if rec:
            best = (m.start(), {"id": rec["id"], "name": rec["name"]})
    return best[1] if best else None


def _team_pub(t: dict[str, Any]) -> dict[str, Any]:
    """The slim, frontend-facing team payload (no internal scan flags)."""
    out: dict[str, Any] = {"espn_id": t["espn_id"], "name": t["name"]}
    for k in ("abbr", "color", "logo"):
        if t.get(k):
            out[k] = t[k]
    return out


def _blob(story: dict, *, body: bool) -> str:
    parts = [str(story.get(k, "")) for k in ("headline", "subheadline", "lede")]
    if body:
        parts += [str(x) for x in ((story.get("detail") or {}).get("sections") or [])]
    return " ".join(parts).lower()


def _attach_marks(stories: list[dict], dynasty: dict) -> list[dict]:
    """Tag each story with the team/conference logos it references, so the slider can
    render a crisp broadcast bug (a matchup VS, a conference mark, or a cluster of team
    logos). Detection runs on the VISIBLE copy (headline, subheadline, lede) so the
    logos always match what the slide shows. Also sets the faint background watermark
    (`espn_id`) for national stories: the named non-user team, falling back to a scan
    of the article body when the team appears only there. Program stories keep the user
    watermark (espn_id left unset), so the lead slide stays the user's team."""
    index = _league_index(dynasty)
    confs = _conf_needles()
    user_espn = (dynasty.get("team") or {}).get("espn_id")
    for s in stories:
        visible = _blob(s, body=False)
        teams = _teams_in(visible, index)
        conf = _conf_in(visible, confs)

        if not s.get("espn_id") and (s.get("scope") or "").lower() != "program":
            lead = next((t for t in teams if t["espn_id"] != user_espn), None)
            if lead is None:
                lead = next((t for t in _teams_in(_blob(s, body=True), index)
                             if t["espn_id"] != user_espn), None)
            if lead is not None:
                s["espn_id"] = lead["espn_id"]

        # The bug treatment: a head-to-head matchup, a group of teams, a conference, or
        # a single team. The frontend (StoryMarks) picks the layout from `kind`.
        n = len(teams)
        is_matchup = n == 2 and bool(_MATCHUP_RE.search(visible))
        kind = ("matchup" if is_matchup
                else "group" if n >= 2
                else "conference" if conf
                else "team" if n == 1
                else None)
        s["marks"] = {"kind": kind, "conference": conf, "teams": [_team_pub(t) for t in teams]}
    return stories


def _program_first(stories: list[dict], dynasty: dict) -> list[dict]:
    """The slider always opens on a story about the user's program. Move the first
    program story to the front (stable otherwise); the rest keep the model's mix of
    national and program angles."""
    if not stories:
        return stories
    team = dynasty.get("team", {}) or {}
    needles = [str(n).lower() for n in (team.get("name"), team.get("school"), team.get("nickname")) if n]
    idx = next((i for i, s in enumerate(stories) if _is_program(s, needles)), None)
    if idx is None or idx == 0:
        return stories
    return [stories[idx]] + stories[:idx] + stories[idx + 1:]


def _wl(rec: str) -> tuple[int, int]:
    try:
        w, l = str(rec).split("-")[:2]
        return int(w), int(l)
    except (ValueError, AttributeError):
        return 0, 0


def _standing_phrase(cfp, ap, rec: str) -> str:
    if cfp:
        return f"No. {cfp} in the projected playoff field"
    if ap:
        return f"No. {ap} in the national rankings"
    w, l = _wl(rec)
    if w and not l:
        return "unbeaten and pushing toward the rankings"
    if w >= l:
        return "building a resume in the thick of the race"
    return "scuffling and looking for a spark"


def _expectation_phrase(rk: dict) -> str:
    if rk.get("cfp"):
        return f"a preseason No. {rk['cfp']} in the projected playoff field"
    if rk.get("ap"):
        return f"a preseason No. {rk['ap']} ranking"
    return "outside the preseason rankings, with something to prove"


def _mock_open(dynasty: dict) -> list[dict[str, Any]]:
    """Season-opening landscape stories: the coaching situation (new coach's first
    year if so), last season + expectations, a star to watch, the recruiting class,
    and the portal/opener. Grounded in the program history + roster + board."""
    team = dynasty["team"]
    name = team["name"]
    school = team.get("school", name)
    conf = team.get("conference", "")
    hc = team.get("head_coach", {}) or {}
    coach = hc.get("name", "the head coach")
    tenure = int(hc.get("tenure_years") or 1)
    rk = team.get("rankings", {}) or {}
    year = dynasty["season"].get("year")
    hist = dynasty.get("history") or []
    last = hist[0] if hist else None
    pred = base.predecessor_coach(dynasty)
    players = dynasty["roster"].get("key_players") or []
    star = players[0] if players else None
    rec = dynasty.get("recruiting", {}) or {}
    crank = rec.get("class_rank_national")
    portal = (dynasty.get("transfer_portal", {}) or {}).get("incoming") or []
    up = dynasty["schedule"].get("upcoming") or {}
    expect = _expectation_phrase(rk)
    last_line = f"{last['overall']} a year ago ({(last.get('result') or '').lower()})" if last else "a quiet offseason"
    hist_bits = "; ".join(f"{h.get('year')} {h.get('overall')}" for h in hist[:3])

    stories: list[dict[str, Any]] = []

    # 1) The coaching situation - central if it is a first-year coach.
    if tenure <= 1:
        stories.append({
            "category": "Coaching carousel",
            "headline": f"New era at {school}: {coach} takes over",
            "subheadline": f"A fresh staff inherits a program that went {last['overall'] if last else 'through change'} last fall.",
            "lede": (
                f"{coach} opens his first season as {name}'s head coach"
                + (f", taking over from {pred}. " if pred else ". ")
                + f"After {last_line}, the mandate is a clean reset. {name} enter the {year} season {expect}."
            ),
            "byline": "Dana Reyes, The Press Box",
        })
    else:
        stories.append({
            "category": "Coaching carousel",
            "headline": f"Year {tenure}: {coach} maps out {school}'s season",
            "subheadline": f"Coming off {last['overall'] if last else 'last season'}, the {name.split()[-1]} reset for {year}.",
            "lede": (
                f"{coach} enters year {tenure} at {name} after {last_line}. The roster is set, the schedule is "
                f"out, and the program opens {year} {expect}."
            ),
            "byline": "Dana Reyes, The Press Box",
        })

    # 2) Expectations / where the program stands.
    stories.append({
        "category": "CFP watch",
        "headline": f"{school} opens {year} {('ranked' if (rk.get('ap') or rk.get('cfp')) else 'unranked')} in the {conf}",
        "subheadline": f"The {name.split()[-1]} begin the year as {expect}.",
        "lede": (
            f"Expectations are set for {name}. "
            + (f"Recent history reads {hist_bits}. " if hist else "")
            + f"Now the {year} season starts to write itself."
        ),
        "byline": "Marcus Hale, Saturday Authority",
    })

    # 3) A returning star to watch.
    if star:
        stories.append({
            "category": "Heisman watch",
            "headline": f"{star.get('name')} headlines the {school} watch list",
            "subheadline": f"The {star.get('position')} is {name}'s biggest name entering {year}.",
            "lede": (
                f"{star.get('name')}, {name}'s {star.get('position')}, is the player to watch this fall"
                + (f" ({star.get('draft_stock')})" if star.get("draft_stock") else "")
                + f". A big season would put him in the national conversation."
            ),
            "byline": "Marcus Hale, Saturday Authority",
        })

    # 4) The incoming recruiting class.
    if crank:
        stories.append({
            "category": "Recruiting",
            "headline": f"{school} brings in the No. {crank} class nationally",
            "subheadline": f"The new staff's first full class reshapes the {name.split()[-1]} roster.",
            "lede": (
                f"{name} signed the No. {crank} class in the country, the kind of haul that sets up the next "
                f"few seasons. The work now is turning that talent into results."
            ),
            "byline": "Theo Marsh, RecruitWire",
        })

    # 5) Portal additions or the opener.
    if portal:
        p0 = portal[0]
        stories.append({
            "category": "Transfer portal",
            "headline": f"{school} adds {p0.get('name')} from the portal",
            "subheadline": f"The {p0.get('position')} arrives from {p0.get('from', 'another program')} for {year}.",
            "lede": (
                f"{p0.get('name')}, a {p0.get('position')} from {p0.get('from', 'the portal')}, joins {name} to "
                f"fill a need right away. The transfer market did its part to round out the roster."
            ),
            "byline": "Ron Castellano, Portal Report",
        })
    elif up.get("opponent"):
        stories.append({
            "category": "CFP watch",
            "headline": f"{school} opens {('at home against' if up.get('home') else 'on the road at')} {up.get('opponent')}",
            "subheadline": "The season kicks off with an early measuring stick.",
            "lede": (
                f"{name} begin the year {('hosting' if up.get('home') else 'traveling to')} {up.get('opponent')}. "
                f"It is the first read on whether the offseason buzz holds up."
            ),
            "byline": "Dana Reyes, The Press Box",
        })

    # Everything above is about the user's program; tag it so the slider knows.
    for s in stories:
        s.setdefault("scope", "program")

    # National preseason stories, so the slider is not 100% the user's team. Each
    # carries the leading team's espn_id so the slider can show that team's logo.
    national: list[dict[str, Any]] = []
    ap25 = (dynasty.get("national", {}) or {}).get("ap_top25") or []
    top = [r for r in ap25[:4] if r.get("team")]
    if top:
        names = [r["team"] for r in top]
        national.append({
            "category": "CFP watch", "scope": "national",
            "espn_id": top[0].get("espn_id"), "team": top[0].get("team"),
            "headline": f"{names[0]} headlines the preseason top 25",
            "subheadline": f"{', '.join(names[1:3]) or 'the contenders'} give chase as the {year} season opens.",
            "lede": (
                f"{names[0]} open the year at No. 1, with {', '.join(names[1:4]) or 'a deep field'} in pursuit. "
                "The preseason poll sets the bar; the schedule will decide the real contenders."
            ),
            "byline": "Marcus Hale, Saturday Authority",
        })
    heis = (dynasty.get("national", {}) or {}).get("heisman_frontrunners") or []
    if heis:
        def _hname(h): return (h.get("name") if isinstance(h, dict) else str(h)) or ""
        def _hteam(h): return (h.get("team", "") if isinstance(h, dict) else "") or ""
        def _hespn(h): return h.get("espn_id") if isinstance(h, dict) else None
        h0 = heis[0]
        others = [_hname(h) for h in heis[1:3] if _hname(h)]
        national.append({
            "category": "Heisman watch", "scope": "national",
            "espn_id": _hespn(h0), "team": _hteam(h0),
            "headline": f"{_hname(h0)} tops the preseason Heisman board",
            "subheadline": (f"{', '.join(others)} are right there entering {year}." if others
                            else f"The race opens wide entering {year}."),
            "lede": (
                f"{_hname(h0)}" + (f" of {_hteam(h0)}" if _hteam(h0) else "")
                + " leads the preseason Heisman conversation"
                + (f", with {', '.join(others)} in the mix" if others else "")
                + ". The favorites set the tone; the season writes the rest."
            ),
            "byline": "Camille Booker, The Rundown",
        })

    # Guarantee a second national angle (the chase behind No. 1) when the Heisman
    # board is empty preseason, so the slider is a real national mix, not 1 story.
    if len(national) < 2 and len(top) >= 2:
        chasers = [r for r in top[1:4] if r.get("team")]
        if chasers:
            cnames = [r["team"] for r in chasers]
            national.append({
                "category": "CFP watch", "scope": "national",
                "espn_id": chasers[0].get("espn_id"), "team": chasers[0].get("team"),
                "headline": f"{cnames[0]} leads a loaded chase entering {year}",
                "subheadline": f"{', '.join(cnames[1:]) or 'the contenders'} are right there behind the No. 1 spot.",
                "lede": (
                    f"{cnames[0]} headline the group chasing the top of the poll, with "
                    f"{', '.join(cnames[1:]) or 'a deep field'} in the hunt. The {year} title race looks wide open."
                ),
                "byline": "Marcus Hale, Saturday Authority",
            })

    # Lead with the program, then weave the national stories in, capped at five.
    return (stories[:1] + national + stories[1:])[:5]


def _mock(dynasty: dict) -> list[dict[str, Any]]:
    """Honest, dynasty-grounded fallback stories. Derives every claim from the
    actual record, ranking, latest result, upcoming game, Heisman board, and
    national poll so the slider tracks the simulated season (never demo prose)."""
    if base.is_season_open(dynasty):
        return _mock_open(dynasty)
    team = dynasty["team"]
    name = team["name"]
    school = team.get("school", name)
    rec = team["record"]["overall"]
    cfp = team["rankings"].get("cfp")
    ap = team["rankings"].get("ap")
    week = dynasty["season"]["week_label"]
    up = dynasty["schedule"]["upcoming"]
    recent = dynasty["schedule"].get("recent_results") or []
    last = recent[0] if recent else None
    standing = _standing_phrase(cfp, ap, rec)

    ap25 = (dynasty.get("national", {}) or {}).get("ap_top25") or []
    top_names = [r.get("team") for r in ap25[:4] if r.get("team")]
    heis = (dynasty.get("national", {}) or {}).get("heisman_frontrunners") or []
    qb = dynasty["roster"]["key_players"][0]
    targets = dynasty["recruiting"].get("targets") or []
    commit = targets[0] if targets else None
    portal = dynasty["transfer_portal"].get("outgoing") or []
    portal_out = portal[0] if portal else None

    stories: list[dict[str, Any]] = []

    # 1) The user's program, framed by its real result + standing.
    if last:
        won = last.get("result") == "W"
        verb = "takes down" if won else "drops a tough one to"
        loc = "at home over" if last.get("home") and won else ("on the road at" if not last.get("home") else "to")
        stories.append({
            "category": "CFP watch",
            "headline": f"{school} {verb} {last.get('opponent')} {last.get('score', '')}".strip(),
            "subheadline": f"At {rec}, the {name.split()[-1]} are {standing} heading into {week}.",
            "lede": (
                f"{name} {'handled' if won else 'fell to'} {last.get('opponent')} {last.get('score', '')} "
                f"and sit at {rec}. Next comes {'a home date with' if up.get('home') else 'a road trip to'} "
                f"{up.get('opponent')}, a game that shapes where this season is heading."
            ),
            "byline": "Dana Reyes, The Press Box",
        })
    else:
        stories.append({
            "category": "CFP watch",
            "headline": f"{school} opens the season {'at home against' if up.get('home') else 'on the road at'} {up.get('opponent')}",
            "subheadline": f"The {name.split()[-1]} begin {standing}.",
            "lede": (
                f"The wait is over. {name} kick off {week} {'hosting' if up.get('home') else 'traveling to'} "
                f"{up.get('opponent')}. Expectations are set; now the season starts to write itself."
            ),
            "byline": "Dana Reyes, The Press Box",
        })

    # 2) National poll picture from the real top of the rankings.
    if top_names:
        stories.append({
            "category": "CFP watch",
            "headline": f"{top_names[0]} headlines the latest national rankings",
            "subheadline": f"{', '.join(top_names[:3])} hold the top of the poll in {week}.",
            "lede": (
                f"{top_names[0]} sit atop the rankings, with {', '.join(top_names[1:3]) or 'the chasing pack'} "
                f"close behind. The separation at the top is starting to form as the schedule hardens."
            ),
            "byline": "Marcus Hale, Saturday Authority",
        })

    # 3) Heisman race from the live board (could be any program's star).
    if heis:
        h0 = heis[0]
        stories.append({
            "category": "Heisman watch",
            "headline": f"{h0.get('name')} leads the early Heisman conversation",
            "subheadline": f"The {h0.get('team', '')} {h0.get('position', 'star')} is pacing the field through {week}.",
            "lede": (
                f"{h0.get('name')} of {h0.get('team', '')} has played his way to the front of the Heisman race. "
                f"The numbers back it up, and the spotlight only grows from here."
            ),
            "byline": "Marcus Hale, Saturday Authority",
        })

    # 4) Recruiting, from the user's actual board.
    if commit:
        stars = commit.get("stars")
        interest = commit.get("interest")
        stories.append({
            "category": "Recruiting",
            "headline": f"{school} pushing hard for {stars}-star {commit.get('position')} {commit.get('name')}".strip(),
            "subheadline": f"The staff sits at {interest}/100 interest with {commit.get('name')} as {week} arrives.",
            "lede": (
                f"{commit.get('name')}, a {stars}-star {commit.get('position')} out of {commit.get('hometown', 'a key region')}, "
                f"is a priority on the {name} board. The current leader is {commit.get('leader') or 'wide open'}, and "
                f"every week of contact matters now."
            ),
            "byline": "Theo Marsh, RecruitWire",
        })

    # 5) Portal noise (still scaffolded from customization).
    if portal_out:
        stories.append({
            "category": "Transfer portal",
            "headline": f"Portal watch: {portal_out['name']} a name to monitor",
            "subheadline": "Depth-chart math and the December window are shaping spring rosters.",
            "lede": (
                f"{portal_out['name']} is a name circulating as the portal window approaches. Any move would "
                f"reshuffle depth and open snaps. It is early, but the board is already taking shape."
            ),
            "byline": "Ron Castellano, Portal Report",
        })

    return stories[:5]


def _story_from_article(a: dict[str, Any]) -> dict[str, Any]:
    """A slider story is a VIEW of a news article: same headline, its dek as the
    subheadline, its first paragraph as the lede, and its already-built reader page,
    so opening a slide opens the same full article instantly (no extra generation)."""
    body = a.get("body") or ""
    lede = body.split("\n\n", 1)[0].strip() if body else a.get("dek", "")
    reporter, outlet = a.get("reporter", ""), a.get("outlet", "")
    byline = ", ".join(p for p in (reporter, outlet) if p)
    return {
        "category": a.get("category", "National"),
        "accent": a.get("accent") or base.accent_for(a.get("category", "National")),
        "scope": a.get("scope"), "espn_id": a.get("espn_id"),
        "headline": a.get("headline", ""), "subheadline": a.get("dek", ""), "lede": lede,
        "byline": byline, "detail": a.get("detail"),
    }


def generate(dynasty: dict, *, year: int, week: int, use_llm: bool, regenerate: bool = False) -> dict[str, Any]:
    progress.set_sub_step("Top stories")
    # The slider is a VIEW of the week's news coverage (one shared generation), not a
    # separate model pass. We take the biggest articles, lead with the program, and
    # fill out a national mix. Each carries its full reader page already.
    from . import news_feed
    cov = news_feed.coverage(dynasty, year=year, week=week, use_llm=use_llm, regenerate=False)
    prog = [_story_from_article(a) for a in cov.get("program", [])]
    nat = [_story_from_article(a) for a in cov.get("national", [])]
    stories = [s for s in (prog[:2] + nat[:3] + prog[2:] + nat[3:]) if s.get("headline")]
    if not stories:  # coverage somehow empty: last-resort grounded mock
        stories = _mock(dynasty)

    stories = _attach_accents(stories[:5])
    # The slider always opens on the user's program, then carries the national mix.
    stories = _program_first(stories, dynasty)
    # A blockbuster the coach set off leads the slider (deduped by id, capped).
    stories = world_events.merge_top_stories(stories, year, week)
    # Tag every final story (the national mix and any coach-caused blockbuster) with
    # the team/conference logos it references, plus the background watermark team.
    stories = _attach_marks(stories, dynasty)
    return base.sanitize({"module": MODULE, "source": cov.get("source", "mock"), "stories": stories})
