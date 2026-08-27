"""Shared helpers for generation modules."""
from __future__ import annotations

import json
import re
from typing import Any

from .. import llm, narrative

# Emoji / pictograph ranges. Project rule: no emojis anywhere in the app or in
# generated content. This is the server-side safety net (LLM output included).
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF"   # pictographs, emoji, supplemental symbols
    "\U00002600-\U000027BF"    # misc symbols + dingbats
    "\U00002B00-\U00002BFF"    # misc symbols and arrows block (stars etc)
    "\U0000FE00-\U0000FE0F"    # variation selectors
    "\U0001F1E6-\U0001F1FF"    # regional indicator flags
    "\U00002640-\U00002642"
    "\U0000200D\U000020E3\U0000FE0F]+",
    flags=re.UNICODE,
)

# Category accent colors for the top-stories slider and news tagging.
# Hex values only; the frontend maps these to gradients/borders.
CATEGORY_COLORS = {
    "CFP watch": "#3b82f6",
    "Coaching carousel": "#f59e0b",
    "Recruiting": "#22c55e",
    "Transfer portal": "#a855f7",
    "Heisman watch": "#eab308",
    "Program": "#e41c38",
    "National": "#64748b",
    "Rivalry": "#ef4444",
    "Injury": "#f97316",
}

DEFAULT_ACCENT = "#64748b"


def accent_for(category: str) -> str:
    return CATEGORY_COLORS.get(category, DEFAULT_ACCENT)


def sanitize(value: Any) -> Any:
    """Recursively clean generated content.

    Project rules enforced here as a safety net (mock and LLM output alike):
      * no dashes used as punctuation - em/en dashes and spaced hyphens become
        commas; hyphens inside words and scores (top-15, 28-24) are preserved
      * no emojis anywhere
    Whitespace left behind by removed glyphs is tidied without disturbing
    paragraph breaks.
    """
    if isinstance(value, str):
        # Strip any HTML / embed markup first. Generated content is always plain
        # text, but a model occasionally echoes a tweet-embed blockquote or stray
        # tags, which must never reach the UI (it renders post/article text
        # verbatim, so a tag would show as a broken-looking literal). Only matches
        # real-looking tags (< followed by a letter, / or !), so math like "3 < 5"
        # and "x > y" survive untouched.
        out = re.sub(r"<[/!a-zA-Z][^>]*>", "", value)
        # Dashes used as punctuation -> commas. In-word hyphens and scores
        # (top-15, 28-24, 7-2, regular-season) have no surrounding spaces, so
        # they survive untouched.
        out = re.sub(r"\s*[—–]+\s*", ", ", out)  # em / en dashes
        out = re.sub(r"\s+--+\s*", ", ", out)                # word -- word
        out = re.sub(r" +-+ +", ", ", out)                   # word - word
        out = re.sub(r"\s+-+\s*$", "", out)                  # trailing " -"
        out = _EMOJI.sub("", out)
        # tidy spaces and any double punctuation the swaps can leave behind
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"([.!?;:])[ \t]*,", r"\1", out)        # ". ," -> "."
        out = re.sub(r",[ \t]*,+", ",", out)                 # ", ," -> ","
        out = re.sub(r"^[ \t]*,[ \t]*", "", out)             # leading comma
        out = re.sub(r"[ \t]+([,.!?;:])", r"\1", out)        # space before punct
        out = re.sub(r"[ \t]+(?=\n)", "", out)
        out = re.sub(r"[ \t]+$", "", out)
        return out
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    return value


def grounding_facts(dynasty: dict) -> str:
    """A short, authoritative bullet list of the facts a small model most often
    gets wrong by reaching for real-world knowledge (the coach, record, rank)."""
    t = dynasty.get("team", {}) or {}
    hc = t.get("head_coach", {}) or {}
    rk = t.get("rankings", {}) or {}
    rec = t.get("record", {}) or {}
    up = dynasty.get("schedule", {}).get("upcoming", {}) or {}
    season = dynasty.get("season", {}) or {}
    players = dynasty.get("roster", {}).get("key_players", []) or []

    def rank(v):
        return f"No. {v}" if v else "unranked"

    tenure = int(hc.get("tenure_years") or 0)
    coach_line = f"Head coach (the user): {hc.get('name')}, {hc.get('title', 'Head Coach')}"
    if tenure <= 1:
        coach_line += " (FIRST SEASON as head coach)"
    elif tenure:
        coach_line += f", year {tenure} of his tenure"
    facts = [
        f"Program: {t.get('name')}",
        coach_line,
        f"Record: {rec.get('overall', '0-0')} overall, {rec.get('conference', '0-0')} in the {t.get('conference', '')}",
        f"Rankings: CFP {rank(rk.get('cfp'))}, AP {rank(rk.get('ap'))}",
        f"Now: {season.get('week_label')}, {season.get('year')} season",
        f"Next opponent: {up.get('opponent', 'TBD')}",
    ]
    hist = dynasty.get("history") or []
    if hist:
        last = hist[0]
        facts.append(f"Last season ({last.get('year')}): {last.get('overall')}, {last.get('result', '')}"
                     + (f", under {last.get('coach')}" if last.get("coach") else ""))
    if players:
        names = ", ".join(f"{p.get('name')} ({p.get('position')})" for p in players[:4])
        facts.append(f"Key players: {names}")
    return "\n".join("  - " + f for f in facts)


