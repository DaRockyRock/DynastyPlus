"""Flask application.

Serves the local web UI and exposes one endpoint per generation module plus
dynasty/teams/pipeline endpoints. Each module is independently callable so the
frontend can regenerate a single section without rerunning the full pipeline.
"""
from __future__ import annotations

import hashlib

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from . import budget, cache, config, conferences, customization, directory, dynasties, feed_state, inbox, interview, llm, llm_settings, messages, pipeline, schema, teams, world, world_events
from .modules import REGISTRY, phone, article_detail
from .modules import base as module_base
from .watcher import SaveWatcher

app = Flask(__name__, static_folder=None)
_watcher = SaveWatcher()

# Image uploads (Customize flow). Kept small and local: hashed filenames so the
# same image is stored once, extension allowlist, served back from /uploads.
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp", "svg", "avif"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


# --- frontend (Vite build) ------------------------------------------------
_BUILD_HINT = (
    "<html><body style='font-family:sans-serif;background:#0a0e14;color:#e9eef5;"
    "padding:48px'><h2>Frontend not built yet</h2><p>Run the build once:</p>"
    "<pre style='background:#141a24;padding:16px;border-radius:10px'>"
    "cd frontend\nnpm install\nnpm run build</pre>"
    "<p>Or develop with hot reload: <code>npm run dev</code> (Vite proxies /api here).</p>"
    "</body></html>"
)


def _serve_index():
    """Serve the SPA shell with no-cache headers. The JS/CSS bundles are content
    hashed (safe to cache forever), but index.html points at the current bundle,
    so it must always revalidate. Otherwise a rebuild has no effect until the
    browser cache expires: the stale index.html keeps loading the old bundle."""
    resp = send_from_directory(config.FRONTEND_DIST, "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    # send_from_directory attaches `Content-Disposition: inline; filename=...`,
    # which Safari treats as a file to hand off rather than a page to render
    # (the tab ends up on about:blank). Drop it so the HTML renders inline.
    resp.headers.pop("Content-Disposition", None)
    return resp


@app.route("/")
def index():
    index_file = config.FRONTEND_DIST / "index.html"
    if not index_file.exists():
        return _BUILD_HINT, 200
    return _serve_index()


@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    """Serve a user-uploaded image. Registered before the SPA catch-all."""
    return send_from_directory(config.UPLOADS_DIR, filename)


@app.route("/<path:path>")
def static_files(path: str):
    target = config.FRONTEND_DIST / path
    if not target.exists():
        # SPA fallback: unknown non-API paths return index.html.
        return _serve_index()
    return send_from_directory(config.FRONTEND_DIST, path)


# --- meta / config --------------------------------------------------------
@app.get("/api/config")
def api_config():
    info = config.runtime_summary()
    info["watcher"] = _watcher.info()
    info["modules"] = list(REGISTRY.keys())
    return jsonify(info)


@app.get("/api/schema")
def api_schema():
    return jsonify({"description": schema.SCHEMA_DESCRIPTION, "required": schema.REQUIRED_PATHS})


# --- LLM connection (the setup wizard) ------------------------------------
@app.get("/api/llm")
def api_llm():
    """Current connection status. Never includes the API key itself."""
    return jsonify(llm_settings.status())


@app.put("/api/llm")
def api_llm_set():
    """Save the connection from the setup wizard. Clears the per-week cache so
    content regenerates with the new model."""
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(llm_settings.save(body))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/llm/test")
def api_llm_test():
    """Live-test a candidate connection without saving it. If the api key is
    omitted, fall back to the one already saved for that provider so an existing
    connection can be re-tested without resending the secret."""
    body = request.get_json(silent=True) or {}
    provider = (body.get("provider") or llm_settings.provider()).strip().lower()
    api_key = (body.get("api_key") or "").strip() or llm_settings.saved_api_key(provider)
    result = llm.probe(
        provider=provider,
        model=body.get("model") or "",
        api_key=api_key,
        base_url=body.get("base_url") or "",
    )
    return jsonify(result)


@app.get("/api/teams")
def api_teams():
    refresh = request.args.get("refresh") == "1"
    return jsonify(teams.get_all_teams(force_refresh=refresh))


@app.get("/api/conferences")
def api_conferences():
    return jsonify(conferences.all_conferences())


# --- customization (the Customize flow) -----------------------------------
@app.get("/api/customization")
def api_customization():
    """Full editor payload: schema, current values, and which sections changed."""
    return jsonify(customization.get_state())


@app.put("/api/customization/<section>")
def api_customization_set(section: str):
    body = request.get_json(silent=True) or {}
    if "value" not in body:
        return jsonify({"error": "missing 'value'"}), 400
    try:
        value = customization.set_section(section, body["value"])
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"section": section, "value": value})


