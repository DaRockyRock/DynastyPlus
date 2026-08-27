"""The validation chain: reject the contradictions a small model produces.

Deterministic, high-precision checks against the Entity Canon and the engine's
own world state. The design principle is NO FALSE REJECTIONS: a fictional analyst
or invented role player is allowed (the universe is full of them); only claims
that contradict the canon or the engine's own facts are flagged. Issues carry a
severity: "hard" issues drop the item (mock backfills), "warn" issues are logged
only. Per-beat regeneration on a hard issue lands in step 3; for now the batch
path drops-and-backfills.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from . import canon as canon_mod
from .canon import Canon
from .state import WorldState

log = logging.getLogger("cfbmod.editorial")


@dataclass
class Issue:
    severity: str   # "hard" | "warn"
    code: str
    detail: str


# A two-token (or three) TitleCase name. Deliberately conservative so we only look
# at things that are clearly person names.
_NAME = r"[A-Z][a-z]+(?:['-][A-Z]?[a-z]+)*(?:\s[A-Z][a-z]+(?:['-][A-Z]?[a-z]+)*){1,2}"

# Coach attributions: "head coach NAME", "coach NAME", "NAME, the TEAM head coach".
# Pattern 3 requires the appositive comma so it cannot grab a distant name out of a
# headline that merely happens to be followed by "head coach".
_COACH_CTX = [
    re.compile(rf"\b(?:head\s+)?coach\s+({_NAME})"),
    re.compile(rf"({_NAME}),\s+(?:the\s+)?(?:[A-Z][\w'.&-]+\s+){{0,3}}head coach\b"),
]
# "5-star CB Emory Cromwell" / "four-star wide receiver Cole Ross" (digit or word)
_WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
_STAR_RE = re.compile(
    rf"\b(?P<n>[Oo]ne|[Tt]wo|[Tt]hree|[Ff]our|[Ff]ive|[1-5])[-\s][Ss]tar\s+"
    rf"(?P<pos>[A-Za-z][A-Za-z /]*?)\s+(?P<name>{_NAME})")
# season-open stat fabrications. A stat number alone is NOT a violation (citing a
# returning player's LAST-season production in a preview is legitimate); it is only a
# violation when framed as CURRENT-season production, which cannot exist before kickoff.
_STAT_RE = [
    re.compile(r"\b\d{2,}\s*(?:yards|yds)\b", re.IGNORECASE),
    re.compile(r"\b(?:threw|passed|ran|rushed)\s+for\s+\d", re.IGNORECASE),
    re.compile(r"\b\d+\s+(?:touchdowns?|tds?|interceptions?|sacks?)\b", re.IGNORECASE),
]
_CURRENT_SEASON = re.compile(
    r"\b(this season|this year|so far|through (?:the )?(?:first )?\w+ games?|"
    r"leads the nation|leading the nation|on pace|heisman (?:front|favorite|race|watch))\b", re.IGNORECASE)
_LAST_SEASON = re.compile(
    r"\b(last season|last year|a year ago|in 202\d|returning|previous season|prior year|"
    r"a season ago|coming off)\b", re.IGNORECASE)
_HOTSEAT_RE = re.compile(
    r"\b(hot seat|on the hot seat|job (?:in jeopardy|is in question)|"
    r"fired|firing|ouster|uncertain future|seat is (?:warm|hot)|"
    r"calls for his (?:job|firing)|on his way out|coaching change|pressure mount)\b", re.IGNORECASE)
# Calendar-impossible framing for the season's first weeks (a week-1 game is not a
# "late-season test"). The model knows football phrasing better than it tracks the
# week number, so this is a common small-model slip.
_LATE_SEASON_RE = re.compile(
    r"\b(late[-\s]season|mid[-\s]?season|down the stretch|stretch run|"
    r"closing weeks|november (?:clash|test|showdown|football)|"
    r"(?:bowl|playoff)[-\s]clinch\w*|rivalry week finale|season finale)\b", re.IGNORECASE)
# Affirming security (the article is saying he is SAFE, the opposite of a violation).
_SECURE_RE = re.compile(
    r"\b(secure|safe|not on|isn't on|is not on|no hot seat|far from|locked in|"
    r"job security|backing|full support|extension|here to stay|in no danger|no pressure)\b",
    re.IGNORECASE)
# words that mean "this person did NOT actually leave/get fired" so we don't flag a
# correctly-hedged note. (kept minimal; hot-seat content about the user is the target)
_KNOWN_TITLES = {"coach", "head", "offensive", "defensive", "special", "the", "former",
                 "interim", "associate", "co"}


def _article_text(item: dict) -> str:
    parts = [item.get("headline"), item.get("dek"), item.get("body"), item.get("claim")]
    body = item.get("body")
    if isinstance(body, list):
        parts[2] = " ".join(str(x) for x in body)
    return "  ".join(str(p) for p in parts if p)


def _check_coaches(text: str, scope: str, canon: Canon) -> list[Issue]:
    """Any name presented as a HEAD coach must be a canonical coach; otherwise it
    is a real-life leak (e.g. 'Ryan Day') or a fabricated coach ('Hank Paxton')."""
    issues: list[Issue] = []
    seen: set[str] = set()
    for rx in _COACH_CTX:
        for m in rx.finditer(text):
            name = m.group(1).strip()
            key = canon_mod.norm(name)
            if key in seen:
                continue
            seen.add(key)
            if canon.is_known_coach(name):
                continue
            if canon.find_person(name):       # a known player/recruit miscaptured, not a coach
                continue
            # ignore captures that are really titles ("Defensive Coordinator Smith"
            # captured as a name) by requiring both tokens to look like a personal name
            toks = name.split()
            if any(canon_mod.norm(t) in _KNOWN_TITLES for t in toks):
                continue
            issues.append(Issue("hard", "coach_not_in_canon",
                                f"'{name}' is named as a head coach but is not in the universe "
                                f"(real-life leak or fabrication)"))
    return issues


def _check_recruit_attrs(text: str, canon: Canon) -> list[Issue]:
    """A '(stars)-star (position) (Name)' phrase must match the recruit's canonical
    stars and position group."""
    issues: list[Issue] = []
    for m in _STAR_RE.finditer(text):
        stars_txt, pos_txt, name = m.group("n"), m.group("pos"), m.group("name").strip()
        ent = canon.find_person(name)
        if not ent or ent.kind not in ("recruit", "player"):
            continue
        stars = _WORDNUM.get(stars_txt.lower(), None)
        stars = stars if stars is not None else (int(stars_txt) if stars_txt.isdigit() else None)
        canon_stars = ent.attrs.get("stars")
        if canon_stars and stars and int(canon_stars) != stars:
            issues.append(Issue("hard", "recruit_stars_mismatch",
                                f"{name} written as {stars}-star but is {canon_stars}-star"))
        cg = canon_mod.position_group(ent.attrs.get("position") or "")
        wg = canon_mod.position_group(pos_txt)
        if cg and wg and cg != wg:
            issues.append(Issue("hard", "recruit_position_mismatch",
                                f"{name} written as {pos_txt} ({wg}) but is "
                                f"{ent.attrs.get('position')} ({cg})"))
    return issues


def _check_season_open_stats(text: str, state: WorldState) -> list[Issue]:
    # Only a violation when a stat is framed as CURRENT-season production at season
    # open. Last-season production in a preview is legitimate and must not be flagged.
    if not state.season_open:
        return []
    if not _CURRENT_SEASON.search(text) or _LAST_SEASON.search(text):
        return []
    for rx in _STAT_RE:
        m = rx.search(text)
        if m:
            return [Issue("hard", "fabricated_season_open_stat",
                          f"cites current-season production ('{m.group(0)}') before any games "
                          "have been played")]
    return []


def _check_user_coach_standing(text: str, scope: str, state: WorldState) -> list[Issue]:
    """A hot-seat / firing narrative about the USER'S coach must be backed by the
    engine's own state (a hot seat or a real shortfall vs expectation). Mason at
    8/100 with no losses is secure; calling that 'uncertain future' is a
    contradiction the model imported from training priors."""
    if scope != "program" or not state.coach_name:
        return []
    if not _HOTSEAT_RE.search(text):
        return []
    # The article is AFFIRMING security ("Mason is secure, not on the hot seat") - that
    # is correct content, not a violation. Only an unmitigated jeopardy claim is flagged.
    if _SECURE_RE.search(text):
        return []
    if not re.search(re.escape(state.coach_name.split()[-1]), text):
        return []
    secure = state.seat_temp < 45 and state.expectation_delta > -1.0
    if secure:
        return [Issue("hard", "unfounded_hot_seat",
                      f"frames {state.coach_name} as on the hot seat, but his seat is "
                      f"{state.seat_temp}/100 and he is {state.expectation_delta:+.1f} vs expectation")]
    return []


def _check_temporal(text: str, state: WorldState) -> list[Issue]:
    """In the season's first weeks, late-season framing is calendar-impossible."""
    if state.week > 3:
        return []
    m = _LATE_SEASON_RE.search(text)
    if m:
        return [Issue("hard", "impossible_calendar_framing",
                      f"describes a week-{state.week} story as '{m.group(0)}'")]
    return []


def check_article(item: dict, *, scope: str, canon: Canon, state: WorldState) -> list[Issue]:
    """Run the chain on one realized article. Structural guards (dashes, emoji,
    self-matchup headlines) live in news_feed/base and run separately."""
    text = _article_text(item)
    issues: list[Issue] = []
    issues += _check_coaches(text, scope, canon)
    issues += _check_recruit_attrs(text, canon)
    issues += _check_season_open_stats(text, state)
    issues += _check_user_coach_standing(text, scope, state)
    issues += _check_temporal(text, state)
    return issues


def passes(item: dict, *, scope: str, canon: Canon, state: WorldState,
           label: str = "") -> bool:
    """True if the item has no HARD issues. Logs every issue for the dev view."""
    issues = check_article(item, scope=scope, canon=canon, state=state)
    hard = [i for i in issues if i.severity == "hard"]
    for i in issues:
        log.log(logging.WARNING if i.severity == "hard" else logging.INFO,
                "VALIDATE %-9s %-26s %s :: %s", i.severity, i.code,
                (item.get("headline") or "")[:48], i.detail)
    return not hard