# --- the situation brief ("what just happened, react to THIS") -------------
# A small local model cannot mine the salient moment out of the full dynasty
# JSON, so it drifts to generic optimism and parrots its own earlier lines. The
# fix is a short, prominent digest of the few things the program is actually
# reacting to RIGHT NOW (the last result, the coach's own public press-conference
# words, the live storylines), placed high in the system context AND prepended to
# the user prompt (the proven anti-drift lever, see llm._ground), so every
# generator reacts to what really happened instead of inventing a vibe.
def _latest_presser(year: int, week: int) -> dict | None:
    """The coach's most recent completed press conference up to this week, or None.
    Lazy import: interview is a leaf that imports base, so a top-level import would
    cycle."""
    try:
        from .. import interview
        pressers = [p for p in interview.completed(year) if p.get("week", 0) <= week]
    except Exception:
        return None
    return pressers[-1] if pressers else None


def _presser_quotes(presser: dict, limit: int = 5) -> list[str]:
    """The coach's own answers from a presser, verbatim, in order (his public words
    on the record). Follow-up answers count too."""
    out: list[str] = []
    for turn in presser.get("turns", []):
        for key in ("answer", "follow_up_answer"):
            a = (turn.get(key) or "").strip()
            if len(a) > 1:
                out.append(a)
    return out[:limit]


def _active_threads(year: int, week: int, limit: int = 4) -> list[str]:
    """The most recent DISTINCT live storylines, newest last. Skips the generic
    'a pointed statement is reverberating' pollution so real threads come through."""
    try:
        state = narrative.load(year)
    except Exception:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for th in reversed(state.get("threads", []) or []):  # newest first
        if th.get("week", 0) > week:
            continue
        s = (th.get("summary") or "").strip()
        low = s.lower()
        if not s or low in seen:
            continue
        if "reverberating around" in low or ("pointed" in low and "statement" in low):
            continue  # generic seed noise, carries no information
        seen.add(low)
        out.append(s)
        if len(out) >= limit:
            break
    return list(reversed(out))


def flashpoints(dynasty: dict, year: int, week: int) -> str:
    """A compact, prioritized 'RIGHT NOW' digest of the few things the program is
    reacting to this week. Returns '' when nothing notable has happened yet."""
    t = dynasty.get("team", {}) or {}
    coach = (t.get("head_coach") or {}).get("name") or "the head coach"
    lines: list[str] = []

    # At the very start of the season there is no game and no press conference yet,
    # so say so explicitly. Otherwise a small model invents a result or a presser
    # (people were texting the coach about remarks he never made).
    if is_season_open(dynasty):
        lines.append("The season has NOT started yet: no games have been played and the coach has held no "
                     "press conference, so there are no results or coach remarks to react to. Do not invent "
                     "a game outcome or anything the coach supposedly said.")

    recent = (dynasty.get("schedule") or {}).get("recent_results") or []
    if recent and recent[0].get("result"):
        g = recent[0]
        won = g["result"] == "W"
        loc = "vs" if g.get("home") else "at"
        ranked = " (a ranked opponent)" if g.get("rank") else ""
        lines.append(f"The team just {'WON' if won else 'LOST'} {g.get('score', '')} {loc} "
                     f"{g.get('opponent', '')}{ranked} in week {g.get('week')}.")

    presser = _latest_presser(year, week)
    if presser:
        quotes = _presser_quotes(presser)
        if quotes:
            joined = "; ".join(f'"{q}"' for q in quotes)
            lines.append(
                f"In his post-game press conference ({presser.get('result_line', 'the last game')}), "
                f"{coach} said this, on the record: {joined}. Those are his ACTUAL public words. Anyone "
                f"reacting to {coach} should respond to what he really said here, the tone and the "
                "substance of it, not to vague or generic 'culture' talk.")

    threads = _active_threads(year, week)
    if threads:
        lines.append("Other live storylines: " + "; ".join(s.rstrip(". ") for s in threads) + ".")

    if not lines:
        return ""
    return ("=== RIGHT NOW (what the program is actually reacting to this week; let this drive tone "
            "and what people bring up) ===\n" + "\n".join("- " + ln for ln in lines))


