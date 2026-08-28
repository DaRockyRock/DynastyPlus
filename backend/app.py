"""Flask application for the local Dynasty+ Tools editor."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import threading

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from . import app_settings, bowl_editor, config, conferences, confsetup, dynasties, gamefind, modtools, pipeline, playoff, playoff_live, polledit, recruiting_fix, resume, schedrules, schema, school_sites, teams
from .saveparse import stadiums as savestadiums

def pin_web_mime_types() -> None:
    """Pin the Content-Type of our own web assets, ignoring the machine's
    registry.

    Flask serves the Vite build's JS/CSS with a Content-Type from
    mimetypes.guess_type(). On Windows that map is seeded from the registry
    (HKCR\\.js\\"Content Type"), and on many machines that value is wrong or
    missing: other software points ".js" at "text/plain". When the bundle's
    entry module (<script type="module">) is served as text/plain, Chromium
    (our Electron window) refuses to execute it under its strict module MIME
    check, so the app hangs on the boot screen with a blank/green window
    (reported in the wild; users worked around it by hand-editing the registry).

    mimetypes.add_type() runs init() first (reading the registry) and then
    overrides, so calling it here makes our value win regardless of the
    machine's registry state. Idempotent, so it is safe to call more than once.
    """
    for ext, ctype in {
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".map": "application/json",
        ".svg": "image/svg+xml",
        ".wasm": "application/wasm",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".otf": "font/otf",
    }.items():
        mimetypes.add_type(ctype, ext)


pin_web_mime_types()

app = Flask(__name__, static_folder=None)


@app.errorhandler(Exception)
def _unhandled_error(exc):
    """Every unhandled exception becomes a JSON error the UI can actually
    show, and a traceback lands in DATA_DIR/error.log for bug reports.
    Without this, any crash surfaced as Flask's HTML 500 page and the UI
    toast said only "Request failed: 500", which is undiagnosable from a
    user report (observed: "moved files ... just got a 500 error code")."""
    from werkzeug.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return exc  # real 4xx/5xx responses (404s etc.) pass through
    import traceback
    from datetime import datetime
    from flask import request as _rq
    line = (f"{datetime.now().isoformat(timespec='seconds')} "
            f"{_rq.method} {_rq.path}\n{traceback.format_exc()}\n")
    try:
        with (config.DATA_DIR / "error.log").open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass
    app.logger.error(line)
    return jsonify({"error": f"{type(exc).__name__}: {exc} "
                             "(details in error.log next to the app's data)"}), 500


# Image uploads for custom conference logos. Kept small and local: hashed filenames so the
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


@app.route("/game-assets/<path:filename>")
def game_asset(filename: str):
    """Serve art extracted from the local CFB 27 install
    (scripts/extract_game_assets.py -> DATA_DIR/game_assets). Content only
    changes when the extractor reruns, so let the browser cache it for a day."""
    resp = send_from_directory(config.DATA_DIR / "game_assets", filename)
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


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
    info["autosync_enabled"] = app_settings.autosync_enabled()
    return jsonify(info)


@app.post("/api/autosync")
def api_autosync():
    """Toggle the background auto-sync master switch (per app; the header
    toggle). When off, a new game save triggers no automatic poll push or
    playoff write; the user drives sync/apply by hand."""
    body = request.get_json(silent=True) or {}
    enabled = app_settings.set_autosync_enabled(bool(body.get("enabled", True)))
    return jsonify({"autosync_enabled": enabled})


@app.get("/api/schema")
def api_schema():
    return jsonify({"description": schema.SCHEMA_DESCRIPTION, "required": schema.REQUIRED_PATHS})


# --- first-run setup (game install + saves folder + art extraction) --------
# Tools needs the saves folder (to Scan) and the game art (logos,
# helmets, fonts). Lets a non-programmer point the app at a non-standard install
# and pull the art with one button, no command line.
_extract_lock = threading.Lock()
_extract_job = {"running": False, "stage": None, "done": 0, "total": 0,
                "error": None, "summary": None}


def _art_present() -> bool:
    """True once game art has been extracted (a manifest with team entries)."""
    mani = config.DATA_DIR / "game_assets" / "manifest.json"
    try:
        return bool(json.loads(mani.read_text(encoding="utf-8")).get("teams"))
    except (OSError, ValueError):
        return False


# Dynasty+ Tools only needs the marks its editors show (team + conference
# logos, the UI/bowl/rivalry icons) and the game fonts.
_TOOLS_ART_STAGES = ["teams", "conferences", "fonts", "ui"]


def _run_extraction(game_root: str) -> None:
    from .assets import extract_art
    try:
        def progress(stage, done, total):
            with _extract_lock:
                _extract_job.update(stage=stage, done=done, total=total)
        summary = extract_art.run(game_root=game_root, stages=_TOOLS_ART_STAGES, progress=progress)
        with _extract_lock:
            _extract_job.update(running=False, stage="done", summary=summary, error=None)
    except Exception as exc:  # noqa: BLE001  (report any failure to the UI)
        with _extract_lock:
            _extract_job.update(running=False, error=str(exc))


@app.get("/api/setup/status")
def api_setup_status():
    st = app_settings.status()
    st["art_present"] = _art_present()
    with _extract_lock:
        st["extracting"] = _extract_job["running"]
    # Setup is "done enough" to use the app once the saves folder exists and the
    # game art has been pulled. (Saves usually auto-resolve; art needs the click.)
    st["complete"] = bool(st["save_path_exists"] and st["art_present"])
    return jsonify(st)


@app.get("/api/setup/detect")
def api_setup_detect():
    return jsonify({"installs": gamefind.detect_game_installs(),
                    "saves": gamefind.detect_saves_folders()})


@app.post("/api/setup/paths")
def api_setup_paths():
    body = request.get_json(silent=True) or {}
    app_settings.set_paths(save_path=body.get("save_path"),
                           game_root=body.get("game_root"))
    return jsonify(app_settings.status())


@app.post("/api/setup/extract")
def api_setup_extract():
    body = request.get_json(silent=True) or {}
    game_root = (body.get("game_root") or "").strip()
    if game_root:
        app_settings.set_paths(game_root=game_root)
    root = str(app_settings.resolve_game_root())
    if not gamefind.is_valid_install(root):
        return jsonify({"error": "not_an_install", "game_root": root}), 400
    with _extract_lock:
        if _extract_job["running"]:
            return jsonify({"error": "already_running"}), 409
        _extract_job.update(running=True, stage="starting", done=0, total=0,
                            error=None, summary=None)
    threading.Thread(target=_run_extraction, args=(root,), daemon=True).start()
    return jsonify({"started": True, "game_root": root})


@app.get("/api/setup/extract/status")
def api_setup_extract_status():
    with _extract_lock:
        return jsonify(dict(_extract_job))


@app.get("/api/teams")
def api_teams():
    refresh = request.args.get("refresh") == "1"
    return jsonify(teams.get_all_teams(force_refresh=refresh))


@app.get("/api/conferences")
def api_conferences():
    merged = conferences.all_conferences()
    merged.update(confsetup.conference_registry())
    return jsonify(merged)


# --- playoff format (the custom CFP) ---------------------------------------
@app.get("/api/playoff/format")
def api_playoff_format():
    return jsonify({
        "format": playoff.get_format(),
        "default": playoff.normalize_format(playoff.DEFAULT_FORMAT),
        "customized": playoff.is_customized(),
        "bowls": playoff.BOWLS,
        # Whether Dynasty+ drives the postseason (True) or the game runs its own
        # native 12-team playoff (False, the opt-in default).
        "enabled": playoff_live.is_enabled(),
    })


@app.post("/api/playoff/config")
def api_playoff_config():
    """Turn the custom playoff bracket automation on or off for this dynasty.
    OFF (the default) leaves the game's native 12-team playoff untouched; custom
    conferences and custom polls still seed it."""
    body = request.get_json(silent=True) or {}
    cfg = playoff_live.set_config(body)
    return jsonify({"config": cfg})


@app.put("/api/playoff/format")
def api_playoff_format_set():
    body = request.get_json(silent=True) or {}
    fmt = playoff.normalize_format(body.get("format") or {})
    problems = playoff.validate_format(fmt)
    if problems:
        return jsonify({"error": "; ".join(problems), "problems": problems}), 400
    saved = playoff.set_format(fmt)
    return jsonify({"format": saved, "customized": True})


@app.post("/api/playoff/format/reset")
def api_playoff_format_reset():
    fmt = playoff.reset_format()
    return jsonify({"format": fmt, "customized": False})


@app.get("/api/playoff/live")
def api_playoff_live():
    """The live custom-playoff bracket over the real save: a projected field
    during the regular season, the frozen/seeded bracket once the CCGs are
    official, live results as rounds complete, and the champion at the end.
    CAPTURE-ONLY by default: results are read and the bracket advances, and
    `needs_write` reports whether an apply would change the save. Writes go
    through POST /api/playoff/apply (the update button) so the save never
    changes underneath a running game session."""
    write = request.args.get("write", "0") not in ("0", "false")
    out = playoff_live.sync(write=write)
    out["history"] = playoff_live.history()
    out["autosync"] = playoff_live.autosync_info()
    out["enabled"] = playoff_live.is_enabled()
    return jsonify(out)


@app.post("/api/playoff/apply")
def api_playoff_apply():
    """The 'update dynasty file' button: write pending playoff matchups (or a
    due rewind) into the save NOW. Meant to be pressed while the dynasty is
    closed in CFB 27 (at the game's main menu), so the game picks the changes
    up on its next load instead of clobbering them from memory."""
    out = playoff_live.sync(write=True)
    out["history"] = playoff_live.history()
    out["enabled"] = playoff_live.is_enabled()
    return jsonify(out)


@app.get("/api/bowls")
def api_bowls():
    """The editable nonplayoff bowl schedule for the selected postseason.

    It appears only after a
    custom playoff field is selected, and subtracts every bowl and save record
    reserved by that playoff layout.
    """
    if not playoff_live.is_enabled():
        return jsonify({"available": False,
                        "reason": "Turn on the custom playoff before assigning bowls."})
    playoff_live.sync(write=False)
    return jsonify(bowl_editor.get_state(playoff_live._load_state()))


@app.post("/api/bowls/apply")
def api_bowls_apply():
    """Validate, freeze, and write the season's complete bowl schedule."""
    if not playoff_live.is_enabled():
        return jsonify({"error": "the custom playoff is not enabled"}), 400
    # Capture a newly reached selection boundary before taking the write lock.
    playoff_live.sync(write=False)
    body = request.get_json(silent=True) or {}
    try:
        out = bowl_editor.apply(body.get("assignments"), auto=bool(body.get("auto")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(out)


@app.get("/api/playoff/stadiums")
def api_playoff_stadiums():
    """The game's real stadium list for the neutral-site picker: every stadium
    in the active dynasty's save (stable index + derived name), with the
    game's own venue-pool memberships so the UI can put the marquee neutral
    sites first. Empty when no real save is readable (mock/dev dynasties)."""
    payload = confsetup.current_payload()
    if payload is None:
        return jsonify({"stadiums": [], "available": False})
    try:
        rows = savestadiums.annotate(
            payload, bowl_catalog=playoff.BOWLS,
            school_stadium_names=school_sites.STADIUM_NAMES)
    except ValueError:
        return jsonify({"stadiums": [], "available": False})
    return jsonify({"available": True, "stadiums": [
        {"index": s.index, "name": s.name, "city": s.city,
         "home_of": s.home_of, "pools": list(s.pools)}
        for s in rows
    ]})


@app.post("/api/playoff/preview")
def api_playoff_preview():
    """Build a bracket from the current rankings for a DRAFT format without
    saving it (the format editor's live preview). Validation problems come back
    in-band so the editor can render them next to the controls."""
    body = request.get_json(silent=True) or {}
    year, week = _yw()
    fmt = playoff.normalize_format(body.get("format") or playoff.get_format())
    problems = playoff.validate_format(fmt)
    if problems:
        return jsonify({"bracket": None, "problems": problems})
    dynasty = pipeline.load_dynasty(year, week)
    try:
        bracket = playoff.build_bracket(dynasty, fmt)
    except playoff.BracketError as exc:
        return jsonify({"bracket": None, "problems": [str(exc)]})
    # How this format will run in CFB 27: stock, native for 16 or fewer teams,
    # or hybrid with an early rewind phase and a native final-16 handoff.
    return jsonify({"bracket": bracket, "problems": [],
                    "mode": playoff_live.classify_mode(bracket)})


# --- poll editor (the national polls customizer) ---------------------------
# The save's polls are full
# per-team orderings (saveparse/polls.py); the editor hands any of them to
# the user (manual order or a computer rating) and auto-pushes on every new
# game save through the playoff watcher (backend/polledit.py).

@app.get("/api/polls")
def api_polls():
    return jsonify(polledit.get_state())


@app.put("/api/polls/config")
def api_polls_config():
    body = request.get_json(silent=True) or {}
    try:
        cfg = polledit.set_config(body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    # config changes take effect immediately: re-assert the polls right away
    # (auto_apply no-ops when auto-push is off or everything is game-owned)
    applied = polledit.auto_apply()
    return jsonify({"config": cfg, "applied": applied})


@app.post("/api/polls/apply")
def api_polls_apply():
    """The explicit 'push my poll now' button (auto-push covers the weekly
    case; this is for right-after-editing feedback and for auto-push off)."""
    body = request.get_json(silent=True) or {}
    out = polledit.apply(force=bool(body.get("force")))
    return jsonify(out)


@app.post("/api/polls/preview")
def api_polls_preview():
    """Rank the current season with a draft algorithm choice WITHOUT saving
    anything (the algorithm picker's live preview)."""
    body = request.get_json(silent=True) or {}
    try:
        out = polledit.preview(body.get("algorithm") or "colley",
                               body.get("poll") or "cfp")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(out)


# --- rankings hub (team resumes + the national scoreboard) -----------------
# Read-only views of
# the save's own results (backend/resume.py); official scores only, so the
# engine's pre-simmed current week never leaks.

@app.get("/api/rankings/resume/<int:row>")
def api_rankings_resume(row: int):
    """One team's season resume: results with opponent records/current ranks,
    quality wins and losses, and the summary the comparison view reads."""
    return jsonify(resume.team_resume(row))


@app.get("/api/rankings/scoreboard")
def api_rankings_scoreboard():
    """The current week's slate (the engine's own queue) plus the latest
    official finals league-wide."""
    return jsonify(resume.scoreboard())


# --- conference setup (the custom conferences editor) ----------------------
@app.get("/api/conferences/setup")
def api_conference_setup():
    return jsonify(confsetup.get_state())


@app.put("/api/conferences/setup")
def api_conference_setup_save():
    body = request.get_json(silent=True) or {}
    try:
        state = confsetup.set_state(body.get("conferences") or [])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(state)


@app.get("/api/conferences/historic-logos")
def api_conference_historic_logos():
    """The game's classic conference marks, grouped by conference key, so the
    identity editor can offer them as a logo. Extracts them on first call."""
    return jsonify(confsetup.historic_logos())


@app.post("/api/conferences/setup/reset")
def api_conference_setup_reset():
    state = confsetup.reset()
    return jsonify(state)


# --- custom schedule generator ----------------------------------------------
# Rules, feasibility, generation, and the
# explicit apply that patches the active save's regular season in place.

@app.get("/api/schedule/setup")
def api_schedule_setup():
    """Editor state: the save's week skeleton, per-conference rules with
    observed counts, protected rivals, the apply gate, and a feasibility
    report for the current rules."""
    return jsonify(schedrules.get_state())


@app.put("/api/schedule/setup")
def api_schedule_setup_save():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(schedrules.set_rules(body))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/schedule/setup/reset")
def api_schedule_setup_reset():
    return jsonify(schedrules.reset())


@app.post("/api/schedule/generate")
def api_schedule_generate():
    """Build a full-season plan from the saved rules (or report exactly why
    none exists). `shuffle` re-rolls the randomized parts."""
    body = request.get_json(silent=True) or {}
    return jsonify(schedrules.generate(shuffle=bool(body.get("shuffle"))))


@app.post("/api/schedule/apply")
def api_schedule_apply():
    """Write the generated plan into the active dynasty's save (preseason
    only, original backed up once). Press while the dynasty is closed in
    CFB 27."""
    try:
        return jsonify(schedrules.apply_plan())
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 400


# --- MMC Modding Tools (in-game mods via the community's Frosty fork) ------
# Dynasty+ exports
# .fbmod files and the MMC Mod Manager owns applying them and launching the
# game; the legacy self-built ModData + Steam launch-option pipeline is gone
# from the UI (backend.steam / modbuild remain for diagnostics).

@app.get("/api/modtools/status")
def api_modtools_status():
    """Detection: tools folder, anti-cheat swap state, installed mods."""
    return jsonify(modtools.status())


@app.post("/api/modtools/path")
def api_modtools_path():
    """Point the app at the extracted MMC Modding Tools folder ("" clears)."""
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(modtools.set_path(body.get("path") or ""))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/modtools/open")
def api_modtools_open():
    """Launch the MMC Mod Manager for the user (apply + play happen there)."""
    try:
        return jsonify(modtools.open_manager())
    except (ValueError, OSError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/conferences/mod/export")
def api_conference_mod_export():
    """Export the custom conference logos as a .fbmod and, when the MMC tools
    are installed, drop it straight into the Mod Manager's mod library."""
    try:
        result = confsetup.export_logo_fbmod()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    try:
        result["installed_to"] = str(modtools.install_fbmod(result["file"]))
    except (ValueError, OSError):
        result["installed_to"] = None  # tools absent; the file is still exported
    result["modtools"] = modtools.status()
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
        "status": pipeline.status(),
        "save_hash": pipeline.save_hash(),
        "save_present": pipeline.save_present(),
        # The save's own current season/week, so the UI can auto-advance when
        # CFB 27 moves the week forward (without a manual rescan).
        "save": pipeline.save_pointer(),
        "save_automation": recruiting_fix.automation_status(),
    })


# --- dynasty library + scan -------------------------------------------------
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
    """Read CFB 27 saves and register or update their dynasties."""
    res = pipeline.scan()
    if not res.get("present"):
        return jsonify({"present": False,
                        "error": "No CFB 27 dynasty save was found."}), 404
    # The recruiting writer is synchronous only when the coach explicitly
    # enabled it. With the tool off, Scan stays a normal read-only setup flow.
    recruiting_enabled = recruiting_fix.is_enabled()
    if recruiting_enabled:
        recruiting_fix.auto_apply()
    # users reach for Scan as a universal "refresh from the save" button, so
    # also kick a capture-only playoff sync (async, same as a watcher fire);
    # without this, Scan visibly does nothing for a mid-playoff bracket
    # Enabled recruiting holds this response until the weekly chain has a
    # final status. Other editor syncs stay in the background when recruiting
    # is off, so setup does not show a needless progress modal.
    playoff_live._on_saves_changed(recruiting_done=True, wait=recruiting_enabled)
    res["save_automation"] = recruiting_fix.automation_status()
    return jsonify(res)


@app.post("/api/dynasty/select")
def api_dynasty_select():
    body = request.get_json(silent=True) or {}
    entry = pipeline.select_dynasty(body.get("id", ""))
    if not entry:
        return jsonify({"error": "unknown dynasty"}), 404
    return jsonify({"dynasty": entry})


@app.delete("/api/dynasty/<path:dynasty_id>")
def api_dynasty_remove(dynasty_id: str):
    """Hide one card from the Dynasty+ library.

    The CFB 27 save and the companion's per-dynasty data stay untouched. Scan
    respects the hidden id, while an explicit Import makes it visible again.
    """
    if not dynasties.remove(dynasty_id):
        return jsonify({"error": "unknown dynasty"}), 404
    confsetup.invalidate_caches()
    return jsonify({"removed": dynasty_id,
                    "current": dynasties.current_id()})


# --- manual save import ----------------------------------------------------
# Scan only finds saves whose PROFILE-COLLEGE row is still live; these let the
# user browse every save file on disk and import one by hand (picking their
# program when the save has no profile row), so dynasties whose row rotated away
# are selectable again.
@app.get("/api/saves/browse")
def api_saves_browse():
    return jsonify({"saves": pipeline.browse_saves()})


@app.get("/api/saves/teams")
def api_saves_teams():
    teams_list = pipeline.save_team_options(request.args.get("path", ""))
    if teams_list is None:
        return jsonify({"error": "That file is not a readable CFB 27 save."}), 400
    return jsonify({"teams": teams_list})


@app.post("/api/dynasty/import")
def api_dynasty_import():
    body = request.get_json(silent=True) or {}
    entry = pipeline.import_save(body.get("save_path", ""), body.get("school") or None)
    if not entry:
        return jsonify({"error": "Could not import that save. Pick your program and try again."}), 400
    return jsonify({"dynasty": entry})


@app.get("/api/status")
def api_status():
    return jsonify(pipeline.status())


# --- recruiting competition tool -----------------------------------------
@app.get("/api/recruiting/tool")
def api_recruiting_tool():
    """The real save's offer and CPU attention audit plus correction settings."""
    return jsonify(recruiting_fix.tool_state())


@app.put("/api/recruiting/tool")
def api_recruiting_tool_config():
    body = request.get_json(silent=True) or {}
    return jsonify({"config": recruiting_fix.set_config(body)})


@app.post("/api/recruiting/apply")
def api_recruiting_apply():
    """Apply the correction now.  A successful write requires a game reload."""
    return jsonify(recruiting_fix.apply_to_current_save())


@app.post("/api/recruiting/reload-complete")
def api_recruiting_reload_complete():
    """Clear the reload gate after the user reloads the patched dynasty."""
    return jsonify({"automation": recruiting_fix.acknowledge_reload()})


@app.route("/api/<path:_unknown>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def api_not_found(_unknown: str):
    """Unknown API calls must not fall through to the single-page app."""
    return jsonify({"error": "not found"}), 404


def create_app() -> Flask:
    # While the app is open, new game saves re-sync the live bracket and push
    # custom-playoff matchups back into the save. It
    # no-ops until a dynasty is selected and a postseason is underway.
    # CFBMOD_PLAYOFF_AUTOSYNC=false disables it.
    import os
    if os.getenv("CFBMOD_PLAYOFF_AUTOSYNC", "true").strip().lower() not in ("0", "false", "no"):
        try:
            playoff_live.start_autosync()
        except Exception:  # noqa: BLE001 - never block boot on the watcher
            pass
    return app
