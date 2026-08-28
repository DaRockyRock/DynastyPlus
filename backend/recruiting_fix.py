"""Capacity-safe recruiting competition correction for CFB 27 saves.

The tool reads and writes the game's Recruit, RecruitTarget, and
ProspectTargetSchool stores directly.

Scholarship totals and active attention are corrected independently.  Offer
totals are raised to a rank tier floor.  Active attention is reallocated within
each CPU school's existing 35 slot board, from surplus lower ranked prospects
to under attended top prospects already present in that school's top school
list.  Committed prospects and the user's recruiting board are never changed.
"""
from __future__ import annotations

import json
import struct
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple

from . import app_settings, confsetup, dynasty_paths
from .saveparse import container
from .saveparse import recruiting as saverecruiting
from .saveparse import teams as saveteams


class Tier(NamedTuple):
    key: str
    rank_lo: int
    rank_hi: int
    offer_floor: int
    target_top_interest: int
    attention_floor: int = 0


# Offer floors follow the original real world calibration.  Attention floors
# are intentionally separate and fit inside CFB 27's fixed 138 by 35 CPU board
# grid.  Only the first 600 prospects receive a guaranteed active attention
# floor.  The game remains free to use every other slot as it sees fit.
TIERS: list[Tier] = [
    Tier("top10", 1, 10, 22, 96, 6),
    Tier("elite5", 11, 32, 20, 94, 5),
    Tier("high4", 33, 150, 16, 90, 3),
    Tier("mid4", 151, 250, 13, 84, 2),
    Tier("low4", 251, 330, 11, 80, 2),
    Tier("high3", 331, 450, 9, 74, 1),
    Tier("mid3", 451, 600, 7, 68, 1),
    Tier("low3", 601, 10_000, 5, 60, 0),
]

_CONFIG_FILE = lambda: dynasty_paths.sub("recruiting") / "settings.json"
_config_lock = threading.Lock()
_status_lock = threading.Lock()
_status: dict[str, Any] = {
    "phase": "idle", "running": False, "reload_required": False,
    "save": None, "message": None, "result": None, "progress": 0,
    "revision": 0,
}


def tier_for(national_rank: int) -> Tier:
    for tier in TIERS:
        if tier.rank_lo <= national_rank <= tier.rank_hi:
            return tier
    return TIERS[-1]


def real_offer_floor(national_rank: int) -> int:
    """Floor used by the real save writer until recruit positions are mapped."""
    return min(31, tier_for(national_rank).offer_floor)


def attention_floor_for(national_rank: int) -> int:
    return tier_for(national_rank).attention_floor


def _default_config() -> dict[str, Any]:
    return {
        # Opt in because a patched save must be reloaded in CFB 27.  The tool
        # explains this before enabling and the global auto sync remains a
        # second master switch.
        "enabled": False,
        "offer_correction": True,
        "attention_correction": True,
        "last_applied": None,
    }


