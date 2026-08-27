"""The companion inbox: the write-back channel from Dynasty+ to the Simulator.

Dynasty+ has no authority over game data (NIL/budget lives in the Simulator), so
when the coach takes an action the game would record (an NIL offer from the
phone, a recruiting action, a budget reallocation), Dynasty+ APPENDS it here as
an intent. The Simulator DRAINS the inbox at the start of each advance, before
the recruiting cycle reads the coach's spend, and applies each pending action
through the budget engine, then marks it applied. It also drains on demand when
its own watcher sees the file change, so the effect shows up without waiting for
the next week.

One JSON document at config.INBOX_PATH:
    {"version": 1, "applied_through": "<id>", "actions": [ {action}, ... ]}
Each action: {id, ts, year, week, applied, kind, ...kind-specific fields}.

Append-only from Dynasty+; the Simulator only flips `applied` and bumps
`applied_through`. A cross-process file lock guards the read-modify-write so the
two apps never clobber each other, and writes are atomic (temp + os.replace).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from . import config

_PATH = Path(config.INBOX_PATH)
_LOCK_PATH = Path(str(config.INBOX_PATH) + ".lock")
_TMP_PATH = Path(str(config.INBOX_PATH) + ".tmp")
_thread_lock = threading.Lock()

# The action kinds the Simulator knows how to apply (1:1 with budget mutations).
VALID_KINDS = ("nil_offer", "recruiting_action", "allocate")


@contextmanager
def _file_lock():
    """Best-effort cross-process exclusive lock around read-modify-write. Falls
    back to the in-process thread lock alone where fcntl is unavailable."""
    try:
        import fcntl
    except Exception:  # pragma: no cover - non-POSIX
        fcntl = None
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fh = open(_LOCK_PATH, "w")
    try:
        if fcntl is not None:
            fcntl.flock(fh, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if fcntl is not None:
                fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()


def _empty() -> dict[str, Any]:
    return {"version": 1, "applied_through": None, "actions": []}


def _read() -> dict[str, Any]:
    if not _PATH.exists():
        return _empty()
    try:
        with _PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError
        data.setdefault("version", 1)
        data.setdefault("applied_through", None)
        data.setdefault("actions", [])
        return data
    except (OSError, ValueError):
        return _empty()


def _write(data: dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    with _TMP_PATH.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(_TMP_PATH, _PATH)


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def append(action: dict[str, Any]) -> dict[str, Any]:
    """Queue a coach action (Dynasty+ side). Stamps id/ts/applied and persists."""
    kind = action.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(f"unknown inbox action kind: {kind}")
    record = dict(action)
    record["id"] = uuid.uuid4().hex
    record["ts"] = _now()
    record["applied"] = False
    with _thread_lock, _file_lock():
        data = _read()
        data["actions"].append(record)
        _write(data)
    return record


def pending(year: int | None = None) -> list[dict[str, Any]]:
    """Un-applied actions, optionally filtered to one season."""
    out = [a for a in _read()["actions"] if not a.get("applied")]
    if year is not None:
        out = [a for a in out if a.get("year") == year]
    return out


def pending_count(year: int | None = None) -> int:
    return len(pending(year))


def all_actions() -> list[dict[str, Any]]:
    return list(_read()["actions"])


def drain(year: int, current_week: int,
          appliers: dict[str, Callable[[dict[str, Any]], Any]]) -> list[dict[str, Any]]:
    """Apply pending actions for `year` whose week <= current_week (Simulator
    side). `appliers` maps each kind to a function taking the action dict. Marks
    each applied, bumps applied_through, and returns the applied actions (each
    with the applier's `effect`). Idempotent: already-applied actions are skipped,
    so re-draining is safe."""
    applied: list[dict[str, Any]] = []
    with _thread_lock, _file_lock():
        data = _read()
        for a in data["actions"]:
            if a.get("applied"):
                continue
            if a.get("year") != year:
                continue
            if int(a.get("week", 0)) > current_week:
                continue
            fn = appliers.get(a.get("kind"))
            if fn is None:
                continue
            try:
                effect = fn(a)
            except Exception as exc:  # keep draining the rest; record the failure
                a["error"] = str(exc)
                continue
            a["applied"] = True
            a["applied_at"] = _now()
            data["applied_through"] = a["id"]
            applied.append({**a, "effect": effect})
        if applied:
            _write(data)
    return applied
