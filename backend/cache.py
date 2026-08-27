"""Per-week content cache.

Generated content is cached per (season, week, module) so advancing back
through weeks shows consistent historical content and the frontend can request
a single module without rerunning the whole pipeline. Cache lives on disk as
JSON under data/cache/.
"""
from __future__ import annotations

import json
from typing import Any

from . import dynasty_paths


def _key(year: int, week: int) -> str:
    return f"{year}_wk{week:02d}"


def _dir():
    return dynasty_paths.sub("cache")  # data/dynasties/<id>/cache


def _path(year: int, week: int):
    return _dir() / f"{_key(year, week)}.json"


def _read(year: int, week: int) -> dict[str, Any]:
    path = _path(year, week)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _write(year: int, week: int, data: dict[str, Any]) -> None:
    try:
        with _path(year, week).open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def get_module(year: int, week: int, module: str) -> Any | None:
    """Return cached content for a module, or None if not cached."""
    return _read(year, week).get(module)


def set_module(year: int, week: int, module: str, content: Any) -> None:
    data = _read(year, week)
    data[module] = content
    _write(year, week, data)


def get_week(year: int, week: int) -> dict[str, Any]:
    """All cached modules for a week."""
    return _read(year, week)


def clear_module(year: int, week: int, module: str) -> None:
    data = _read(year, week)
    data.pop(module, None)
    _write(year, week, data)


def clear_week(year: int, week: int) -> None:
    path = _path(year, week)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def clear_all() -> None:
    """Drop every cached week. Reserved for a full reset; routine invalidations
    (settings/customization saves) use clear_current_week so the dynasty archive
    of past weeks is not wiped."""
    for path in _dir().glob("*.json"):
        try:
            path.unlink()
        except OSError:
            pass


def clear_current_week() -> None:
    """Drop only the cache for the week the app is currently on. Used when LLM
    settings or customization change: the live week regenerates with the new
    connection/edits on the next request, while previously generated weeks stay
    intact so the dynasty archive is preserved."""
    try:
        from . import pipeline  # local import: pipeline imports cache
        ptr = pipeline.current_pointer()
        clear_week(ptr["year"], ptr["week"])
    except Exception:
        pass


def list_cached_weeks() -> list[dict[str, int]]:
    """Weeks that have any cached content, newest first."""
    out: list[dict[str, int]] = []
    for path in _dir().glob("*.json"):
        stem = path.stem  # e.g. 2026_wk10
        try:
            year_s, wk_s = stem.split("_wk")
            out.append({"year": int(year_s), "week": int(wk_s)})
        except ValueError:
            continue
    out.sort(key=lambda r: (r["year"], r["week"]), reverse=True)
    return out