def get_config() -> dict[str, Any]:
    cfg = _default_config()
    try:
        raw = json.loads(_CONFIG_FILE().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for key in cfg:
                if key in raw:
                    cfg[key] = raw[key]
    except (OSError, ValueError):
        pass
    return cfg


def set_config(body: dict[str, Any]) -> dict[str, Any]:
    with _config_lock:
        cfg = get_config()
        for key in ("enabled", "offer_correction", "attention_correction"):
            if key in body:
                cfg[key] = bool(body[key])
        path = _CONFIG_FILE()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def _save_config(cfg: dict[str, Any]) -> None:
    with _config_lock:
        path = _CONFIG_FILE()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _set_status(**changes: Any) -> dict[str, Any]:
    with _status_lock:
        _status.update(changes)
        _status["revision"] = int(_status.get("revision", 0)) + 1
        return dict(_status)


def automation_status() -> dict[str, Any]:
    with _status_lock:
        return dict(_status)


def is_enabled() -> bool:
    """Whether this dynasty explicitly opted into recruiting save writes."""
    return bool(get_config().get("enabled"))


def mark_detected(path: str | Path | None = None) -> None:
    _set_status(phase="detected", running=True, reload_required=False,
                save=Path(path).name if path else None,
                message="Waiting for CFB 27 to finish saving", result=None,
                progress=8)


def mark_shared_tools() -> dict[str, Any]:
    """Hold the frontend while the remaining shared weekly tools run."""
    current = automation_status()
    if current.get("reload_required") or current.get("phase") == "error":
        return current
    return _set_status(
        phase="tools", running=True, reload_required=False,
        message="Synchronizing playoff and rankings tools", progress=78,
    )


def finish_shared_tools() -> dict[str, Any]:
    """Release the media gate unless recruiting requires a game reload."""
    current = automation_status()
    if current.get("reload_required") or current.get("phase") == "error":
        return current
    return _set_status(
        phase="complete", running=False, reload_required=False,
        message="Weekly dynasty tools are ready", progress=100,
    )


def acknowledge_reload() -> dict[str, Any]:
    return _set_status(phase="idle", running=False, reload_required=False,
                       message=None, result=None, progress=0)


@contextmanager
def _save_lock():
    """Serialize recruiting save writes across running Tools processes."""
    from .saveparse import cfb27
    path = cfb27.saves_dir() / ".dynastyplus-recruiting.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+")
    locked = False
    try:
        try:
            import msvcrt
            fh.seek(0)
            for _ in range(150):
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                    break
                except OSError:
                    time.sleep(0.2)
            if not locked:
                raise TimeoutError("another Dynasty+ Tools process is updating this save")
        except ImportError:  # pragma: no cover
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
            locked = True
        yield
    finally:
        try:
            if locked:
                try:
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except ImportError:  # pragma: no cover
                    import fcntl
                    fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()


def _plan(state: saverecruiting.RecruitingState, user_team_row: int | None,
          cfg: dict[str, Any]):
    offers, attention = saverecruiting.correction_plan(
        state, offer_floor=real_offer_floor,
        attention_floor=attention_floor_for, user_team_row=user_team_row)
    if not cfg.get("offer_correction", True):
        offers = []
    if not cfg.get("attention_correction", True):
        attention = []
    return offers, attention


def _user_team_row() -> int | None:
    try:
        from . import dynasties
        from .saveparse import profile
        current = dynasties.current() or {}
        name = current.get("save_name")
        if not name:
            return None
        ctx = confsetup._read_table()
        if ctx is None:
            return None
        slot = profile.slot_for(ctx["path"])
        if slot is not None:
            return slot.team_row
        # Manually imported saves can outlive their PROFILE-COLLEGE row.  The
        # registry still carries the selected school, so resolve its stable
        # team-table row and keep that board out of CPU attention transfers.
        school = str(current.get("school") or "").strip().casefold()
        if school:
            for row, team in enumerate(saveteams.parse_teams(ctx["payload"])):
                if team.school.casefold() == school:
                    return row
        return None
    except Exception:
        return None


def tool_state() -> dict[str, Any]:
    cfg = get_config()
    payload = confsetup.current_payload()
    if payload is None:
        return {"available": False, "writable": False, "config": cfg,
                "reason": "No readable CFB 27 dynasty save is selected.",
                "automation": automation_status()}
    try:
        state = saverecruiting.parse(payload)
        offers, attention = _plan(state, _user_team_row(), cfg)
        audit = saverecruiting.summary(
            state, tiers=TIERS, offer_floor=real_offer_floor,
            attention_floor=attention_floor_for)
        return {
            "available": True,
            "writable": True,
            "config": cfg,
            "audit": audit,
            "plan": {"offers": len(offers), "attention": len(attention)},
            "automation": automation_status(),
            "reload_required": True,
        }
    except (ValueError, struct.error) as exc:
        return {"available": False, "writable": False, "config": cfg,
                "reason": str(exc), "automation": automation_status()}


def _matches_changed_path(ctx: dict[str, Any], changed_path: str | Path | None) -> bool:
    if changed_path is None:
        return True
    try:
        return Path(changed_path).resolve() == Path(ctx["path"]).resolve()
    except OSError:
        return False


