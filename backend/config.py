"""Central configuration for Dynasty+ Tools.

All settings are read from environment variables (loaded from a local .env
file when present). Sensible defaults let the app boot with zero config so the
UI can be built out before the game ships.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Project layout -----------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load optional local overrides from the project root.
load_dotenv(ROOT_DIR / ".env")


APP_NAME = "Dynasty+ Tools"


def _platform_data_dir(app_name: str) -> Path:
    """The OS-conventional per-user data directory for a published desktop app.

    Windows -> %LOCALAPPDATA%\\<app>, macOS -> ~/Library/Application Support/<app>,
    Linux/other -> $XDG_DATA_HOME or ~/.local/share/<app>.
    """
    home = Path.home()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or (home / "AppData" / "Local")
        return Path(base) / app_name
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / app_name
    base = os.environ.get("XDG_DATA_HOME") or (home / ".local" / "share")
    return Path(base) / app_name


def _resolve_data_dir() -> Path:
    """Where all runtime playthrough data lives. Precedence:

    1. CFBMOD_DATA_DIR  - explicit override (honored in any environment).
    2. a bundled/frozen build (PyInstaller, py2app, Electron-packed Python): the
       OS per-user data dir, so writes never land in a read-only install
       directory and the user's dynasties survive app updates/reinstalls.
    3. a source checkout (development): the repo's ./data, unchanged.

    Everything else (per-dynasty stores, the archive, the save boundary) derives
    from this, so this is the single seam to point data wherever it belongs.
    """
    override = os.environ.get("CFBMOD_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        return _platform_data_dir("CFBMod Tools")
    return ROOT_DIR / "data"


DATA_DIR = _resolve_data_dir()
UPLOADS_DIR = DATA_DIR / "uploads"  # custom conference logos
FRONTEND_DIR = ROOT_DIR / "frontend"
# The single Tools frontend is built to frontend/dist.
FRONTEND_DIST = FRONTEND_DIR / "dist"
TEAMS_CACHE_FILE = DATA_DIR / "teams_cache.json"

for _d in (DATA_DIR, UPLOADS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _seed_bundled_data() -> None:
    """First-run seeding for a frozen/packaged build.

    In a source checkout DATA_DIR is the repo's ./data, which already holds the
    checked-in league seed. In a frozen build DATA_DIR is a fresh per-user dir,
    so copy it out of the PyInstaller bundle on first run. Existing files are
    never overwritten, so a user's edits survive.
    """
    if not getattr(sys, "frozen", False):
        return
    bundled = Path(getattr(sys, "_MEIPASS", ROOT_DIR)) / "data"
    for name in ("league_seed.json",):
        src, dst = bundled / name, DATA_DIR / name
        if src.exists() and not dst.exists():
            try:
                dst.write_bytes(src.read_bytes())
            except OSError:
                pass


_seed_bundled_data()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# The real CFB 27 save location ---------------------------------------------
# Dynasty+ reads the game's own dynasty saves. By default this is EA's saves
# folder under Documents; CFBMOD_SAVE_PATH overrides it (a folder, or a single
# save file). backend/saveparse/cfb27.discover() enumerates the DYNASTY-* saves
# there and joins them against the college profile (PROFILE-COLLEGE) to map each
# save to a dynasty. Empty default = the standard Documents saves folder.
SAVE_PATH = os.getenv("CFBMOD_SAVE_PATH", "").strip() or str(
    Path.home() / "Documents" / "EA SPORTS College Football 27" / "saves")

# The CFB 27 install location, used to extract game art (logos/helmets/fonts).
# CFBMOD_GAME_ROOT overrides; empty default = the standard Steam install path
# (mirrors assets/frostbite/gamefs.DEFAULT_GAME_ROOT). The in-app Setup screen
# can override this at runtime via app_settings for a non-standard install.
GAME_ROOT = os.getenv("CFBMOD_GAME_ROOT", "").strip() or str(
    Path(r"C:\Program Files (x86)\Steam\steamapps\common\College Football 27"))

# Web server ---------------------------------------------------------------
# CFBMOD_PORT overrides the local Tools server port.
HOST = os.getenv("CFBMOD_HOST", "127.0.0.1").strip()
PORT = int(os.getenv("CFBMOD_PORT", "5051"))

APP_VERSION = "0.1.9"

def runtime_summary() -> dict:
    """Small, non-sensitive description of the local Tools runtime."""
    return {
        "version": APP_VERSION,
        "app_name": APP_NAME,
        "data_dir": str(DATA_DIR),
        "save_path": SAVE_PATH or None,
        "watching": bool(SAVE_PATH),
        "save_present": Path(SAVE_PATH).exists() if SAVE_PATH else False,
    }