def _league_coaches_block(dynasty: dict, limit: int = 24) -> str:
    """A compact reference of OTHER programs' (fictional) head coaches, drawn from
    dynasty['coaches'] (the Simulator names a coach for every FBS team). Lists the
    teams most likely to appear in coverage (ranked, rivals, opponents) so a story
    about another program names a real fictional coach instead of inventing a
    real-life one. Empty when the save carries no coach directory."""
    coaches = dynasty.get("coaches") or {}
    if not coaches:
        return ""
    user = (dynasty.get("team") or {}).get("name")
    relevant: list[str] = []
    seen: set[str] = set()

    def add(team: str | None) -> None:
        if team and team != user and team in coaches and team not in seen:
            seen.add(team)
            relevant.append(team)

    nat = dynasty.get("national", {}) or {}
    for key in ("ap_top25", "cfp_top12"):
        for row in nat.get(key) or []:
            if isinstance(row, dict):
                add(row.get("team"))
    for r in dynasty.get("rivals") or []:
        if isinstance(r, dict):
            add(r.get("name"))
    sched = dynasty.get("schedule", {}) or {}
    for g in sched.get("recent_results") or []:
        add(g.get("opponent"))
    add((sched.get("upcoming") or {}).get("opponent"))

    relevant = relevant[:limit]
    if not relevant:
        return ""

    def _name(team: str) -> str:
        c = coaches.get(team)
        return (c.get("name") if isinstance(c, dict) else c) or ""

    lines = "\n".join(f"  - {t}: {_name(t)}" for t in relevant if _name(t))
    return ("=== OTHER PROGRAMS' HEAD COACHES (fictional, specific to THIS universe) ===\n"
            "When a story, post, or text refers to another program's head coach, use the EXACT name below "
            "for that team. NEVER name a real-life coach, even for a famous program.\n" + lines)


def reactive_grounding(dynasty: dict, year: int, week: int) -> str:
    """The authoritative facts PLUS the situation brief, for the `grounding`
    argument of reactive generators. Prepended to the user prompt, where a small
    model actually uses it (see llm._ground), so replies, texts, posts, and
    articles react to what just happened instead of drifting generic."""
    facts = grounding_facts(dynasty)
    fp = flashpoints(dynasty, year, week)
    return facts + ("\n\n" + fp if fp else "")


def is_season_open(dynasty: dict) -> bool:
    """True at the very start of a season (no games played yet), when news should
    be season-opening landscape coverage rather than game recaps."""
    season = dynasty.get("season", {}) or {}
    recent = (dynasty.get("schedule", {}) or {}).get("recent_results") or []
    return int(season.get("week", 0) or 0) <= 1 and not recent


def predecessor_coach(dynasty: dict) -> str | None:
    """The coach the user replaced, read from the program history (the most recent
    season not coached by the user)."""
    for h in dynasty.get("history") or []:
        if not h.get("user_coached"):
            return h.get("coach")
    return None


