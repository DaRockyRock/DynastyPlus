"""Persistent phone message threads.

Conversations the coach has in the in-app phone (recruits, staff, players,
media) used to live only in the browser's memory, so they vanished on every
reload. They are now stored per season at data/messages/<year>.json, mirroring
the narrative and budget stores, so chats survive restarts.

A thread is a flat list of message items in display order. Each item is one of:
  * {"from": "me" | "them", "text": "..."}            a chat bubble
  * {"from": "me", "kind": "receipt", "effect": {...}} an NIL/action receipt

An inbound (unprompted) text the coach has not yet read carries "unread": true
on the bubble until he opens that conversation (see mark_read).

Threads are keyed by contact id and scoped to the season (year), so a
conversation carries across the weeks of a dynasty. An "inbound_log" map
({week: [contact_id, ...]}) records which contacts have already texted the coach
first in a given week, so re-running the weekly pipeline never doubles up a text.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from . import dynasty_paths

_lock = threading.Lock()


def _stamped(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tag each item with a wall-clock `ts` (seconds) if it lacks one, so the UI
    can sort conversations by most recent activity. One stamp per batch keeps the
    items in their appended order."""
    now = time.time()
    out = []
    for it in items:
        if isinstance(it, dict) and "ts" not in it:
            it = {**it, "ts": now}
        out.append(it)
    return out


def _path(year: int):
    return dynasty_paths.sub("messages") / f"{year}.json"


def _empty(year: int) -> dict[str, Any]:
    return {"year": year, "threads": {}}


def _read(year: int) -> dict[str, Any]:
    path = _path(year)
    if not path.exists():
        return _empty(year)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("threads"), dict):
            return _empty(year)
        return data
    except (OSError, ValueError):
        return _empty(year)


def _write(year: int, data: dict[str, Any]) -> None:
    try:
        with _path(year).open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def threads(year: int) -> dict[str, list[dict[str, Any]]]:
    """All conversation threads for a season, keyed by contact id."""
    return _read(year).get("threads", {})


def thread(year: int, contact_id: str) -> list[dict[str, Any]]:
    """One contact's conversation, oldest message first."""
    return threads(year).get(contact_id, [])


def append(year: int, contact_id: str, items: list[dict[str, Any]]) -> None:
    """Append message items to a contact's thread and persist."""
    if not contact_id or not items:
        return
    with _lock:
        data = _read(year)
        store = data.setdefault("threads", {})
        store.setdefault(contact_id, []).extend(_stamped(items))
        _write(year, data)


def deliver_inbound(year: int, week: int, contact_id: str, items: list[dict[str, Any]],
                    *, key: str | None = None) -> bool:
    """Append unprompted inbound items to a thread, deduped two ways.

    The `key` guard (the week for the weekly pass, a statement id for a world,
    reaction cascade) stops the SAME source re-delivering the same thing. On top of
    that, a per-week cap allows each contact at most ONE unprompted text per week
    across ALL sources, so a player never piles up several texts about the same news
    in one week (the weekly pass, the next pass, and a cascade off the coach's own
    replies were each delivering separately).

    Returns True if delivered, False if this contact already has a text under the
    key OR has already sent an unprompted text this week.
    """
    if not contact_id or not items:
        return False
    log_key = key if key is not None else str(week)
    with _lock:
        data = _read(year)
        log = data.setdefault("inbound_log", {})
        delivered = log.setdefault(log_key, [])
        if contact_id in delivered:
            return False
        week_seen = log.setdefault(f"wk:{week}", [])  # one unprompted text per person per week
        if contact_id in week_seen:
            return False
        store = data.setdefault("threads", {})
        store.setdefault(contact_id, []).extend(_stamped(items))
        delivered.append(contact_id)
        week_seen.append(contact_id)
        _write(year, data)
        return True


def mark_reply_unread(year: int, contact_id: str) -> int:
    """Mark the most recent incoming reply (the trailing run of 'them' bubbles,
    back to the coach's last message or receipt) as unread, so a reply that landed
    while the coach was not looking persists as a notification across reloads and
    week advances. Returns how many bubbles were marked."""
    if not contact_id:
        return 0
    with _lock:
        data = _read(year)
        thread = data.get("threads", {}).get(contact_id, [])
        marked = 0
        for item in reversed(thread):
            if item.get("from") != "them":
                break  # stop at the coach's last message / action receipt
            if not item.get("unread"):
                item["unread"] = True
            marked += 1
        if marked:
            _write(year, data)
        return marked


def mark_read(year: int, contact_id: str) -> int:
    """Clear the unread flag on every bubble in a contact's thread (the coach
    opened the conversation). Returns how many bubbles were marked read."""
    if not contact_id:
        return 0
    with _lock:
        data = _read(year)
        thread = data.get("threads", {}).get(contact_id, [])
        cleared = 0
        for item in thread:
            if item.pop("unread", None):
                cleared += 1
        if cleared:
            _write(year, data)
        return cleared


def unread_counts(year: int) -> dict[str, int]:
    """Unread inbound count per contact id (only threads with unread bubbles)."""
    out: dict[str, int] = {}
    for cid, thread in threads(year).items():
        n = sum(1 for item in thread if item.get("unread"))
        if n:
            out[cid] = n
    return out
