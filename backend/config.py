"""Central configuration for the CFBMod companion app.

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

# Load .env from the project root first, so path/LLM config below can read it.
load_dotenv(ROOT_DIR / ".env")


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
        return _platform_data_dir("CFBMod")
    return ROOT_DIR / "data"


DATA_DIR = _resolve_data_dir()
CACHE_DIR = DATA_DIR / "cache"
NARRATIVE_DIR = DATA_DIR / "narrative"
BUDGET_DIR = DATA_DIR / "budget"
MESSAGES_DIR = DATA_DIR / "messages"  # persisted phone conversation threads
FEED_DIR = DATA_DIR / "feed"  # persisted social-feed state (coach likes + seen marker)
WORLD_DIR = DATA_DIR / "world"  # persisted world-reaction event log (coach-caused tweets/articles/texts)
INTERVIEWS_DIR = DATA_DIR / "interviews"  # persisted post-game press conference transcripts
MOCK_DIR = DATA_DIR / "mock"
SIM_DIR = DATA_DIR / "sim"  # persisted simulated seasons (the Simulator app owns these)
UPLOADS_DIR = DATA_DIR / "uploads"  # user-uploaded images for the Customize flow
SAVE_DIR = DATA_DIR / "save"  # the file boundary between the two apps (see below)
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"  # Vite production build served by Flask
TEAMS_CACHE_FILE = DATA_DIR / "teams_cache.json"

for _d in (DATA_DIR, CACHE_DIR, NARRATIVE_DIR, BUDGET_DIR, MESSAGES_DIR, FEED_DIR,
           WORLD_DIR, INTERVIEWS_DIR, MOCK_DIR, SIM_DIR, UPLOADS_DIR, SAVE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Anthropic / LLM ----------------------------------------------------------
# These are the .env-derived SEED values. At runtime the live connection is
# owned by backend/llm_settings.py (persisted to data/llm.json and editable from
# the in-app setup wizard); these only bootstrap it on first run.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
MODEL = os.getenv("CFBMOD_MODEL", "claude-haiku-4-5").strip()

# Optional seeds for connecting a local Anthropic-compatible server instead of
# Anthropic's hosted API (both speak the Messages API; they differ by base_url).
LLM_PROVIDER = os.getenv("CFBMOD_LLM_PROVIDER", "").strip().lower()
LLM_BASE_URL = os.getenv("CFBMOD_LLM_BASE_URL", "").strip()

# Raw master switch from .env. The effective "is generation on" decision lives
# in llm_settings.is_ready() (this AND a usable connection). USE_LLM is kept as a
# convenience for the .env seed and any legacy reads.
LLM_ENABLED_ENV = _as_bool(os.getenv("CFBMOD_USE_LLM"), default=False)
USE_LLM = LLM_ENABLED_ENV and bool(ANTHROPIC_API_KEY)

# The two-app file boundary ------------------------------------------------
# The Simulator (a CFB 27 stand-in) writes the assembled dynasty save here; the
# Dynasty+ companion watches it and reads from it. When the real CFB 27 save
# format is known, the game writes this same file and the Simulator goes away.
# Dynasty+ always watches the save now (the empty "no save" default is gone).
SAVE_PATH = os.getenv("CFBMOD_SAVE_PATH", "").strip() or str(SAVE_DIR / "dynasty.json")

# The companion inbox: Dynasty+ appends coach actions here (NIL offers,
# recruiting actions, allocations); the Simulator drains and applies them.
INBOX_PATH = os.getenv("CFBMOD_INBOX_PATH", "").strip() or str(SAVE_DIR / "companion_inbox.json")

# Demo mode: a startup-only flag for building/testing the UI without a live
# save file. When on, the frontend shows a manual "Advance Week" control
# instead of the passive live-watch indicator. The normal experience is
# passive (watch the save, generate, refresh the screen) and needs no flag.
# Run with:  CFBMOD_DEMO_MODE=true python run.py
DEMO_MODE = _as_bool(os.getenv("CFBMOD_DEMO_MODE"), default=False)

# Debug mode: surfaces the in-app Simulation panel (start a new season, advance
# week to week, simulate / override game results) for building and testing the
# app against a modeled CFB 27 season before the save format is readable. Implied
# by DEMO_MODE. Run with:  CFBMOD_DEBUG=true python run.py
DEBUG_MODE = _as_bool(os.getenv("CFBMOD_DEBUG"), default=False) or DEMO_MODE

# Web server ---------------------------------------------------------------
HOST = os.getenv("CFBMOD_HOST", "127.0.0.1").strip()
PORT = int(os.getenv("CFBMOD_PORT", "5050"))  # Dynasty+ companion
# 5070, not 5060: browsers block port 5060 (it is the SIP port, ERR_UNSAFE_PORT),
# so a 5060 page dead-ends at about:blank. 5070 is unrestricted.
SIM_PORT = int(os.getenv("CFBMOD_SIM_PORT", "5070"))  # the Simulator (CFB 27 stand-in)

APP_VERSION = "0.1.0"

# Default team for development / mock data.
DEFAULT_TEAM = "Nebraska Cornhuskers"

# NIL / Dynasty Points budget --------------------------------------------
# CFB 27 introduces Dynasty Points as the annual program budget (allocated
# across Coaching Staff / Facilities / NIL) while NIL deals themselves are
# dollar figures. These constants tie the two together and bound the weekly
# recruiting effort. They are modeled assumptions until the save format is
# readable; the future save parser fills dynasty["nil"] and these are the
# fallbacks. DP_PER_DOLLAR: 0.0004 means every $250k of NIL committed draws
# 100 Dynasty Points from your available balance.
DP_PER_DOLLAR = float(os.getenv("CFBMOD_DP_PER_DOLLAR", "0.0004"))
WEEKLY_RECRUITING_HOURS = int(os.getenv("CFBMOD_WEEKLY_HOURS", "1500"))


def runtime_summary() -> dict:
    """Small dict describing how the backend is configured, for the UI. The LLM
    fields come from the live llm_settings store (not the .env seed) so the UI
    reflects whatever the user set up in the wizard."""
    from . import llm_settings  # lazy: llm_settings imports config

    st = llm_settings.status()
    return {
        "version": APP_VERSION,
        "model": st["model"],
        "provider": st["provider"],
        "base_url": st["base_url"],
        "use_llm": st["ready"],
        "llm_enabled": st["enabled"],
        "llm_configured": st["configured"],
        "has_api_key": st["anthropic"]["has_api_key"] or st["local"]["has_api_key"],
        "data_dir": str(DATA_DIR),
        "save_path": SAVE_PATH or None,
        "watching": bool(SAVE_PATH),
        # True once the Simulator (or the real game) has written a save. Dynasty+
        # shows a "start the Simulator" state until then.
        "save_present": Path(SAVE_PATH).exists() if SAVE_PATH else False,
        "demo_mode": DEMO_MODE,
        "debug_mode": DEBUG_MODE,
    }