def season_landscape(dynasty: dict) -> str:
    """A grounded brief of where the program stands entering the season: the
    coaching situation (and whether the coach is brand new), last season and the
    recent history, preseason expectations, key returners, the recruiting class,
    and rivals. Used to steer the season-opening news."""
    t = dynasty.get("team", {}) or {}
    hc = t.get("head_coach", {}) or {}
    season = dynasty.get("season", {}) or {}
    rk = t.get("rankings", {}) or {}
    hist = dynasty.get("history") or []
    tenure = int(hc.get("tenure_years") or 1)

    lines = [f"SEASON LANDSCAPE, entering the {season.get('year')} season for {t.get('name')}:"]
    if tenure <= 1:
        pred = predecessor_coach(dynasty)
        lines.append(
            f"- {hc.get('name')} is in his FIRST SEASON as head coach"
            + (f", having taken over from {pred}" if pred else "")
            + ". A new era; make this a central storyline.")
    else:
        lines.append(
            f"- {hc.get('name')} enters year {tenure} as head coach"
            + (f", alma mater {hc.get('alma_mater')}" if hc.get("alma_mater") else "") + ".")
    if hc.get("hot_seat") is not None:
        lines.append(f"- Hot seat {hc.get('hot_seat')}/100; contract through {hc.get('contract_through')}.")
    if hist:
        last = hist[0]
        lines.append(
            f"- Last season ({last.get('year')}): {last.get('overall')}, {last.get('result', '')}"
            + (f", under {last.get('coach')}" if last.get("coach") else "") + ".")
        lines.append("- Recent history: " + "; ".join(
            f"{h.get('year')} {h.get('overall')}" + (f" (No. {h['final_rank']})" if h.get("final_rank") else "")
            for h in hist[:5]) + ".")
    pre = []
    if rk.get("cfp"):
        pre.append(f"No. {rk['cfp']} in the preseason playoff projection")
    if rk.get("ap"):
        pre.append(f"No. {rk['ap']} in the preseason AP poll")
    lines.append("- Preseason expectations: " + (", ".join(pre) if pre else "unranked entering the year") + ".")
    players = (dynasty.get("roster", {}) or {}).get("key_players") or []
    if players:
        lines.append("- Key returning players: " + ", ".join(
            f"{p.get('name')} ({p.get('position')})" for p in players[:4]) + ".")
    rec = dynasty.get("recruiting", {}) or {}
    if rec.get("class_rank_national"):
        lines.append(f"- Incoming recruiting class ranked No. {rec['class_rank_national']} nationally.")
    rivals = dynasty.get("rivals") or []
    if rivals:
        lines.append("- Rivals: " + ", ".join(r.get("name", "") for r in rivals[:3]) + ".")
    up = (dynasty.get("schedule", {}) or {}).get("upcoming") or {}
    if up.get("opponent"):
        lines.append(f"- Opens {'at home vs' if up.get('home') else 'on the road at'} {up['opponent']}.")
    return "\n".join(lines)


# --- the national brief ("what is happening across the sport RIGHT NOW") ----
# The program gets a rich flashpoints() digest (its last result, the coach's
# words, its live threads). National coverage had no equivalent: the writer saw
# only a static top-10 of names, so it drifted to "the picture is taking shape"
# filler. national_brief() is the national analog: a concrete, prioritized digest
# of the week's results and upsets, poll movement vs last week, the top of the
# polls, the projected playoff field, the Heisman race WITH numbers, the
# statistical leaders, and the coaching-carousel hot seats, all drawn from the
# data the Simulator already computes (the scoreboard, polls, stat board, and the
# coaching directory). Fed to the dedicated national news pass as grounding.
def _wl_pair(rec: Any) -> tuple[int, int]:
    try:
        w, l = str(rec).split("-")[:2]
        return int(w), int(l)
    except (ValueError, AttributeError):
        return 0, 0


def _coach_of(dynasty: dict, team: str | None) -> str | None:
    c = (dynasty.get("coaches") or {}).get(team or "")
    return (c.get("name") if isinstance(c, dict) else c) or None


def _team_label(dynasty: dict, name: str | None, rank: Any) -> str:
    """'No. 3 Ohio State Buckeyes (Owen Okeke)' -> the rank, team, and its FICTIONAL
    coach inline, so a small model writing the line has the right name in hand instead
    of reaching for a real-life coach."""
    base_name = f"No. {rank} {name}" if rank else (name or "")
    coach = _coach_of(dynasty, name)
    return base_name + (f" (coach {coach})" if coach else "")


def _rank_name(rank: Any, name: str | None) -> str:
    return f"No. {rank} {name}" if rank else (name or "")


def _prior_ap_ranks(year: int, week: int) -> dict[str, int]:
    """{team: AP rank} from the PRIOR week's archived snapshot, for poll movement.
    Empty before week 2 or when no prior snapshot exists. Lazy-imports pipeline
    (which reads JSON only, never generates) to avoid a load-order cycle."""
    if not week or week <= 1:
        return {}
    try:
        from .. import pipeline
        prior = pipeline.load_dynasty(year, week - 1)
    except Exception:
        return {}
    ranks: dict[str, int] = {}
    for r in ((prior.get("national") or {}).get("ap_top25") or []):
        if isinstance(r, dict) and r.get("team") and r.get("rank"):
            ranks[r["team"]] = r["rank"]
    return ranks


