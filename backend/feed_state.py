"""Persistent social-feed state.

The Feed itself (the timeline of posts) is generated content cached per week by
the `feed` module, like every other module. What lives HERE is the small slice of
state the coach creates by interacting with it:

  * which posts he has liked (the only interactive control in the Feed; read +
    like, no replying or composing)
  * how far through the Feed he has read, per week, so an unseen badge can show
    how many posts arrived that he has not looked at yet

Stored per season at data/feed/<year>.json, mirroring the message store. Likes are
keyed by post id; post ids are deterministic (see modules/feed.py), so a like
survives a regeneration of the week's timeline.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from . import dynasty_paths

_lock = threading.Lock()


def _path(year: int):
    return dynasty_paths.sub("feed") / f"{year}.json"


def _empty(year: int) -> dict[str, Any]:
    return {"year": year, "likes": {}, "seen": {}}


def _read(year: int) -> dict[str, Any]:
    path = _path(year)
    if not path.exists():
        return _empty(year)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return _empty(year)
        base = _empty(year)
        base.update(data)
        if not isinstance(base.get("likes"), dict):
            base["likes"] = {}
        if not isinstance(base.get("seen"), dict):
            base["seen"] = {}
        return base
    except (OSError, ValueError):
        return _empty(year)


def _write(year: int, data: dict[str, Any]) -> None:
    try:
        with _path(year).open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def state(year: int) -> dict[str, Any]:
    """The coach's feed state for a season: liked post ids and the per-week seen
    marker. Surfaced to the UI so it can render filled hearts and the unseen
    badge over the freshly generated timeline."""
    data = _read(year)
    return {"likes": data.get("likes", {}), "seen": data.get("seen", {})}


def liked(year: int) -> dict[str, bool]:
    """Map of liked post id -> True for a season."""
    return _read(year).get("likes", {})


def toggle_like(year: int, post_id: str) -> bool:
    """Flip the like on a post. Returns the new liked state (True = now liked)."""
    if not post_id:
        return False
    with _lock:
        data = _read(year)
        likes = data.setdefault("likes", {})
        now_liked = not likes.get(post_id)
        if now_liked:
            likes[post_id] = True
        else:
            likes.pop(post_id, None)
        _write(year, data)
        return now_liked


def mark_seen(year: int, week: int) -> None:
    """Record that the coach has read the Feed through this week (clears the
    unseen badge for it). Stamps the wall-clock time he last looked."""
    with _lock:
        data = _read(year)
        data.setdefault("seen", {})[str(week)] = time.time()
        _write(year, data)


def seen_at(year: int, week: int) -> float | None:
    """When the coach last marked this week's Feed seen, or None if never."""
    ts = _read(year).get("seen", {}).get(str(week))
    return ts if isinstance(ts, (int, float)) else None
