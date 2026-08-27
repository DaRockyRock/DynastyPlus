"""The rumor lifecycle: insider claims that resolve, and reporters who own them.

A carousel report ("sources say Coach X is on his way out") is a CLAIM: attributed
to a persona, carrying a confidence, and tracked. Weeks later the simulation
settles it (the coach is replaced, or he is not), and the engine fires a
resolution beat (vindication or a quiet correction) and moves the reporter's
credibility. That is what makes the insider ecosystem feel real instead of
decorative: reliability is something you watch happen over a season, and a
burned reporter carries the scar into next week's framing.

Persisted per dynasty+year. Resolution is checked against the SAVE (what the sim
actually did), never the hidden roll, so the world is the source of truth.
"""
from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from .. import dynasty_paths
from . import personas

_lock = threading.Lock()

# Heat at which a coach's seat is a genuine, reportable rumor (below this it is
# just background pressure, not a "he is out" claim).
_CLAIM_HEAT = 70
# Weeks before a still-unfulfilled "he is out" claim is judged wrong.
_REFUTE_AFTER = 3


def _path(year: int):
    return dynasty_paths.sub("editorial") / f"{year}_claims.json"


def _read(year: int) -> dict[str, Any]:
    p = _path(year)
    if not p.exists():
        return {"year": year, "claims": []}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("claims"), list) else {"year": year, "claims": []}
    except (OSError, ValueError):
        return {"year": year, "claims": []}


def _write(year: int, data: dict[str, Any]) -> None:
    try:
        _path(year).write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass


def _resolution_beat(claim: dict, corroborated: bool) -> dict[str, Any]:
    """A follow-up insider report when a prior claim settles."""
    rep, coach = claim["persona_name"], claim["coach"]
    if corroborated:
        head = f"Confirmed: {coach} is out, as {rep} first reported"
        body = (f"The move {rep} flagged weeks ago is now official. {coach} is out at "
                f"{claim['team']}. The early call holds up.")
        status = "corroborated"
    else:
        head = f"{rep}'s report on {coach} has not materialized"
        body = (f"Weeks after the rumor surfaced, {coach} remains at {claim['team']} with the "
                f"heat cooling. The reporting has not panned out.")
        status = "refuted"
    return {"outlet": claim.get("outlet"), "reporter": rep, "reliability": claim.get("confidence", 70),
            "category": "Coaching carousel", "headline": head, "dek": "A carousel rumor settles.",
            "body": body, "claim": claim["text"], "confidence": claim.get("confidence", 70),
            "credibility": claim.get("confidence", 70), "status": status,
            "timestamp": "today", "day_slot": "Tue", "source": "claim"}


def render_insider(claim: dict) -> dict[str, Any]:
    """A live claim rendered as an attributed, hedged insider report."""
    coach = claim["coach"]
    return {"outlet": claim.get("outlet"), "reporter": claim["persona_name"],
            "reliability": claim.get("confidence", 70), "category": "Coaching carousel",
            "headline": f"Sources: {coach}'s seat is hot at {claim['team']}",
            "dek": "An insider read on a heating-up situation.",
            "body": (f"People around {claim['team']} describe mounting pressure on {coach}. "
                     f"{claim['persona_name']} reports a change is in play before the season is out. "
                     "Nothing is final, but the temperature is rising."),
            "claim": claim["text"], "confidence": claim.get("confidence", 70),
            "credibility": claim.get("confidence", 70), "status": "developing",
            "timestamp": "today", "day_slot": "Tue", "source": "claim"}


def for_week(dynasty: dict, year: int, week: int, season_open: bool,
             registry=None) -> dict[str, list[dict]]:
    """Resolve old claims and open new ones for this week's genuine hot seats.
    Returns {"live": [...], "resolutions": [...]} as insider-shaped dicts. No claims
    in the preseason (a rumor cannot exist before any games). Idempotent per week."""
    if season_open:
        return {"live": [], "resolutions": []}
    preg = registry or personas.build()
    coaches = dynasty.get("coaches") or {}
    resolutions: list[dict] = []
    with _lock:
        data = _read(year)
        claims = data["claims"]
        by_team_live = {c["team"]: c for c in claims if c["status"] == "live"}

        # 1) resolve live claims against the save (what the sim actually did)
        for c in claims:
            if c["status"] != "live":
                continue
            coach_now = (coaches.get(c["team"]) or {}).get("name")
            base = int(c.get("confidence", 75))   # the reporter's credibility at the time
            if coach_now and coach_now != c["coach"]:          # the coach is gone -> it happened
                c.update(status="corroborated", resolved_week=week)
                personas.adjust_credibility(c["persona_id"], +6, base=base)
                resolutions.append(_resolution_beat(c, True))
            elif week - c["week"] >= _REFUTE_AFTER:             # gave it time, still there
                c.update(status="refuted", resolved_week=week)
                personas.adjust_credibility(c["persona_id"], -8, base=base)
                resolutions.append(_resolution_beat(c, False))

        # 2) open new claims for genuine hot seats not already under a live claim
        hot = sorted(((cc.get("hot_seat", 0), team, cc) for team, cc in coaches.items()
                      if isinstance(cc, dict) and not cc.get("is_user")
                      and (cc.get("hot_seat") or 0) >= _CLAIM_HEAT and cc.get("name")), reverse=True)
        for heat, team, cc in hot[:3]:
            if team in by_team_live:
                continue
            card = personas.byline_for("national", f"claim:{team}", preg)
            # hidden truth: a higher seat and a credible reporter make the rumor more
            # likely to actually pan out (recorded for analysis; resolution uses the sim).
            roll = int(hashlib.sha1(f"{year}:{team}:{week}:truth".encode()).hexdigest(), 16) % 100
            truth = roll < min(90, heat + (card.credibility - 70 if card else 0))
            claim = {"id": f"claim:{team}:{week}", "team": team, "coach": cc["name"], "week": week,
                     "persona_id": card.id if card else "", "persona_name": card.name if card else "An insider",
                     "outlet": card.outlet if card else None,
                     "text": f"{cc['name']} will be out at {team} before the season ends.",
                     "confidence": card.credibility if card else 70, "truth": truth, "status": "live"}
            claims.append(claim)
            by_team_live[team] = claim
        _write(year, data)
        live = [c for c in claims if c["status"] == "live"]
    return {"live": live, "resolutions": resolutions}
