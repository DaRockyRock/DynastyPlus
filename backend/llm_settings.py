"""Runtime LLM connection settings - the single source of truth for how CFBMod
reaches a model.

Persisted to data/llm.json so the in-app setup wizard can change the connection
at runtime (no .env edit, no restart). Seeded from .env on first run so existing
installs keep working unchanged.

Both providers speak the Anthropic Messages API, so the generation code in
llm.py is identical for each - the only difference is the client's base_url:

  * "anthropic"  Anthropic's hosted API (external). Needs an API key.
  * "local"      An Anthropic-compatible server on the user's machine (a local
                 proxy/gateway exposing the Messages API), reached via a custom
                 base_url. API key optional.

This module is a near-leaf: it depends only on config (paths + env seed) and is
imported by llm.py, app.py and pipeline.py. It never hands the API key to the
frontend - status() returns only a has_api_key boolean.
"""
from __future__ import annotations

import copy
import json
import threading
from typing import Any

from . import config

_lock = threading.Lock()
_STORE_FILE = config.DATA_DIR / "llm.json"

PROVIDERS = ("anthropic", "local")
DEFAULT_MODEL = "claude-haiku-4-5"

# Models offered in the wizard's dropdown for the external Anthropic provider.
# Current model ids; Haiku is the default - fastest and cheapest, a good fit for
# the per-week burst of generation this app does.
KNOWN_MODELS = [
    {"id": "claude-haiku-4-5", "label": "Claude Haiku 4.5 - fastest, cheapest"},
    {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 - balanced"},
    {"id": "claude-opus-4-8", "label": "Claude Opus 4.8 - most capable"},
]

_cache: dict[str, Any] | None = None


# =========================================================================
# Seed + load + persist
# =========================================================================
def _seed() -> dict[str, Any]:
    """Initial settings derived from .env / config (first run, before the user
    has touched the wizard)."""
    env_model = (config.MODEL or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    env_base = config.LLM_BASE_URL
    provider = config.LLM_PROVIDER if config.LLM_PROVIDER in PROVIDERS else ("local" if env_base else "anthropic")

    if provider == "local":
        enabled = bool(config.LLM_ENABLED_ENV and env_base)
    else:
        enabled = bool(config.LLM_ENABLED_ENV and config.ANTHROPIC_API_KEY)

    return {
        "provider": provider,
        "enabled": enabled,
        # "configured" gates the first-run wizard. An install that turned on
        # generation via .env is treated as already set up; a zero-config install
        # is not, so the wizard greets it.
        "configured": enabled,
        "anthropic": {"api_key": config.ANTHROPIC_API_KEY, "model": env_model},
        # Local has no default model id - it is whatever the user runs (llama3.1,
        # qwen2.5, ...). Seed it from CFBMOD_MODEL only when .env selects local;
        # otherwise leave it blank for the wizard to fill.
        "local": {"base_url": env_base, "api_key": "", "model": (env_model if provider == "local" else "")},
    }


def _load() -> dict[str, Any]:
    """The effective settings: defaults seeded from .env, overlaid with whatever
    the user saved through the wizard. Cached in-process; save() invalidates."""
    global _cache
    if _cache is not None:
        return _cache
    data = _seed()
    if _STORE_FILE.exists():
        try:
            with _STORE_FILE.open("r", encoding="utf-8") as fh:
                stored = json.load(fh)
            if isinstance(stored, dict):
                for key in ("provider", "enabled", "configured"):
                    if key in stored:
                        data[key] = stored[key]
                for prov in PROVIDERS:
                    if isinstance(stored.get(prov), dict):
                        data[prov].update(stored[prov])
                if data["provider"] not in PROVIDERS:
                    data["provider"] = "anthropic"
        except (OSError, ValueError):
            pass
    _cache = data
    return data


def _persist(data: dict[str, Any]) -> None:
    try:
        with _STORE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def _after_change() -> None:
    """Settings changed: drop the cached LLM client so the next call rebuilds it,
    and clear the current week's cached module output so it regenerates with the
    new connection. Past weeks are left intact (the dynasty archive)."""
    try:
        from . import llm
        llm.reset_client()
    except Exception:
        pass
    try:
        from . import cache
        cache.clear_current_week()
    except Exception:
        pass


# =========================================================================
# Accessors (read at generate time)
# =========================================================================
def provider() -> str:
    return _load()["provider"]


def _conn() -> dict[str, Any]:
    cur = _load()
    return cur.get(cur["provider"], {})


def model() -> str:
    cur = _load()
    m = (cur.get(cur["provider"], {}).get("model") or "").strip()
    if m:
        return m
    # Only the hosted provider has a meaningful default; local must be explicit.
    return DEFAULT_MODEL if cur["provider"] == "anthropic" else ""


def base_url() -> str | None:
    cur = _load()
    if cur["provider"] == "local":
        return (cur["local"].get("base_url") or "").strip() or None
    return None


def active_connection() -> dict[str, Any]:
    """The (api_key, base_url) the Anthropic client should be built with."""
    cur = _load()
    if cur["provider"] == "local":
        return {"api_key": (cur["local"].get("api_key") or "").strip(), "base_url": base_url()}
    return {"api_key": (cur["anthropic"].get("api_key") or "").strip(), "base_url": None}


def is_ready() -> bool:
    """True when generation is enabled and the active provider has what it needs
    (a key for Anthropic, a base_url for local)."""
    cur = _load()
    if not cur.get("enabled"):
        return False
    if cur["provider"] == "local":
        return bool((cur["local"].get("base_url") or "").strip() and (cur["local"].get("model") or "").strip())
    return bool((cur["anthropic"].get("api_key") or "").strip())


def use_llm() -> bool:
    """The flag threaded to every module (gates the LLM path vs mock)."""
    return is_ready()


def is_configured() -> bool:
    """Whether the first-run setup wizard has been completed (or seeded from
    .env). Drives whether the wizard auto-opens on boot."""
    return bool(_load().get("configured"))


def status() -> dict[str, Any]:
    """Safe snapshot for the frontend. Never includes the API key itself."""
    cur = _load()
    a, l = cur["anthropic"], cur["local"]
    return {
        "provider": cur["provider"],
        "enabled": bool(cur["enabled"]),
        "configured": bool(cur["configured"]),
        "ready": is_ready(),
        "model": model(),
        "base_url": base_url(),
        "providers": list(PROVIDERS),
        "models": KNOWN_MODELS,
        "default_model": DEFAULT_MODEL,
        "anthropic": {"model": a.get("model") or DEFAULT_MODEL, "has_api_key": bool((a.get("api_key") or "").strip())},
        "local": {
            "base_url": (l.get("base_url") or "").strip(),
            "model": l.get("model") or DEFAULT_MODEL,
            "has_api_key": bool((l.get("api_key") or "").strip()),
        },
    }


def saved_api_key(prov: str) -> str:
    """The currently-stored key for a provider (used server-side to re-test an
    existing connection without the frontend having to resend the secret)."""
    cur = _load()
    if prov in PROVIDERS:
        return (cur[prov].get("api_key") or "").strip()
    return ""


# =========================================================================
# Save (from the wizard)
# =========================================================================
def save(patch: dict[str, Any]) -> dict[str, Any]:
    """Merge a settings patch from the wizard, persist, and return status().

    Shape (every field optional except that a sensible provider must resolve):
        {
          "provider": "anthropic" | "local",
          "enabled": true,
          "anthropic": {"api_key": "...", "model": "..."},
          "local": {"base_url": "...", "api_key": "...", "model": "..."}
        }

    An api_key is only overwritten when a non-empty value is supplied, so the
    frontend can leave it blank to keep the existing key.
    """
    if not isinstance(patch, dict):
        raise ValueError("settings must be an object")

    with _lock:
        cur = copy.deepcopy(_load())
        prov = str(patch.get("provider") or cur["provider"]).strip().lower()
        if prov not in PROVIDERS:
            raise ValueError(f"unknown provider: {prov}")
        cur["provider"] = prov
        if "enabled" in patch:
            cur["enabled"] = bool(patch["enabled"])

        for p in PROVIDERS:
            pp = patch.get(p)
            if not isinstance(pp, dict):
                continue
            tgt = cur.setdefault(p, {})
            if pp.get("model") is not None:
                m = str(pp["model"]).strip()
                tgt["model"] = m or (DEFAULT_MODEL if p == "anthropic" else "")
            if p == "local" and pp.get("base_url") is not None:
                tgt["base_url"] = str(pp["base_url"]).strip()
            # Only overwrite the key when a non-empty value is supplied.
            if pp.get("api_key"):
                tgt["api_key"] = str(pp["api_key"]).strip()

        # Going through the wizard counts as configured, even if the user saved a
        # connection they have not enabled yet.
        cur["configured"] = True
        _persist(cur)
        global _cache
        _cache = cur

    _after_change()
    return status()