def _results_digest(dynasty: dict) -> list[str]:
    """This week's national results from the scoreboard, classified by
    newsworthiness (ranked clashes, upsets, thrillers), biggest first. Excludes
    the user's own game (national coverage is about the rest of the country)."""
    sb = (dynasty.get("national") or {}).get("scoreboard") or []
    scored = []
    for g in sb:
        if g.get("status") != "final" or g.get("user"):
            continue
        if g.get("home_score") is None or g.get("away_score") is None:
            continue
        home, away = g.get("home") or {}, g.get("away") or {}
        hs, as_ = g["home_score"], g["away_score"]
        win, lose, ws, ls = (home, away, hs, as_) if hs >= as_ else (away, home, as_, hs)
        wr, lr = win.get("rank"), lose.get("rank")
        margin = ws - ls
        upset = bool(lr) and (not wr or wr > lr + 4)
        if wr and lr:
            sig = 100 - (wr + lr)
        elif upset:
            sig = 80 - lr
        elif wr or lr:
            sig = 40 - (wr or lr or 25)
        else:
            sig = 10
        if margin <= 4:
            sig += 6
        scored.append((sig, win, lose, ws, ls, wr, lr, upset, margin))
    scored.sort(key=lambda x: -x[0])
    lines: list[str] = []
    for _sig, win, lose, ws, ls, wr, lr, upset, margin in scored[:7]:
        wn = _team_label(dynasty, win.get("name"), wr)
        ln = _team_label(dynasty, lose.get("name"), lr)
        score = f"{ws}-{ls}"
        if upset:
            lines.append(f"UPSET: {wn} ({win.get('record', '')}) beat {ln} {score}.")
        elif wr and lr:
            lines.append(f"{wn} beat {ln} {score}{' in a thriller' if margin <= 4 else ''} (ranked vs ranked).")
        else:
            lines.append(f"{wn} beat {ln} {score}.")
    return lines


def _slate_digest(dynasty: dict) -> list[str]:
    """When this week's games are not yet played (a fresh advance), the marquee
    matchups to preview, ranked-vs-ranked first. Excludes the user's own game."""
    sb = (dynasty.get("national") or {}).get("scoreboard") or []
    scored = []
    for g in sb:
        if g.get("status") == "final" or g.get("user"):
            continue
        home, away = g.get("home") or {}, g.get("away") or {}
        hr, ar = home.get("rank"), away.get("rank")
        if hr and ar:
            sig = 100 - (hr + ar)
        elif hr or ar:
            sig = 40 - (hr or ar or 25)
        else:
            sig = 5
        scored.append((sig, home, away, g.get("line"), bool(hr and ar)))
    scored.sort(key=lambda x: -x[0])
    lines: list[str] = []
    for _sig, home, away, line, both in scored[:5]:
        hn = _team_label(dynasty, home.get("name"), home.get("rank"))
        an = _team_label(dynasty, away.get("name"), away.get("rank"))
        lines.append(f"{an} at {hn}{' (ranked vs ranked)' if both else ''}" + (f", line {line}" if line else "") + ".")
    return lines


def _movement_lines(dynasty: dict, year: int, week: int, user: str | None) -> list[str]:
    """Poll movement against last week's archived AP top 25: risers, fallers, new
    entrants, and teams that dropped out. The user's team is left out (national
    coverage is about the rest of the country). Empty with no prior snapshot."""
    cur: dict[str, int] = {}
    for r in ((dynasty.get("national") or {}).get("ap_top25") or []):
        if isinstance(r, dict) and r.get("team") and r.get("rank") and r.get("team") != user:
            cur[r["team"]] = r["rank"]
    prior = {t: r for t, r in _prior_ap_ranks(year, week).items() if t != user}
    if not prior or not cur:
        return []
    risers, fallers, entered, dropped = [], [], [], []
    for team, rank in cur.items():
        if team in prior:
            delta = prior[team] - rank
            if delta >= 3:
                risers.append((delta, f"{team} up to No. {rank} (from No. {prior[team]})"))
            elif delta <= -3:
                fallers.append((-delta, f"{team} down to No. {rank} (from No. {prior[team]})"))
        else:
            entered.append((rank, f"{team} (No. {rank})"))
    for team, rank in prior.items():
        if team not in cur:
            dropped.append((rank, f"{team} (was No. {rank})"))
    risers.sort(key=lambda x: -x[0]); fallers.sort(key=lambda x: -x[0])
    entered.sort(key=lambda x: x[0]); dropped.sort(key=lambda x: x[0])
    lines: list[str] = []
    if risers:
        lines.append("Risen: " + ", ".join(t for _, t in risers[:4]) + ".")
    if fallers:
        lines.append("Fallen: " + ", ".join(t for _, t in fallers[:4]) + ".")
    if entered:
        lines.append("New in the top 25: " + ", ".join(t for _, t in entered[:4]) + ".")
    if dropped:
        lines.append("Fell out: " + ", ".join(t for _, t in dropped[:4]) + ".")
    return lines


