"""Persistent world-reaction log.

When the coach says something the world can hear (a media text, a presser
answer, or a leak out of a private conversation), the reaction engine
(`modules/world.py`) judges it and, when it is newsworthy, spins up a cascade:
a reporter breaks it, other accounts react, articles get filed, and people text
the coach. Every one of those reactions is recorded HERE as an append-only
event, so the cascade is durable, survives a full week re-roll of the feed/news,
and can be threaded (a reaction `reacts_to` the event it answers).

This store is to the reaction engine what `messages.py` is to the phone and
`feed_state.py` is to the timeline: the small slice of durable state a feature
owns, kept per season at data/world/<year>.json.

An event is:
  {
    "id":        stable, deterministic id (so re-firing the same statement and
                 re-merging into the feed are both no-ops),
    "type":      "coach_statement" | "tweet" | "quote" | "article" | "inbound_text",
    "week":      the week it happened on,
    "ts":        wall-clock creation time (orders events, drives recency),
    "tier":      0..3 newsworthiness of the statement that spawned it,
    "reacts_to": the id of the event this one answers, or null,
    "payload":   type-specific. For "tweet"/"quote" it is a ready-to-render feed
                 post (the feed module and the engine both render events the same
                 way through `merge_feed_posts`).
  }

A monotonic `version` counter is bumped on every append so the frontend can
notice (via /api/state) that the world reacted and refresh the affected surfaces
without a full generation pass.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from . import dynasty_paths

_lock = threading.Lock()

# Event types whose payload is a feed post (so they render on the timeline).
_FEED_TYPES = {"tweet", "quote"}


def _path(year: int):
    return dynasty_paths.sub("world") / f"{year}.json"


def _empty(year: int) -> dict[str, Any]:
    return {"year": year, "version": 0, "events": []}


def _read(year: int) -> dict[str, Any]:
    path = _path(year)
    if not path.exists():
        return _empty(year)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("events"), list):
            return _empty(year)
        base = _empty(year)
        base.update(data)
        return base
    except (OSError, ValueError):
        return _empty(year)


def _write(year: int, data: dict[str, Any]) -> None:
    try:
        with _path(year).open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def load(year: int) -> dict[str, Any]:
    return _read(year)


def events(year: int) -> list[dict[str, Any]]:
    return _read(year).get("events", [])


def version(year: int) -> int:
    """A monotonic counter bumped on every append. Surfaced to the frontend so it
    can tell the world reacted and refresh the feed/messages, with no new state to
    diff. Returns 0 when nothing has happened yet this season."""
    return int(_read(year).get("version", 0) or 0)


def add_events(year: int, new_events: list[dict[str, Any]]) -> int:
    """Append events that are not already present (dedup by id, so re-firing an
    identical statement is a no-op). Stamps a wall-clock `ts` on any event missing
    one and bumps the version when anything was actually added. Returns the new
    version."""
    if not new_events:
        return version(year)
    now = time.time()
    with _lock:
        data = _read(year)
        have = {e.get("id") for e in data["events"]}
        added = 0
        for ev in new_events:
            eid = ev.get("id")
            if not eid or eid in have:
                continue
            if "ts" not in ev:
                ev = {**ev, "ts": now}
            data["events"].append(ev)
            have.add(eid)
            added += 1
        if added:
            data["version"] = int(data.get("version", 0) or 0) + 1
            _write(year, data)
        return int(data.get("version", 0) or 0)


def events_for_week(year: int, week: int, *, type: str | None = None) -> list[dict[str, Any]]:
    out = [e for e in events(year) if e.get("week") == week]
    if type is not None:
        out = [e for e in out if e.get("type") == type]
    return out


def feed_posts(year: int, week: int) -> list[dict[str, Any]]:
    """The week's tweet/quote events rendered as feed posts. Each event's payload
    is already a feed post; we just stamp the event id onto it so likes and dedup
    key off a stable id."""
    posts: list[dict[str, Any]] = []
    for e in events_for_week(year, week):
        if e.get("type") not in _FEED_TYPES:
            continue
        post = dict(e.get("payload") or {})
        post["id"] = e["id"]
        posts.append(post)
    return posts


def merge_feed_posts(base_posts: list[dict[str, Any]], year: int, week: int) -> list[dict[str, Any]]:
    """Fold the week's coach-caused tweet events into a list of feed posts, deduped
    by id and sorted newest first (by the feed's synthetic `ts`). Used by both the
    feed module (at generation time, so reactions survive a re-roll) and the engine
    (to patch the already-cached timeline the moment a reaction lands)."""
    by_id: dict[str, dict[str, Any]] = {p["id"]: p for p in base_posts if p.get("id")}
    for post in feed_posts(year, week):
        by_id[post["id"]] = post
    merged = list(by_id.values())
    merged.sort(key=lambda p: -(p.get("ts") or 0))
    return merged


# --- news (articles + top stories) ---------------------------------------
def news_articles(year: int, week: int) -> list[tuple[str, dict[str, Any]]]:
    """The week's coach-caused articles as (scope, article) pairs. Each article is a
    full news_feed article object (with its reader `detail`) carrying a stable id."""
    out: list[tuple[str, dict[str, Any]]] = []
    for e in events_for_week(year, week, type="article"):
        p = e.get("payload") or {}
        art = dict(p.get("article") or {})
        art.setdefault("id", e["id"])
        out.append((p.get("scope") or "program", art))
    return out


def merge_news(content: dict[str, Any], year: int, week: int) -> dict[str, Any]:
    """Fold coach-caused articles into a news_feed payload, prepending each to its
    scope bucket (the user's program, or national), deduped by id. Used by the
    news_feed module at generation time and by the engine to patch the cache."""
    if not isinstance(content, dict):
        return content
    for scope, art in news_articles(year, week):
        bucket = scope if scope in ("national", "program") else "program"
        lst = content.get(bucket)
        if not isinstance(lst, list):
            lst = content[bucket] = []
        if any(isinstance(a, dict) and a.get("id") == art.get("id") for a in lst):
            continue
        lst.insert(0, art)
    return content


def top_story_items(year: int, week: int) -> list[dict[str, Any]]:
    """The week's coach-caused top-stories slider items, each carrying a stable id."""
    out: list[dict[str, Any]] = []
    for e in events_for_week(year, week, type="top_story"):
        story = dict((e.get("payload") or {}).get("story") or {})
        story.setdefault("id", e["id"])
        out.append(story)
    return out


def merge_top_stories(stories: list[dict[str, Any]], year: int, week: int,
                      limit: int = 6) -> list[dict[str, Any]]:
    """Prepend coach-caused top stories (a blockbuster leads the slider), deduped by
    id, capped so the slider stays tight."""
    items = top_story_items(year, week)
    if not items:
        return stories
    have = {s.get("id") for s in stories if isinstance(s, dict)}
    fresh = [s for s in items if s.get("id") not in have]
    return (fresh + list(stories))[:limit]