@app.post("/api/customization/<section>/reset")
def api_customization_reset(section: str):
    try:
        value = customization.reset_section(section)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"section": section, "value": value})


@app.post("/api/customization/reset")
def api_customization_reset_all():
    customization.reset_all()
    return jsonify({"ok": True})


@app.post("/api/customization/<section>/generate-person")
def api_customization_generate_person(section: str):
    """Generate a fresh personality + bio for a new person in a section
    (e.g. when a recruit is added to the board)."""
    body = request.get_json(silent=True) or {}
    seed = body.get("seed") or {}
    try:
        result = customization.generate_person(section, seed, use_llm=llm_settings.use_llm())
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(result)


@app.post("/api/upload")
def api_upload():
    """Store an uploaded image and return its served URL."""
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "no file"}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXT:
        return jsonify({"error": f"unsupported type: .{ext}"}), 415

    data = file.read()
    if not data:
        return jsonify({"error": "empty file"}), 400
    if len(data) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "file too large (max 8MB)"}), 413

    digest = hashlib.sha1(data).hexdigest()[:16]
    name = secure_filename(f"{digest}.{ext}")
    path = config.UPLOADS_DIR / name
    if not path.exists():
        try:
            path.write_bytes(data)
        except OSError as exc:
            return jsonify({"error": str(exc)}), 500
    return jsonify({"url": f"/uploads/{name}", "name": name})


# --- dynasty / state ------------------------------------------------------
def _yw():
    year = request.args.get("year", type=int)
    week = request.args.get("week", type=int)
    ptr = pipeline.current_pointer()
    return (year if year is not None else ptr["year"], week if week is not None else ptr["week"])


@app.get("/api/dynasty")
def api_dynasty():
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    problems = schema.validate(dynasty)
    return jsonify({"dynasty": dynasty, "valid": not problems, "problems": problems})


@app.get("/api/state")
def api_state():
    return jsonify({
        "pointer": pipeline.current_pointer(),
        "cached_weeks": cache.list_cached_weeks(),
        "status": pipeline.status(),
        "save_hash": pipeline.save_hash(),
        "save_present": pipeline.save_present(),
        # The save's own current season/week, so the UI can auto-advance when the
        # Simulator moves the week forward (without a manual rescan).
        "save": pipeline.save_pointer(),
        "pending_actions": inbox.pending_count(pipeline.current_pointer()["year"]),
        # Bumps whenever the world reacts to something the coach said, so the
        # frontend can refresh the feed (and, later, messages) without a full pass.
        "world_version": world_events.version(pipeline.current_pointer()["year"]),
    })


# --- dynasty library + scan (the explicit Simulator -> companion handoff) ---
@app.get("/api/dynasties")
def api_dynasties():
    """The dynasties the companion has scanned in, for the landing screen, plus
    whether a (possibly new/updated) save is currently sitting in the drop spot."""
    reg = dynasties.list_all()
    cur = dynasties.current()
    return jsonify({
        "dynasties": reg["dynasties"],
        "current": reg["current"],
        "save_present": pipeline.save_present(),
        # Hint that scanning would pick up something new (a new program or a newer week/hash).
        "save_hash": pipeline.save_hash(),
        "current_hash": cur["hash"] if cur else None,
    })


@app.post("/api/scan")
def api_scan():
    """Read the save the Simulator wrote and register/update a dynasty."""
    res = pipeline.scan()
    if not res.get("present"):
        return jsonify({"present": False,
                        "error": "No save found. Start a dynasty in the Simulator first."}), 404
    return jsonify(res)


@app.post("/api/dynasty/select")
def api_dynasty_select():
    body = request.get_json(silent=True) or {}
    entry = pipeline.select_dynasty(body.get("id", ""))
    if not entry:
        return jsonify({"error": "unknown dynasty"}), 404
    return jsonify({"dynasty": entry})


