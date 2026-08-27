"""Model wrapper used by every generation module.

Two providers, two transports - both funnel through generate_json / generate_text
so the modules never care which is active:

  * "anthropic"  Anthropic's hosted API via the official SDK (external). The
                 dynasty state + narrative memory go in a cached system block.
  * "local"      Any model on the user's machine via an OpenAI-compatible
                 /chat/completions endpoint (Ollama, LM Studio, llama.cpp, vLLM,
                 ...). Plain HTTP with `requests`; no SDK, no provider lock-in.

The active connection (provider, model, key, base_url) is owned by llm_settings.
Generation stays optional: if nothing is set up, available() is False and callers
fall back to mock content.
"""
from __future__ import annotations

import inspect
import json
import logging
import os
import re
import time
from typing import Any

import requests

from . import llm_settings

try:  # Anthropic SDK is only needed for the hosted provider
    import anthropic
except Exception:  # pragma: no cover - import guard
    anthropic = None  # type: ignore

_client: Any = None
_client_sig: tuple[str, str | None] | None = None

# --- timing + logging ------------------------------------------------------
# Every model call is timed and logged, so a local setup can see what the LLM is
# doing and which calls are slow. Lines go to stdout (the terminal running the
# app) and to data/llm.log, and name the calling module, the model, the context/
# prompt size, the attempt count, the elapsed time, and whether the call returned
# clean JSON or exhausted its retries and left the caller to fall back to mock.
log = logging.getLogger("cfbmod.llm")
if not log.handlers:
    _fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    _sh = logging.StreamHandler()
    _sh.setFormatter(_fmt)
    log.addHandler(_sh)
    try:
        from . import config as _config
        _fh = logging.FileHandler(_config.DATA_DIR / "llm.log", encoding="utf-8")
        _fh.setFormatter(_fmt)
        log.addHandler(_fh)
    except Exception:
        pass
    log.setLevel(logging.INFO)
    log.propagate = False


def _caller_label() -> str:
    """The module.function that asked for generation, for the log line. Walks past
    llm.py's own frames to the first real caller (e.g. 'top_stories.generate')."""
    try:
        for fr in inspect.stack()[2:9]:
            mod = fr.frame.f_globals.get("__name__", "")
            if mod and not mod.endswith(".llm") and mod != "llm":
                return f"{mod.split('.')[-1]}.{fr.function}"
    except Exception:
        pass
    return "?"


def _short_err(exc: Exception | None) -> str:
    s = str(exc or "").strip().replace("\n", " ")
    return (s[:140] + "...") if len(s) > 140 else (s or (type(exc).__name__ if exc else "?"))

# Local generation can be slow on consumer hardware; give it a long read budget.
_LOCAL_TIMEOUT = (10, 600)
_PROBE_TIMEOUT = (5, 30)

# Best-effort context window for local servers that read it from the request (Ollama
# via `options.num_ctx`). The context is also trimmed hard for local models (see
# base.build_context), so this is belt-and-suspenders: it lets the trimmed context plus
# grounding plus output fit without the server's stock ~2048-token default clipping the
# system block. Sent only to Ollama-style endpoints (guarded below); servers that ignore
# unknown fields are unaffected. Set to 0 to disable.
_LOCAL_NUM_CTX = int(os.getenv("CFBMOD_LOCAL_NUM_CTX", "8192"))

# Hosted Anthropic request budget. Without these the SDK defaults to a 600s
# timeout and 2 automatic retries, so a slow or overloaded API blocks the whole
# weekly slate (one stuck module freezes the generation overlay). A bounded
# timeout makes a slow call raise quickly so the module falls back to mock and the
# slate keeps moving. Tunable via .env for users on slow connections.
_ANTHROPIC_TIMEOUT = float(os.getenv("CFBMOD_LLM_TIMEOUT", "90"))
_ANTHROPIC_MAX_RETRIES = int(os.getenv("CFBMOD_LLM_MAX_RETRIES", "1"))


def available() -> bool:
    """True when real generation is enabled and possible for the active provider."""
    if not llm_settings.is_ready():
        return False
    if llm_settings.provider() == "local":
        return True  # uses requests, no SDK needed
    return anthropic is not None


def reset_client() -> None:
    """Drop the cached Anthropic client so the next call rebuilds it. Called by
    llm_settings.save() whenever the connection changes."""
    global _client, _client_sig
    _client = None
    _client_sig = None


# --- Anthropic (hosted) ---------------------------------------------------
def _client_kwargs(api_key: str, base_url: str | None, *, timeout: float | None = None,
                   max_retries: int | None = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"api_key": api_key or "local"}
    if base_url:
        kwargs["base_url"] = base_url
    if timeout is not None:
        kwargs["timeout"] = timeout
    if max_retries is not None:
        kwargs["max_retries"] = max_retries
    return kwargs


