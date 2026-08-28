"""Auto-detect where CFB 27 is installed and where its dynasty saves live.

Powers the in-app Setup screen so a non-programmer does not have to know or type
a path. Detection is best-effort and cheap (no deep disk scans): it checks the
known Steam/EA locations and Steam's own library list. Whatever it finds is
offered as a pick; a native "Browse..." folder picker (Electron) is always the
fallback for anything unusual.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import config

# A folder is a CFB 27 install if it has the Oodle DLL or the Frostbite catalog.
_INSTALL_MARKERS = ("oo2core_9_win64.dll", "Data/layout.toc")
_GAME_DIR_NAMES = ("College Football 27", "EA SPORTS College Football 27")


def _is_install(path: Path) -> bool:
    return path.is_dir() and any((path / m.replace("/", "\\")).exists()
                                 or (path / m).exists() for m in _INSTALL_MARKERS)


def _steam_roots() -> list[Path]:
    roots = []
    for p in (Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")):
        if (p / "steamapps").is_dir():
            roots.append(p)
    return roots


def _steam_libraries() -> list[Path]:
    """Every Steam library folder, read from libraryfolders.vdf (games are often
    installed to a second drive, not the default Steam folder)."""
    libs: list[Path] = []
    for root in _steam_roots():
        libs.append(root)
        vdf = root / "steamapps" / "libraryfolders.vdf"
        try:
            text = vdf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # entries look like:   "path"    "D:\\SteamLibrary"
        for m in re.finditer(r'"path"\s*"([^"]+)"', text):
            libs.append(Path(m.group(1).replace("\\\\", "\\")))
    # de-dupe, keep order
    seen, out = set(), []
    for lib in libs:
        key = str(lib).lower()
        if key not in seen:
            seen.add(key)
            out.append(lib)
    return out


def detect_game_installs() -> list[str]:
    """Candidate CFB 27 install folders, best guess first. Only real installs
    (passing the marker check) are returned."""
    candidates: list[Path] = [Path(config.GAME_ROOT)]

    # Steam libraries (default + extra drives).
    for lib in _steam_libraries():
        for name in _GAME_DIR_NAMES:
            candidates.append(lib / "steamapps" / "common" / name)

    # EA app / Origin default locations.
    for base in (r"C:\Program Files\EA Games", r"C:\Program Files (x86)\EA Games",
                 r"C:\Program Files\Electronic Arts", r"C:\Program Files (x86)\Origin Games"):
        for name in _GAME_DIR_NAMES:
            candidates.append(Path(base) / name)

    # A SteamLibrary/EA Games folder on any other drive root (cheap top-level check).
    for drive in "DEFGH":
        d = Path(f"{drive}:\\")
        if not d.exists():
            continue
        for sub in ("SteamLibrary/steamapps/common", "Games/steamapps/common",
                    "EA Games", "Games"):
            for name in _GAME_DIR_NAMES:
                candidates.append(d / sub.replace("/", "\\") / name)

    found, seen = [], set()
    for c in candidates:
        key = str(c).lower()
        if key in seen:
            continue
        seen.add(key)
        if _is_install(c):
            found.append(str(c))
    return found


def _documents_dirs() -> list[Path]:
    home = Path.home()
    dirs = [home / "Documents", home / "OneDrive" / "Documents"]
    # Some OneDrive setups localize/rename the Documents folder; include any
    # sibling that already holds the game's folder.
    return dirs


def detect_saves_folders() -> list[str]:
    """Candidate dynasty saves folders that actually exist, best guess first."""
    found, seen = [], set()
    for docs in _documents_dirs():
        saves = docs / "EA SPORTS College Football 27" / "saves"
        key = str(saves).lower()
        if key in seen:
            continue
        seen.add(key)
        if saves.is_dir():
            found.append(str(saves))
    return found


def is_valid_install(path: str | Path) -> bool:
    """True if the folder looks like a CFB 27 install (marker-file check)."""
    try:
        return _is_install(Path(path).expanduser())
    except OSError:
        return False