def apply_to_current_save(*, automatic: bool = False,
                          changed_path: str | Path | None = None) -> dict[str, Any]:
    cfg = get_config()
    # Both manual and automatic entry points are strict no-ops while the
    # per-dynasty switch is off.  The tab still audits the save, but no path is
    # allowed to mutate recruiting data until the user explicitly opts in.
    if not cfg.get("enabled"):
        result = {"available": True, "written": False,
                  "reason": "recruiting correction is off", "automatic": automatic}
        return result
    if automatic and not app_settings.autosync_enabled():
        result = {"available": True, "written": False,
                  "reason": "automatic save sync is off", "automatic": True}
        _set_status(phase="complete", running=False, reload_required=False,
                    message="Automatic save sync is off", result=result)
        return result

    _set_status(phase="recruiting", running=True, reload_required=False,
                message="Reading CFB 27 recruiting records", result=None,
                progress=22)
    try:
        with _save_lock():
            ctx = confsetup._read_table()
            if ctx is None:
                raise ValueError("No readable CFB 27 dynasty save is selected.")
            _set_status(save=ctx["path"].name, progress=36,
                        message="Calculating offer and attention corrections")
            if not _matches_changed_path(ctx, changed_path):
                result = {"available": True, "written": False,
                          "reason": "a different dynasty save changed", "automatic": automatic}
                _set_status(phase="complete", running=False, reload_required=False,
                            message="A different dynasty save changed", result=result)
                return result

            before = saverecruiting.parse(ctx["payload"])
            offer_changes, transfers = _plan(before, _user_team_row(), cfg)
            if not offer_changes and not transfers:
                result = {"available": True, "written": False, "offers": 0,
                          "attention": 0, "reason": "the class already meets its floors",
                          "automatic": automatic}
                _set_status(phase="recruiting" if automatic else "complete",
                            running=automatic, reload_required=False,
                            message="Recruiting class already meets its floors", result=result,
                            progress=70)
                return result

            _set_status(progress=52, message="Applying corrections in memory")
            patched = bytearray(ctx["payload"])
            saverecruiting.apply_plan(patched, before, offer_changes, transfers)
            _set_status(progress=66, message="Verifying corrected recruiting data")
            after = saverecruiting.parse(bytes(patched))
            if after.target_refs != before.target_refs:
                raise ValueError("recruiting target capacity changed during verification")
            for change in offer_changes:
                if after.prospects_by_row[change.recruit_row].offers != change.after:
                    raise ValueError("an offer correction did not verify")
            for transfer in transfers:
                target = after.prospects_by_row[transfer.to_recruit_row].targets.get(
                    transfer.school_row)
                if target is None or target.row != transfer.target_row:
                    raise ValueError("an attention transfer did not verify")

            _set_status(progress=80, message="Creating backup and preparing dynasty save")
            confsetup._backup_once(ctx["path"])
            encoded = container.encode(ctx["raw"], bytes(patched), saved_at=datetime.now())
            # Reopen the encoded bytes before touching disk.  This verifies both
            # the container and all recruiting references in the final stream.
            verified = container.decode(encoded)
            saverecruiting.parse(verified.payload)
            _set_status(progress=88, message="Writing verified recruiting corrections")
            ctx["path"].write_bytes(encoded)
            confsetup.invalidate_caches()

            result = {
                "available": True,
                "written": True,
                "offers": len(offer_changes),
                "attention": len(transfers),
                "save": ctx["path"].name,
                "automatic": automatic,
            }
            cfg["last_applied"] = {
                "at": datetime.now().isoformat(timespec="seconds"),
                "save": ctx["path"].name,
                "offers": len(offer_changes),
                "attention": len(transfers),
            }
            _save_config(cfg)
            _set_status(
                phase="reload_required", running=False, reload_required=True,
                save=ctx["path"].name,
                message="Reload this dynasty in CFB 27 before continuing",
                result=result, progress=100,
            )
            return result
    except Exception as exc:
        _set_status(phase="error", running=False, reload_required=False,
                    message=str(exc), result=None)
        if automatic:
            return {"available": False, "written": False, "error": str(exc),
                    "automatic": True}
        raise


def auto_apply(changed_path: str | Path | None = None) -> dict[str, Any]:
    return apply_to_current_save(automatic=True, changed_path=changed_path)
