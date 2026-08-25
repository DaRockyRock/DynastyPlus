"""Central configuration for Dynasty+ Tools."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _platform_data_dir(app_name: str) -> Path:
    """Return the conventional per-user data directory for this platform."""
    home = Path.home()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or (home / "AppData" / "Local")
        return Path(base) / app_name
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / app_name
    base = os.environ.get("XDG_DATA_HOME") or (home / ".local" / "share")
    return Path(base) / app_name


def _resolve_data_dir() -> Path:
    """Resolve runtime storage from an override, an app bundle, or this checkout."""
    override = os.environ.get("CFBMOD_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        return _platform_data_dir("CFBMod")
    return ROOT_DIR / "data"


DATA_DIR = _resolve_data_dir()
SIM_DIR = DATA_DIR / "sim"
BUDGET_DIR = DATA_DIR / "budget"
UPLOADS_DIR = DATA_DIR / "uploads"
SAVE_DIR = DATA_DIR / "save"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
TEAMS_CACHE_FILE = DATA_DIR / "teams_cache.json"

for _directory in (DATA_DIR, SIM_DIR, BUDGET_DIR, UPLOADS_DIR, SAVE_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

SAVE_PATH = os.getenv("CFBMOD_SAVE_PATH", "").strip() or str(SAVE_DIR / "dynasty.json")

HOST = os.getenv("CFBMOD_HOST", "127.0.0.1").strip()
PORT = int(os.getenv("CFBMOD_PORT", "5050"))
APP_VERSION = "0.1.0"

# Modeled defaults used until College Football 27 data can supply these values.
DP_PER_DOLLAR = float(os.getenv("CFBMOD_DP_PER_DOLLAR", "0.0004"))
WEEKLY_RECRUITING_HOURS = int(os.getenv("CFBMOD_WEEKLY_HOURS", "1500"))