@app.get("/api/status")
def api_status():
    return jsonify(pipeline.status())


# --- generation -----------------------------------------------------------
@app.get("/api/module/<module_key>")
def api_module(module_key: str):
    if module_key not in REGISTRY:
        return jsonify({"error": f"unknown module: {module_key}"}), 404
    year, week = _yw()
    regenerate = request.args.get("regenerate") == "1"
    try:
        content = pipeline.generate_module(module_key, year=year, week=week, regenerate=regenerate)
    except Exception as exc:  # surface generation errors to the UI
        return jsonify({"error": str(exc)}), 500
    return jsonify(content)


@app.post("/api/generate")
def api_generate():
    body = request.get_json(silent=True) or {}
    year, week = _yw()
    regenerate = bool(body.get("regenerate"))
    results = pipeline.run_full(year=year, week=week, regenerate=regenerate)
    return jsonify({"week": week, "year": year, "results": list(results.keys())})


@app.post("/api/advance")
def api_advance():
    body = request.get_json(silent=True) or {}
    ptr = pipeline.current_pointer()
    year = int(body.get("year", ptr["year"]))
    week = int(body.get("week", ptr["week"] + 1))
    regenerate = bool(body.get("regenerate"))
    results = pipeline.advance_to(year, week, regenerate=regenerate)
    return jsonify({"week": week, "year": year, "results": list(results.keys()),
                    "coaching_search": "coaching_search" in results})


# --- phone ----------------------------------------------------------------
@app.post("/api/article")
def api_article():
    body = request.get_json(silent=True) or {}
    article = body.get("article")
    if not article:
        return jsonify({"error": "missing article"}), 400
    ptr = pipeline.current_pointer()
    year = int(body.get("year", ptr["year"]))
    week = int(body.get("week", ptr["week"]))
    dynasty = pipeline.load_dynasty(year, week)
    detail = article_detail.expand(article, dynasty, year=year, week=week, use_llm=llm_settings.use_llm())
    return jsonify(detail)


@app.get("/api/phone/threads")
def api_phone_threads():
    """Persisted conversation threads for the season, so the phone rehydrates
    its chat history on boot instead of starting empty."""
    year, _week = _yw()
    return jsonify({"threads": messages.threads(year)})


@app.post("/api/phone/message")
def api_phone_message():
    body = request.get_json(silent=True) or {}
    contact_id = body.get("contact_id", "")
    message = body.get("message", "")
    action = body.get("action")
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    res = phone.reply(contact_id, message, dynasty, year=year, week=week,
                      use_llm=llm_settings.use_llm(), action=action)
    if res.get("error"):
        return jsonify(res), 404
    # The world hears what the coach says. The reaction engine judges the message
    # and, when it is newsworthy, breaks it on the feed, files an article when it
    # rises to a real story, and (in later slices) prompts people to text him back,
    # all proportional to how big it is. Runs in the background; the frontend
    # notices the world-version bump on /api/state and refreshes a beat later.
    # This is the single home for "the coach said something on the record" (it
    # supersedes the old blanket news regeneration).
    if message.strip():
        channel = (res.get("contact") or {}).get("category") or ""
        contact_full = directory.by_id(contact_id) or res.get("contact")
        # Remember any commitment the coach just made (span-verified), so the world can
        # hold him to it later (editorial promise tracking).
        try:
            from .editorial import promises
            promises.scan(contact_full, message, year, week)
        except Exception:
            pass
        world.react_async(contact_full, message, dynasty, year=year, week=week,
                          channel=channel, use_llm=llm_settings.use_llm())
        res["world"] = {"reacting": True}
    return jsonify(res)


@app.post("/api/phone/open")
def api_phone_open():
    """Resolve any hovered person (by name, plus an optional kind hint) into a
    textable contact, reusing the curated thread when the person is already on the
    phone roster. Resolution is authoritative here; the client never mints ids."""
    body = request.get_json(silent=True) or {}
    contact = directory.resolve(body.get("name", ""), body.get("kind"))
    if not contact:
        return jsonify({"error": "unknown person"}), 404
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    return jsonify({"contact": module_base.sanitize(phone.enrich_one(contact, dynasty, year))})