def _hot_seat_lines(dynasty: dict, user: str | None, limit: int = 5) -> list[str]:
    """Other programs' coaches whose seat is genuinely warm (heat >= 60), hottest
    first, with their record and trend. Grounds carousel coverage in real fictional
    coaches who are actually struggling, instead of an invented name."""
    rows = []
    for team, c in (dynasty.get("coaches") or {}).items():
        if not isinstance(c, dict) or team == user or c.get("is_user"):
            continue
        heat = c.get("hot_seat")
        if heat is None or heat < 60:
            continue
        rows.append((heat, c))
    rows.sort(key=lambda x: -x[0])
    tnote = {"up": "heating up", "down": "cooling", "flat": "steady"}
    out = []
    for heat, c in rows[:limit]:
        note = tnote.get(c.get("trend"), "")
        out.append(f"{c.get('name')}, {c.get('team')} ({c.get('record', '')}), hot seat {heat}/100"
                   + (f", {note}" if note else "") + ".")
    return out


def national_brief(dynasty: dict, year: int, week: int) -> str:
    """The national analog of flashpoints(): a concrete, prioritized digest of the
    sport's state THIS week, so national stories cite real teams, scores, records,
    and stats instead of drifting to generic filler. Returns '' with no national
    data."""
    nat = dynasty.get("national") or {}
    if not nat:
        return ""
    user = (dynasty.get("team") or {}).get("name")
    blocks: list[str] = []

    # Before any games, there are no stats, Heisman standings, or records to cite. A
    # small model otherwise fabricates a season stat line in week 1 (a "25-TD Heisman
    # frontrunner" before kickoff), so say so plainly and drop the stat-driven blocks.
    season_open = is_season_open(dynasty)
    if season_open:
        blocks.append(
            "EARLY SEASON: the season has just kicked off. There are NO season statistics, "
            "NO Heisman standings, and NO win-loss records beyond 0-0 yet. Do NOT cite passing "
            "yards, touchdown totals, season stat lines, or Heisman frontrunners; cover the "
            "matchups, preseason expectations, and the polls only.")

    results = _results_digest(dynasty)
    if results:
        blocks.append("This week's results (lead with the biggest):\n" + "\n".join("  - " + r for r in results))
    else:
        slate = _slate_digest(dynasty)
        if slate:
            blocks.append("This week's marquee slate. THESE GAMES HAVE NOT BEEN PLAYED YET, they are "
                          "PREVIEWS: do NOT invent a score, a winner, or anything that happened in them. "
                          "Write forward-looking previews only:\n" + "\n".join("  - " + s for s in slate))

    moves = _movement_lines(dynasty, year, week, user)
    if moves:
        blocks.append("Poll movement vs last week:\n" + "\n".join("  - " + m for m in moves))

    ap = [r for r in (nat.get("ap_top25") or []) if r.get("team")]
    if ap:
        line = "Top of the AP poll: " + ", ".join(
            f"{r['rank']}. {r['team']} ({r.get('record', '')})" for r in ap[:8]) + "."
        undef = [r["team"] for r in ap if r.get("team") != user
                 and _wl_pair(r.get("record"))[0] > 0 and _wl_pair(r.get("record"))[1] == 0]
        if undef:
            line += " Still undefeated: " + ", ".join(undef[:6]) + "."
        blocks.append(line)

    cfp = [r for r in (nat.get("cfp_top12") or []) if r.get("team")]
    if cfp:
        blocks.append("Projected playoff field: " + ", ".join(f"{r['rank']} {r['team']}" for r in cfp[:12])
                      + ". The bubble is the teams seeded 10 to 12 and the next few just outside.")

    heis = [h for h in (nat.get("heisman_frontrunners") or []) if h.get("name")]
    if heis and not season_open:
        hl = [f"{h['name']} ({h.get('team', '')}, {h.get('position', '')})"
              + (f": {h['stat_line']}" if h.get("stat_line") else "") for h in heis[:4]]
        blocks.append("Heisman race:\n" + "\n".join("  - " + l for l in hl))

    leaders = nat.get("stat_leaders") or {}
    if leaders and not season_open:
        label = {"passing": "Passing", "rushing": "Rushing", "receiving": "Receiving", "sacks": "Sacks"}
        ll = []
        for key in ("passing", "rushing", "receiving", "sacks"):
            lst = leaders.get(key) or []
            if lst:
                p = lst[0]
                ll.append(f"{label[key]}: {p.get('name')} ({p.get('team', '')}) {p.get('stat_line', '')}".rstrip())
        if ll:
            blocks.append("National statistical leaders:\n" + "\n".join("  - " + l for l in ll))

    carousel = _hot_seat_lines(dynasty, user)
    if carousel:
        blocks.append("Coaching carousel watch (real hot seats this season; ground any carousel item in these "
                      "coaches, do not invent one):\n" + "\n".join("  - " + c for c in carousel))

    if not blocks:
        return ""
    return ("=== NATIONAL LANDSCAPE (authoritative; be specific, name the teams, scores, records, and stats; "
            f"do NOT recap {user or 'the user team'} here) ===\n" + "\n\n".join(blocks))


