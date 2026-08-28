"""Detect the MMC Modding Tools and hand Dynasty+ mods to their Mod Manager.

The MMC Modding Tools (from the Madden / College Football Modding
Communities) are a fork of the open-source Frosty Toolsuite with a CFB 27
profile. They are the community-standard modding pipeline and the one
Dynasty+ targets: we export `.fbmod` files (assets/frostbite/fbmod.py), drop
them into the Mod Manager's mod library, and the manager owns building
ModData and launching the game. Three things have to be true on a machine
before in-game mods work, and status() reports each one:

  1. the tools are installed somewhere (the user extracts the archive to any
     folder; we keep the location in app_settings and auto-discover common
     spots as a convenience);
  2. the game's anti-cheat launcher has been swapped for the tools' stub
     (EAAntiCheat.GameServiceLauncher.exe in the game root: the original is
     ~17 MB, the stub ~95 KB; the original gets renamed aside). Without the
     swap the game rejects modified data, which is why Dynasty+'s own
     ModData attempts never rendered. The swap is the user's call and their
     action; Dynasty+ only detects and explains it;
  3. the exported mod is present in the manager's library
     (<manager>/Mods/CollegeFootball27/), where it shows up in the manager's
     mod list ready to Apply.

Community rule surfaced in the UI: mods are for offline/local play only,
never Online Dynasty.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from . import app_settings

MANAGER_EXE = "MMCModManager.exe"
EDITOR_EXE = "MMCEditor.exe"
PROFILE_NAME = "CollegeFB27"  # the manager's per-game mod library folder (Mods/<profile>/)

AC_EXE = "EAAntiCheat.GameServiceLauncher.exe"
AC_BACKUPS = ("_EAAntiCheat.GameServiceLauncher.exe",
              "EAAntiCheat.GameServiceLauncher_Orig.exe")
# the MMC stub is ~95 KB; EA's real launcher is ~17.5 MB
_AC_STUB_MAX_BYTES = 2 * 1024 * 1024


def _find_exe(root: Path, exe: str) -> Path | None:
    """Find `exe` in root or up to two levels below it (the archive extracts
    as MMC_Modding_Tools_vX/MMC_ModManager_vX/MMCModManager.exe, but users
    may point at any of those levels)."""
    try:
        if (root / exe).is_file():
            return root / exe
        for pattern in (f"*/{exe}", f"*/*/{exe}"):
            hit = next(root.glob(pattern), None)
            if hit is not None:
                return hit
    except OSError:
        pass
    return None


def discover() -> Path | None:
    """Best-effort scan of the usual landing spots for an extracted copy of
    the tools. Shallow globs only; the folder picker covers everything else."""
    home = Path.home()
    for base in (home / "Downloads", home / "Desktop", home / "Documents"):
        try:
            for cand in sorted(base.glob("MMC*Modding*Tools*")):
                if cand.is_dir() and _find_exe(cand, MANAGER_EXE):
                    return cand
        except OSError:
            continue
    return None


def tools_root() -> Path | None:
    """The tools folder: the user's setting, else auto-discovery."""
    saved = app_settings.resolve_modtools_path()
    if saved is not None:
        return saved
    return discover()


def anticheat_state(game_root: Path) -> tuple[str, bool]:
    """(state, backup_present) for the game root's anti-cheat launcher.
    state: 'stub' (MMC stub installed, mods will load), 'original' (EA's
    launcher still active), or 'unknown' (no game root / no launcher)."""
    backup = any((game_root / b).is_file() for b in AC_BACKUPS)
    try:
        size = (game_root / AC_EXE).stat().st_size
    except OSError:
        return "unknown", backup
    return ("stub" if size <= _AC_STUB_MAX_BYTES else "original"), backup


def mods_dir(manager_exe: Path) -> Path:
    """The manager's per-game mod library (created on demand; the manager
    also creates it on first run)."""
    return manager_exe.parent / "Mods" / PROFILE_NAME


def status() -> dict[str, Any]:
    """Everything the UI needs to render the mod-tools setup card."""
    root = tools_root()
    manager = _find_exe(root, MANAGER_EXE) if root else None
    editor = _find_exe(root, EDITOR_EXE) if root else None
    game_root = app_settings.resolve_game_root()
    ac_state, ac_backup = anticheat_state(game_root)

    installed = None
    if manager is not None:
        try:
            mods = sorted(mods_dir(manager).glob("*.fbmod"))
            installed = [m.name for m in mods if m.name.startswith("DynastyPlus")]
        except OSError:
            installed = None

    return {
        "tools_found": manager is not None,
        "tools_path": str(root) if root else None,
        "tools_path_set": app_settings.resolve_modtools_path() is not None,
        "manager_exe": str(manager) if manager else None,
        "editor_found": editor is not None,
        "game_root": str(game_root),
        "anticheat": ac_state,
        "anticheat_backup": ac_backup,
        "anticheat_exe": AC_EXE,
        "mods_dir": str(mods_dir(manager)) if manager else None,
        "installed_mods": installed or [],
        # mods will actually load in game only when both are true
        "ready": manager is not None and ac_state == "stub",
    }


def set_path(path: str) -> dict[str, Any]:
    """Persist the tools folder ("" clears back to auto-discovery). Raises
    ValueError when the folder does not hold the Mod Manager."""
    path = (path or "").strip()
    if path:
        p = Path(path).expanduser()
        if not p.is_dir():
            raise ValueError("That folder does not exist.")
        if _find_exe(p, MANAGER_EXE) is None:
            raise ValueError(f"{MANAGER_EXE} was not found in that folder. Pick the "
                             "folder the MMC Modding Tools were extracted to.")
    app_settings.set_paths(modtools_path=path)
    return status()


def install_fbmod(src: Path | str) -> Path:
    """Copy an exported .fbmod into the manager's mod library so it appears
    in the manager's Available Mods list. Raises ValueError when the tools
    are not installed."""
    root = tools_root()
    manager = _find_exe(root, MANAGER_EXE) if root else None
    if manager is None:
        raise ValueError("The MMC Modding Tools were not found.")
    src = Path(src)
    dest_dir = mods_dir(manager)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    return dest


def open_manager() -> dict[str, Any]:
    """Launch the MMC Mod Manager (Windows honors its run-as-administrator
    compatibility flag, so the UAC prompt appears when the user set one)."""
    st = status()
    if not st["tools_found"]:
        raise ValueError("The MMC Modding Tools were not found.")
    os.startfile(st["manager_exe"])  # noqa: S606 - user-initiated launch
    return {"ok": True, "launched": st["manager_exe"]}