@app.post("/api/phone/read")
def api_phone_read():
    """Mark a conversation read: clear the unread flag on its inbound texts once
    the coach has opened it. Returns the remaining unread count per contact."""
    body = request.get_json(silent=True) or {}
    contact_id = body.get("contact_id", "")
    year, _week = _yw()
    messages.mark_read(year, contact_id)
    return jsonify({"unread": messages.unread_counts(year)})


@app.post("/api/phone/unread")
def api_phone_unread():
    """Mark the most recent reply in a thread unread, so a reply that arrived while
    the coach was not viewing the conversation persists as a notification across
    reloads and week advances. Returns the unread count per contact."""
    body = request.get_json(silent=True) or {}
    contact_id = body.get("contact_id", "")
    year, _week = _yw()
    messages.mark_reply_unread(year, contact_id)
    return jsonify({"unread": messages.unread_counts(year)})


# --- social feed ----------------------------------------------------------
# The timeline itself rides the generic GET /api/module/feed. These endpoints own
# only the coach's interaction state: which posts he liked, and the per-week seen
# marker that clears the unseen badge.
@app.get("/api/feed/state")
def api_feed_state():
    year, _week = _yw()
    return jsonify(feed_state.state(year))


@app.post("/api/feed/like")
def api_feed_like():
    body = request.get_json(silent=True) or {}
    post_id = body.get("post_id", "")
    year, _week = _yw()
    liked = feed_state.toggle_like(year, post_id)
    return jsonify({"post_id": post_id, "liked": liked, "likes": feed_state.liked(year)})


@app.post("/api/feed/seen")
def api_feed_seen():
    body = request.get_json(silent=True) or {}
    year, week = _yw()
    feed_state.mark_seen(year, int(body.get("week", week)))
    return jsonify({"ok": True, "seen": feed_state.state(year)["seen"]})


# --- post-game press conference (the interactive interview) ----------------
# When the user's game finishes, five local reporters ask one question each. The
# coach's answers are public and feed the news + media texts. The news/inbound
# modules are held back (pipeline.HELD_FOR_PRESSER) until the presser completes,
# then pipeline.run_post_presser regenerates them (and builds any weekly module
# deferred to after the interview) so everything reflects his answers.
def _presser_hits_the_world(year: int, week: int, game_key: str, dynasty: dict) -> None:
    """A completed press conference is the coach's biggest public moment, so the
    world judges it like any on-the-record statement: a combustible presser (firing
    threats, questioning his own future, shots at players) breaks across the feed
    and news, while a measured one passes quietly. Public channel, never anonymous.
    Inbound is left to the (presser-aware) weekly news phase so the AD and players
    are not double-texted about the same remarks. Fire-and-forget."""
    statement = interview.public_statement(interview.get(year, game_key))
    if statement:
        # min_tier=2: only a presser that is a genuine story (a meltdown, a firing
        # threat, an injury or a bombshell) breaks on the feed. A routine presser
        # passes quietly, it still feeds the news + presser-aware texts.
        world.react_async(None, statement, dynasty, year=year, week=week, channel="Press conference",
                          use_llm=llm_settings.use_llm(), inbound=False, min_tier=2)


@app.get("/api/interview/pending")
def api_interview_pending():
    """Whether a presser is owed for the user's last game (drives the modal)."""
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    return jsonify({"pending": interview.pending(year, dynasty)})


@app.post("/api/interview/start")
def api_interview_start():
    """Begin (or resume) the presser: returns the reporters and the first question."""
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    res = interview.start(year, week, dynasty, use_llm=llm_settings.use_llm())
    if res is None:
        return jsonify({"error": "no completed game to interview about"}), 404
    return jsonify(res)


@app.post("/api/interview/answer")
def api_interview_answer():
    """Submit the coach's answer; returns a rare follow-up, the next reporter, or
    completion. On completion, releases the news gate."""
    body = request.get_json(silent=True) or {}
    game_key = body.get("game_key", "")
    text = body.get("answer", "")
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    res = interview.answer(year, week, game_key, dynasty, text, use_llm=llm_settings.use_llm())
    if res is None:
        return jsonify({"error": "no active presser for that game"}), 404
    if res.get("status") == "complete":
        _presser_hits_the_world(year, week, game_key, dynasty)
        # The week's coverage (and, on an advance, the rest of the new week) builds
        # in the background now that the coach has spoken; the frontend pulls it in
        # without a blocking overlay.
        pipeline.run_post_presser_async(year, week)
    return jsonify(res)