def _context_dynasty(dynasty: dict) -> dict:
    """The dynasty as embedded in the shared LLM context, trimmed to what a model
    needs to ground content. The raw save is ~280KB (85-player roster, the full
    136-team coaching directory, full poll tails, the whole schedule, the snap-by-
    snap play log), which on a small local model is both slow and easy to drown in.
    Modules read their data from the passed `dynasty` dict, NOT from this JSON, so
    trimming it only sharpens (and speeds) what the LLM sees. The curated essentials
    (KEY FACTS, the RIGHT NOW digest, the league-coaches block) are added separately.

    Dropped/trimmed here: the play-by-play, the deep bench (keep the rotation), the
    full coaching directory (surfaced compactly elsewhere), the poll tails and
    scoreboard, and the full game-by-game schedule (recent + upcoming carry it)."""
    d = dict(dynasty)
    lg = d.get("last_game")
    if isinstance(lg, dict) and "play_by_play" in lg:
        d["last_game"] = {k: v for k, v in lg.items() if k != "play_by_play"}
    roster = d.get("roster")
    if isinstance(roster, dict) and len(roster.get("key_players") or []) > 18:
        d["roster"] = {**roster, "key_players": roster["key_players"][:18]}
    d.pop("coaches", None)  # the league directory is huge; the coaches block covers it
    d.pop("budget", None)   # 45KB of NIL/budget detail the LLM never needs (read directly)
    rec = d.get("recruiting")
    if isinstance(rec, dict):
        tr = dict(rec)
        for k in ("targets", "commits"):
            if isinstance(tr.get(k), list) and len(tr[k]) > 12:
                tr[k] = tr[k][:12]
        d["recruiting"] = tr
    nat = d.get("national")
    if isinstance(nat, dict):
        tn = dict(nat)
        for k in ("ap_top25", "coaches_top25", "ap_receiving_votes", "coaches_receiving_votes"):
            if isinstance(tn.get(k), list):
                tn[k] = tn[k][:12]
        if isinstance(tn.get("scoreboard"), list):
            tn["scoreboard"] = tn["scoreboard"][:10]
        d["national"] = tn
    sched = d.get("schedule")
    if isinstance(sched, dict) and isinstance(sched.get("full"), list) and len(sched["full"]) > 8:
        d["schedule"] = {k: v for k, v in sched.items() if k != "full"}
    return d


