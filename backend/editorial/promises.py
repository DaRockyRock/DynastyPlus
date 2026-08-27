"""Promise tracking: the world remembers what the coach told people.

When the user texts a player or recruit a commitment ("the starting job is
yours", "we'll get you the NIL"), it is extracted with the VERBATIM span (regex
on the actual message, so a weak classifier can never invent a promise) and
remembered. Later, when the simulation makes it checkable (the depth chart posts,
NIL is recorded), the promise is tested; if it was broken, the person texts the
coach about it ("coach you told me i'd start") and trust drops. A phone that
remembers is the deepest immersion mechanic in the design.

Persisted per dynasty+year. Confrontation delivery is keyed by promise id, so it
fires exactly once.
"""
from __future__ import annotations

import json
import re
import threading
from typing import Any

from .. import dynasty_paths

_lock = threading.Lock()

# High-precision commitment patterns. Each is anchored on coach-commitment phrasing
# so ordinary chatter ("you'll start to see improvement") does not trip it. The
# matched text IS the stored span (verbatim from the message).
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("playing_time", re.compile(
        r"\b(?:you'?ll|you will|i'?ll|we'?ll|i promise(?:\s+you)?)\b[^.?!]{0,40}"
        r"\b(?:start(?:er|ing)?|starting (?:job|role|spot)|win the job|qb1|on the field early)\b",
        re.IGNORECASE)),
    ("playing_time", re.compile(
        r"\b(?:the (?:starting )?job is yours|you'?re (?:my|our|the) (?:guy|starter)|"
        r"day one starter)\b", re.IGNORECASE)),
    ("nil", re.compile(
        r"\b(?:we'?ll|i'?ll|you'?ll get|we will)\b[^.?!]{0,40}"
        r"\b(?:nil|the bag|paid|the money|the deal|the collective|taken care of)\b", re.IGNORECASE)),
    ("visit", re.compile(
        r"\b(?:i'?ll|we'?ll)\b[^.?!]{0,40}"
        r"\b(?:official visit|get you (?:on|out|down|up) (?:campus|here|to campus)|set up (?:a|the) visit)\b",
        re.IGNORECASE)),
]


def _path(year: int):
    return dynasty_paths.sub("editorial") / f"{year}_promises.json"


def _read(year: int) -> dict[str, Any]:
    p = _path(year)
    if not p.exists():
        return {"year": year, "promises": []}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("promises"), list) else {"year": year, "promises": []}
    except (OSError, ValueError):
        return {"year": year, "promises": []}


def _write(year: int, data: dict[str, Any]) -> None:
    try:
        _path(year).write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass


def scan(contact: dict | None, message: str, year: int, week: int) -> dict | None:
    """Extract a commitment from the coach's outbound text and remember it. Returns
    the stored promise, or None. Only fires for players/recruits (not media/staff)."""
    if not contact or not message:
        return None
    cat = (contact.get("category") or "").lower()
    if cat not in ("players", "recruits"):
        return None
    for kind, rx in _PATTERNS:
        m = rx.search(message)
        if not m:
            continue
        span = m.group(0).strip()
        if span.lower() not in message.lower():     # verbatim guard (always true for regex, kept explicit)
            continue
        cid = contact.get("id") or contact.get("name")
        pid = f"promise:{cid}:{kind}:{week}"
        with _lock:
            data = _read(year)
            if any(p["id"] == pid for p in data["promises"]):
                return None
            promise = {"id": pid, "contact_id": cid, "contact_name": contact.get("name"),
                       "is_recruit": cat == "recruits", "kind": kind, "span": span,
                       "made_week": week, "status": "open"}
            data["promises"].append(promise)
            _write(year, data)
        return promise
    return None


def _starter(dynasty: dict, name: str) -> bool | None:
    """True/False if the named player is/ isn't a starter; None if not on the roster
    yet (a recruit who has not enrolled, so the promise is not testable)."""
    for p in (dynasty.get("roster") or {}).get("key_players") or []:
        if (p.get("name") or "").lower() == (name or "").lower():
            slot = (p.get("depth_chart_slot") or "").lower()
            return ("starting" in slot or "starter" in slot
                    or (p.get("role") or "").lower() == "starter")
    return None


def _test(promise: dict, dynasty: dict) -> str | None:
    """'honored' | 'broken' | None (not yet testable)."""
    if promise["kind"] == "playing_time":
        st = _starter(dynasty, promise["contact_name"])
        if st is None:
            return None
        return "honored" if st else "broken"
    return None       # nil / visit not tested in this slice


def _confrontation(promise: dict) -> list[str]:
    span = promise["span"]
    return [f"coach you told me {span.lower()}. im not even on the first team rn. whats the deal?",
            "i need to know where i actually stand here"]


def check_due(dynasty: dict, year: int, week: int):
    """Test open promises against the save; deliver a confrontation text for any that
    are broken (keyed once), mark honored ones. Returns the broken promises. Lazy
    import of msg_store keeps the editorial package import-light."""
    from .. import messages as msg_store
    broken: list[dict] = []
    with _lock:
        data = _read(year)
        for p in data["promises"]:
            if p["status"] != "open":
                continue
            outcome = _test(p, dynasty)
            if outcome == "honored":
                p["status"] = "honored"
            elif outcome == "broken":
                p["status"] = "broken"
                broken.append(p)
        _write(year, data)
    for p in broken:
        items = [{"from": "them", "text": t, "unread": True} for t in _confrontation(p)]
        try:
            msg_store.deliver_inbound(year, week, p["contact_id"], items, key=p["id"])
        except Exception:
            pass
    return broken