@app.post("/api/interview/skip")
def api_interview_skip():
    """Decline the rest: the LLM auto-answers the remaining questions in the coach's
    voice, completes the presser, and releases the news gate."""
    body = request.get_json(silent=True) or {}
    game_key = body.get("game_key", "")
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    res = interview.skip(year, week, game_key, dynasty, use_llm=llm_settings.use_llm())
    if res is None:
        return jsonify({"error": "no active presser for that game"}), 404
    if res.get("status") == "complete":
        _presser_hits_the_world(year, week, game_key, dynasty)
        pipeline.run_post_presser_async(year, week)  # week's coverage builds in the background
    return jsonify(res)


@app.get("/api/interview/state")
def api_interview_state():
    """The transcript for a given game_key, for reviewing a completed presser."""
    year, _week = _yw()
    game_key = request.args.get("game_key", "")
    presser = interview.get(year, game_key)
    if not presser:
        return jsonify({"presser": None})
    return jsonify({"presser": presser})


# --- NIL / Dynasty Points budget ------------------------------------------
# Read-only in Dynasty+: the budget is the Simulator's, read straight from the
# save (dynasty["budget"]). Coach actions are queued to the companion inbox
# below; the Simulator drains + applies them and rewrites the save.
@app.get("/api/budget")
def api_budget():
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    # Cold start (no save yet) has no embedded budget; fall back to a seed
    # snapshot from the dynasty blueprint so the UI still renders.
    snap = dynasty.get("budget") or budget.snapshot(year, week, dynasty)
    return jsonify(snap)


# --- companion inbox (the write-back channel to the Simulator) ------------
@app.get("/api/inbox")
def api_inbox():
    year, _week = _yw()
    return jsonify({"pending": inbox.pending(year), "count": inbox.pending_count(year)})


@app.post("/api/inbox/nil-offer")
def api_inbox_nil_offer():
    body = request.get_json(silent=True) or {}
    eid = body.get("entity_id", "")
    kind = body.get("kind", "recruit")
    amount = int(body.get("amount", 0))
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    effect = budget.project_nil_offer(eid, kind, amount, dynasty)
    if effect.get("error"):
        return jsonify(effect), 404
    record = inbox.append({"kind": "nil_offer", "entity_id": eid, "entity_kind": kind,
                           "amount": amount, "year": year, "week": week})
    return jsonify({"queued": True, "action": record, "effect": effect,
                    "snapshot": dynasty.get("budget")})


@app.post("/api/inbox/recruiting-action")
def api_inbox_recruiting_action():
    body = request.get_json(silent=True) or {}
    eid = body.get("entity_id", "")
    action_key = body.get("action_key", "")
    year, week = _yw()
    dynasty = pipeline.load_dynasty(year, week)
    effect = budget.project_recruiting_action(eid, action_key, dynasty)
    if effect.get("error"):
        return jsonify(effect), 404
    record = inbox.append({"kind": "recruiting_action", "entity_id": eid,
                           "action_key": action_key, "year": year, "week": week})
    return jsonify({"queued": True, "action": record, "effect": effect,
                    "snapshot": dynasty.get("budget")})


@app.post("/api/inbox/allocate")
def api_inbox_allocate():
    body = request.get_json(silent=True) or {}
    allocations = body.get("allocations") or {}
    year, week = _yw()
    record = inbox.append({"kind": "allocate", "allocations": allocations,
                           "year": year, "week": week})
    return jsonify({"queued": True, "action": record,
                    "effect": {"kind": "allocate", "allocations": allocations, "pending": True}})


# --- watcher --------------------------------------------------------------
@app.post("/api/watcher/start")
def api_watcher_start():
    ok = _watcher.start()
    return jsonify({"started": ok, "info": _watcher.info()})


@app.post("/api/watcher/stop")
def api_watcher_stop():
    _watcher.stop()
    return jsonify({"stopped": True, "info": _watcher.info()})


def create_app() -> Flask:
    # The companion is passive until the user acts: it opens to the dynasty
    # library and does nothing until they click Scan (which reads the save the
    # Simulator wrote). No auto-watch, no auto-generate on boot.
    return app