def build_context(dynasty: dict, year: int, week: int, *, reactive: bool = True) -> str:
    """Cached system context: the dynasty state plus narrative memory.

    Leads with hard grounding rules and an authoritative KEY FACTS block so a
    model never substitutes real-world coaches, players, or results for a real
    team name (this is a fictional dynasty universe).

    `reactive` controls the user-program "RIGHT NOW" layer (the flashpoints digest
    and the coach's press-conference remarks). Leave it True for content ABOUT the
    user's program; set it False when expanding a NATIONAL story about other teams,
    so the user's result/presser/storylines do not bleed into it (a story about the
    SEC carousel must not turn into a Nebraska recap)."""
    narrative_text = narrative.render_context(year, up_to_week=week)
    # A local model truncates a long system context to its window (Ollama defaults to
    # ~2048 tokens), so the full dynasty JSON, which sits early in the system block, is
    # dropped before the model ever reads it: shipping it only wastes time and starves
    # the grounding. The compact blocks below (KEY FACTS, the RIGHT NOW digest, the
    # league coaches, the narrative) plus the grounding= prepended to the user prompt
    # carry everything the model needs, so omit the heavy JSON on the local path. Hosted
    # models (Anthropic) keep it: there it is cached cheaply and the window is huge.
    dynasty_block = ""
    if not _local_provider():
        dynasty_block = ("=== FULL DYNASTY STATE (JSON) ===\n"
                         + json.dumps(_context_dynasty(dynasty), indent=2) + "\n\n")
    t = dynasty.get("team", {}) or {}
    hc = (t.get("head_coach", {}) or {}).get("name", "the head coach")
    # The salient "react to this" digest, placed high (right after the facts and
    # before the heavy JSON) so a small model weights it instead of drowning it.
    fp = flashpoints(dynasty, year, week) if reactive else ""
    # Other programs' fictional coaches (so national coverage never invents a
    # real-life coach). Relevant for both program and national content.
    coaches_block = _league_coaches_block(dynasty)
    base_ctx = (
        "You are generating content for an immersive college football dynasty "
        "media companion. Follow these rules exactly:\n"
        "1. This is a FICTIONAL dynasty universe. The team names are real, but the "
        "coaches, players, records, rankings, recruits, and results are fictional "
        "and specific to THIS universe. They do not match real life.\n"
        "2. Use ONLY the names and facts provided below. NEVER use real-world "
        "coaches, players, results, or rankings for any team, even famous real "
        "programs. Do not rely on anything you know about these schools from "
        "outside this data.\n"
        f"3. The head coach of {t.get('name')} is {hc}. Refer to the coach only as "
        f"{hc}. Never name any other person, real or invented, as the coach.\n"
        "4. Never use dashes as punctuation. No em dashes, no en dashes, and no "
        "spaced hyphens used as dashes (like word - word). Use commas, periods, "
        "or parentheses. Hyphens only inside compound words and scores "
        "(for example top-15, 28-24, 7-2).\n"
        f"5. NEVER fabricate a direct quote from {hc}. You may quote {hc} word for "
        "word ONLY from things he actually said that are given to you below (his text "
        "messages with media and his post-game press conference remarks, if any are "
        f"present). When no such words are provided, do not put any quotation marks "
        f"around words attributed to {hc}: paraphrase or describe his position "
        "instead, or quote other people (players, coordinators, analysts, reporters). "
        f"Other people in this universe are fictional and may be quoted, but {hc} is "
        "the user and must never be quoted saying something he did not say.\n\n"
        f"=== KEY FACTS (authoritative, use these exact names) ===\n{grounding_facts(dynasty)}\n\n"
        + (fp + "\n\n" if fp else "")
        + (coaches_block + "\n\n" if coaches_block else "")
        + dynasty_block
        + f"=== {narrative_text} ==="
    )
    # The coach's PUBLIC post-game press-conference remarks are on the record, so
    # they belong in the shared context: any generator (news, recruiting, awards,
    # texts) may quote or reference them. Lazy import avoids a load-order cycle.
    from .. import directory
    # Only the most recent press conference (the latest game) is relevant to this
    # week's coverage, so quotes track the current game rather than a stale one.
    # Omitted for a national story (reactive=False) so the user's presser does not
    # bleed into a story about other teams.
    presser = directory.press_conference_block(year, coach_name=hc, up_to_week=week, max_pressers=1) if reactive else ""
    return base_ctx + ("\n\n" + presser if presser else "")


def news_context(dynasty: dict, year: int, week: int, *, reactive: bool = True) -> str:
    """The cached system context for the news generators: the shared context (which
    already includes the public press conference) plus a transcript of the coach's
    PRIVATE conversations with media members, so articles can also quote what he
    told a reporter directly. With `reactive=False` (a national story about other
    teams) the user-program layers are dropped so they cannot bleed in."""
    from .. import directory  # local import keeps base free of a load-order dependency
    ctx = build_context(dynasty, year, week, reactive=reactive)
    if not reactive:
        return ctx
    coach = ((dynasty.get("team") or {}).get("head_coach") or {}).get("name") or "The head coach"
    block = directory.media_interviews_block(year, coach_name=coach)
    return ctx + ("\n\n" + block if block else "")


def llm_available() -> bool:
    return llm.available()


def _local_provider() -> bool:
    """True when generation is pointed at a local (Ollama/OpenAI-compatible) model, so
    the context can be trimmed to fit a small window (see build_context)."""
    try:
        from .. import llm_settings
        return llm_settings.provider() == "local"
    except Exception:
        return False