def _get_client() -> Any:
    global _client, _client_sig
    conn = llm_settings.active_connection()
    sig = (conn["api_key"], conn["base_url"])
    if _client is None or _client_sig != sig:
        _client = anthropic.Anthropic(**_client_kwargs(
            conn["api_key"], conn["base_url"],
            timeout=_ANTHROPIC_TIMEOUT, max_retries=_ANTHROPIC_MAX_RETRIES))
        _client_sig = sig
    return _client


def _anthropic_system_blocks(system: str, cached_context: str | None) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [{"type": "text", "text": system}]
    if cached_context:
        blocks.append({"type": "text", "text": cached_context, "cache_control": {"type": "ephemeral"}})
    return blocks


def _anthropic_complete(system: str, prompt: str, *, cached_context: str | None,
                        max_tokens: int, temperature: float, json_mode: bool = False) -> str:
    # Claude follows JSON instructions reliably from the prompt, so json_mode is a
    # no-op here (the Messages API has no response_format); it exists for parity.
    client = _get_client()
    resp = client.messages.create(
        model=llm_settings.model(),
        max_tokens=max_tokens,
        temperature=temperature,
        system=_anthropic_system_blocks(system, cached_context),
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")


# --- Local (OpenAI-compatible) --------------------------------------------
def _chat_url(base_url: str) -> str:
    return f"{(base_url or '').strip().rstrip('/')}/chat/completions"


def _local_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _local_complete(system: str, prompt: str, *, cached_context: str | None,
                    max_tokens: int, temperature: float, json_mode: bool = False) -> str:
    conn = llm_settings.active_connection()
    system_text = "\n\n".join(p for p in (system, cached_context) if p)
    payload: dict[str, Any] = {
        "model": llm_settings.model(),
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        # Constrained JSON decoding. Honored by Ollama, LM Studio, vLLM and most
        # OpenAI-compatible servers; makes a small local model emit valid JSON
        # instead of prose or fenced markdown.
        payload["response_format"] = {"type": "json_object"}
    base_url = conn["base_url"] or ""
    if _LOCAL_NUM_CTX and ("11434" in base_url or "ollama" in base_url.lower()):
        # Ollama reads num_ctx from `options`; other OpenAI-compatible servers ignore it.
        payload["options"] = {"num_ctx": _LOCAL_NUM_CTX}
    resp = requests.post(_chat_url(conn["base_url"]), json=payload,
                         headers=_local_headers(conn["api_key"]), timeout=_LOCAL_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


# --- dispatch -------------------------------------------------------------
def _complete(system: str, prompt: str, *, cached_context: str | None,
              max_tokens: int, temperature: float, json_mode: bool = False) -> str:
    if llm_settings.provider() == "local":
        return _local_complete(system, prompt, cached_context=cached_context,
                               max_tokens=max_tokens, temperature=temperature, json_mode=json_mode)
    return _anthropic_complete(system, prompt, cached_context=cached_context,
                               max_tokens=max_tokens, temperature=temperature, json_mode=json_mode)


# How many times to ask the model again when a response will not parse as JSON.
_JSON_ATTEMPTS = 4
_JSON_REMINDER = (
    "\n\nIMPORTANT: Respond with ONE valid JSON value and nothing else. No prose, "
    "no explanation, no markdown code fences. Start your response with { or [ and "
    "end it with the matching } or ]. Every string must use double quotes and be "
    "properly closed."
)


def _ground(prompt: str, grounding: str | None) -> str:
    """Prepend authoritative facts to the user prompt. A small local model will
    ignore facts buried in a long system context but follows them when they sit
    right next to the task, so this is the reliable anti-hallucination lever
    (verified: stops a real team's real-world coach overriding the dynasty one)."""
    if not grounding:
        return prompt
    return (
        "AUTHORITATIVE FACTS for this fictional dynasty. Use these EXACT names. "
        "Never use real-life coaches, players, results, or rankings, even for real "
        "teams. If a fact below conflicts with anything you think you know, the "
        "fact below wins:\n" + grounding + "\n\n" + prompt
    )


def generate_json(
    system: str,
    prompt: str,
    *,
    cached_context: str | None = None,
    grounding: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.6,
) -> Any:
    """Call the model and parse a JSON object/array from the response.

    Generation is meant to ALWAYS come from the model: we use the provider's
    constrained JSON mode and retry several times (each retry nudges harder and
    cools the temperature) before giving up. Callers only fall back to mock
    content on a true, repeated failure. `cached_context` (dynasty state +
    narrative memory) is sent as a cached system block on the hosted provider so
    repeated module calls within a week reuse it cheaply. `grounding` (a short
    authoritative fact block) is prepended to the user prompt where the model
    cannot ignore it.
    """
    if not available():
        raise RuntimeError("LLM generation is not set up (open the in-app setup to connect a model)")
    label = _caller_label()
    prompt = _ground(prompt, grounding)
    ctx_c = len(cached_context or "")
    in_c = len(system or "") + len(prompt)
    t0 = time.perf_counter()

    last_err: Exception | None = None
    for attempt in range(_JSON_ATTEMPTS):
        # Escalate strictness across attempts: nudge the prompt and cool down so a
        # flaky small model converges on clean JSON. The final attempt also drops
        # JSON mode in case the server rejects response_format outright.
        attempt_prompt = prompt if attempt == 0 else prompt + _JSON_REMINDER
        attempt_temp = max(0.1, temperature - 0.25 * attempt)
        json_mode = attempt < _JSON_ATTEMPTS - 1
        a0 = time.perf_counter()
        try:
            text = _complete(system, attempt_prompt, cached_context=cached_context,
                             max_tokens=max_tokens, temperature=attempt_temp, json_mode=json_mode)
            data = _extract_json(text)
            log.info("LLM ok    %-30s %-20s ctx=%dc in=%dc  attempt %d/%d  %.1fs (total %.1fs)",
                     label, llm_settings.model(), ctx_c, in_c, attempt + 1, _JSON_ATTEMPTS,
                     time.perf_counter() - a0, time.perf_counter() - t0)
            try:  # feed the editorial ModelProfile's rolling latency (never fatal)
                from .editorial import profile as _ed_profile
                _ed_profile.record_latency(llm_settings.model(), time.perf_counter() - a0)
            except Exception:
                pass
            return data
        except (ValueError, requests.RequestException) as exc:
            log.warning("LLM retry %-30s attempt %d/%d failed in %.1fs: %s",
                        label, attempt + 1, _JSON_ATTEMPTS, time.perf_counter() - a0, _short_err(exc))
            last_err = exc
    log.error("LLM FAIL  %-30s all %d attempts in %.1fs, caller falls back to MOCK (%s)",
              label, _JSON_ATTEMPTS, time.perf_counter() - t0, _short_err(last_err))
    raise ValueError(f"model did not return valid JSON after {_JSON_ATTEMPTS} attempts: {last_err}")


def generate_text(
    system: str,
    prompt: str,
    *,
    cached_context: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.85,
) -> str:
    """Call the model and return its raw text (no JSON parsing). Used for short
    free-form copy such as generated biographies."""
    if not available():
        raise RuntimeError("LLM generation is not set up (open the in-app setup to connect a model)")
    label = _caller_label()
    t0 = time.perf_counter()
    try:
        out = _complete(system, prompt, cached_context=cached_context, max_tokens=max_tokens, temperature=temperature)
        log.info("LLM ok    %-30s %-20s %.1fs (free text)", label, llm_settings.model(), time.perf_counter() - t0)
        return out
    except Exception as exc:
        log.warning("LLM FAIL  %-30s free-text gen failed in %.1fs: %s", label, time.perf_counter() - t0, _short_err(exc))
        raise


# --- connection test (the wizard's "Test connection" button) --------------
def probe(*, provider: str, model: str = "", api_key: str = "", base_url: str = "") -> dict[str, Any]:
    """Live-test a candidate connection without saving it. Returns
    {ok: bool, message: str, reply?: str}."""
    if provider == "local":
        return _probe_local(model=model, api_key=api_key, base_url=base_url)
    return _probe_anthropic(model=model, api_key=api_key)


def _probe_anthropic(*, model: str, api_key: str) -> dict[str, Any]:
    if anthropic is None:
        return {"ok": False, "message": "The anthropic package is not installed on the backend."}
    if not api_key:
        return {"ok": False, "message": "Enter your Anthropic API key first."}
    mdl = (model or "").strip() or llm_settings.DEFAULT_MODEL
    try:
        client = anthropic.Anthropic(**_client_kwargs(
            api_key.strip(), None, timeout=_PROBE_TIMEOUT[1], max_retries=1))
        resp = client.messages.create(
            model=mdl, max_tokens=16,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        )
        reply = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        used = getattr(resp, "model", mdl)
        return {"ok": True, "message": f"Connected to Anthropic ({used}).", "reply": reply[:80]}
    except Exception as exc:
        return {"ok": False, "message": _friendly_anthropic_error(exc)}


def _probe_local(*, model: str, api_key: str, base_url: str) -> dict[str, Any]:
    base = (base_url or "").strip()
    if not base:
        return {"ok": False, "message": "Enter the local server base URL first."}
    if not (model or "").strip():
        return {"ok": False, "message": "Enter the model name your server serves."}
    try:
        payload = {
            "model": model.strip(),
            "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
            "max_tokens": 16,
        }
        resp = requests.post(_chat_url(base), json=payload, headers=_local_headers(api_key.strip()), timeout=_PROBE_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        reply = (data["choices"][0]["message"]["content"] or "").strip()
        used = data.get("model", model)
        return {"ok": True, "message": f"Connected to local server ({used}).", "reply": reply[:80]}
    except Exception as exc:
        return {"ok": False, "message": _friendly_local_error(exc)}


def _friendly_anthropic_error(exc: Exception) -> str:
    name = type(exc).__name__
    if name == "AuthenticationError":
        return "Authentication failed - check the API key."
    if name == "PermissionDeniedError":
        return "The API key does not have access to that model."
    if name == "NotFoundError":
        return "Model not found - check the model name."
    if name in ("APIConnectionError", "APITimeoutError"):
        return "Could not reach Anthropic - check your connection."
    msg = str(exc).strip()
    return f"{name}: {msg}" if msg else name


def _friendly_local_error(exc: Exception) -> str:
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "Could not reach the server - check the base URL and that it is running."
    if isinstance(exc, requests.exceptions.Timeout):
        return "The server did not respond in time."
    if isinstance(exc, requests.exceptions.HTTPError):
        code = getattr(getattr(exc, "response", None), "status_code", None)
        if code in (401, 403):
            return "The server rejected the request - check the API key."
        if code == 404:
            return "Endpoint not found - the base URL may be missing /v1, or the model name is wrong."
        if code == 400:
            return "Server rejected the request (HTTP 400) - check the model name matches 'ollama list' exactly."
        return f"Server returned HTTP {code}." if code else "The server returned an error."
    if isinstance(exc, (KeyError, IndexError, ValueError, TypeError)):
        return "Unexpected response - is the server OpenAI-compatible?"
    msg = str(exc).strip()
    return f"{type(exc).__name__}: {msg}" if msg else type(exc).__name__


def _extract_json(text: str) -> Any:
    """Pull the first JSON object/array out of a model response.

    Tolerant of the ways small local models wrap output: surrounding prose,
    markdown fences, and trailing text after the JSON value. Scans for the first
    opener and returns the first balanced span (string- and escape-aware)."""
    if not text or not text.strip():
        raise ValueError("empty model response")
    text = text.strip()
    # 1. The whole thing is already JSON.
    try:
        return json.loads(text)
    except ValueError:
        pass
    # 2. The first balanced {...}/[...] span. Backticks are not JSON openers, so
    #    this transparently skips surrounding prose and markdown fences.
    span = _first_balanced_span(text)
    if span is not None:
        try:
            return json.loads(span)
        except ValueError:
            pass
    # 3. Last resort: explicit code-fence extraction.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except ValueError:
            pass
    # 4. Repair the breakage small local models produce: trailing commas, and output
    #    cut off mid-value when they hit the token cap (the unbalanced span the scanner
    #    in step 2 rejects). Strip trailing commas and close any still-open brackets, so a
    #    truncated-but-otherwise-valid response yields usable JSON instead of a hard fail.
    repaired = _repair_json(text)
    if repaired is not None:
        return repaired
    raise ValueError("could not parse JSON from model response")


def _repair_json(text: str) -> Any | None:
    """Best-effort recovery of truncated or trailing-comma JSON. Returns the parsed
    value, or None when it cannot be salvaged."""
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        return None
    s = text[min(starts):]
    # Walk the text tracking open brackets (string- and escape-aware), so we know what is
    # left unclosed at the truncation point and whether we ended inside a string.
    stack: list[str] = []
    in_str = False
    escaped = False
    for ch in s:
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            stack.pop()
    repaired = s + ('"' if in_str else "")
    # Drop a trailing comma or a dangling "key": left by a mid-element cut, then close
    # every still-open bracket in reverse order.
    repaired = re.sub(r'(?:"[^"]*"\s*:\s*)?,?\s*$', "", repaired)
    repaired += "".join("}" if ch == "{" else "]" for ch in reversed(stack))
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
    try:
        return json.loads(repaired)
    except ValueError:
        return None


def _first_balanced_span(text: str) -> str | None:
    """The first balanced {...} or [...] span, honoring quoted strings/escapes."""
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        return None
    start = min(starts)
    stack: list[str] = []
    in_str = False
    escaped = False
    pairs = {"}": "{", "]": "["}
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if not stack or stack[-1] != pairs[ch]:
                return None
            stack.pop()
            if not stack:
                return text[start : i + 1]
    return None
