"""Flask API for Dynasty+ Tools.

Owns the game data and the controls to drive a season: start a season, simulate
or override a week, and edit identity / roster / recruiting / NIL. Every change
writes an exportable dynasty snapshot.
"""
from __future__ import annotations

import hashlib
import threading

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from backend import (
    budget, conferences, config, customization_game as customization,
    purge, teams,
)
from backend.sim import adapter, state as sim_state
from . import save_writer

app = Flask(__name__, static_folder=None)
_lock = threading.Lock()

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp", "svg", "avif"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
DEFAULT_YEAR = 2026

_SHELL = "index.html"


# --- frontend (Vite build) ------------------------------------------------
_BUILD_HINT = (
    "<html><body style='font-family:sans-serif;background:#0a0e14;color:#e9eef5;"
    "padding:48px'><h2>Dynasty+ Tools UI not built yet</h2><p>Run the build once:</p>"
    "<pre style='background:#141a24;padding:16px;border-radius:10px'>"
    "cd frontend\nnpm install\nnpm run build</pre>"
    "<p>Or develop with hot reload: <code>npm run dev</code>.</p></body></html>"
)


def _serve_shell():
    resp = send_from_directory(config.FRONTEND_DIST, _SHELL)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    # Drop Content-Disposition: Safari treats `inline; filename=...` as a file to
    # hand off rather than a page to render, landing the tab on about:blank.
    resp.headers.pop("Content-Disposition", None)
    return resp


@app.route("/")
def index():
    if not (config.FRONTEND_DIST / _SHELL).exists():
        return _BUILD_HINT, 200
    return _serve_shell()


@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(config.UPLOADS_DIR, filename)


@app.route("/<path:path>")
def static_files(path: str):
    target = config.FRONTEND_DIST / path
    if not target.exists():
        return _serve_shell()
    return send_from_directory(config.FRONTEND_DIST, path)


# --- helpers --------------------------------------------------------------
def _default_year() -> int:
    """The active season's year, else the development default."""
    years = []
    for p in config.SIM_DIR.glob("*.json"):
        try:
            y = int(p.stem)
        except ValueError:
            continue
        if sim_state.is_active(y):
            years.append(y)
    return max(years) if years else DEFAULT_YEAR


def _req_year(default: int | None = None) -> int:
    body = request.get_json(silent=True) or {}
    y = request.args.get("year", type=int) or body.get("year")
    return int(y) if y not in (None, "") else (default if default is not None else _default_year())


# --- meta / config --------------------------------------------------------
@app.get("/api/config")
def api_config():
    year = _default_year()
    st = sim_state.status(year)
    return jsonify({
        "app": "dynasty-tools",
        "version": config.APP_VERSION,
        "save_path": config.SAVE_PATH,
        "sim": st,
        "user_team": customization.team().get("name"),
    })


@app.get("/api/teams")
def api_teams():
    refresh = request.args.get("refresh") == "1"
    return jsonify(teams.get_all_teams(force_refresh=refresh))


@app.get("/api/conferences")
def api_conferences():
    return jsonify(conferences.all_conferences())


# --- team picker (change my program before a season) ----------------------
def _split_school_nickname(rec: dict, name: str) -> tuple[str, str]:
    """School + nickname for a team. ESPN gives both cleanly; fall back to a
    name split (everything but the last word, then the last word) offline."""
    loc, nick = rec.get("location"), rec.get("nickname")
    if loc and nick:
        return loc, nick
    parts = (name or "").split(" ")
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    return name, ""


def _build_team_identity(name: str) -> dict:
    """The full game-data team identity for an FBS program, from the real team
    metadata (logo/color/abbr/espn id) and the league seed (conference)."""
    from backend.sim import league
    rec = teams.get_team(name)
    conf = next((r.get("conference") for r in league.load_seed() if r.get("name") == name), "")
    school, nickname = _split_school_nickname(rec, name)
    return {
        "name": name,
        "school": school,
        "nickname": nickname,
        "abbreviation": rec.get("abbreviation") or (name[:3] or "FBS").upper(),
        "espn_id": rec.get("espn_id"),
        "conference": conf or "",
        "color": rec.get("color") or "555555",
        "alt_color": rec.get("alternate_color") or "ffffff",
        "logo": "",
    }


@app.get("/api/sim/fbs-teams")
def api_sim_fbs_teams():
    """The FBS universe (the league seed) enriched with logo/color/abbr, for the
    'change my team' dropdown on the season-start screen. Grouped client-side by
    conference."""
    from backend.sim import league
    out = []
    for row in league.load_seed():
        nm = row.get("name")
        rec = teams.get_team(nm)
        out.append({
            "name": nm,
            "conference": row.get("conference"),
            "division": row.get("division"),
            "espn_id": rec.get("espn_id"),
            "abbreviation": rec.get("abbreviation"),
            "color": rec.get("color"),
            "alt_color": rec.get("alternate_color"),
            "logo": rec.get("logo"),
        })
    return jsonify({"teams": out, "current": customization.team().get("name")})


@app.post("/api/sim/set-team")
def api_sim_set_team():
    """Set the user's program from the picker. Writes the full identity (name,
    school, nickname, abbreviation, ESPN id, conference, colors) into the
    game-data team section. Only allowed before a season starts: the universe is
    built from the user's team at kickoff, so changing it mid-season would
    desync. Reset the season first to switch."""
    if sim_state.is_active(_default_year()):
        return jsonify({"error": "reset the active season before changing teams"}), 409
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "missing 'name'"}), 400
    value = customization.set_section("team", _build_team_identity(name))
    return jsonify({"team": value})


# --- customization (the game-data Customize editor) -----------------------
@app.get("/api/customization")
def api_customization():
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
    _rewrite_save_if_active()
    return jsonify({"section": section, "value": value})


@app.post("/api/customization/<section>/reset")
def api_customization_reset(section: str):
    try:
        value = customization.reset_section(section)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    _rewrite_save_if_active()
    return jsonify({"section": section, "value": value})


@app.post("/api/customization/reset")
def api_customization_reset_all():
    customization.reset_all()
    _rewrite_save_if_active()
    return jsonify({"ok": True})


@app.post("/api/customization/<section>/generate-person")
def api_customization_generate_person(section: str):
    body = request.get_json(silent=True) or {}
    seed = body.get("seed") or {}
    try:
        result = customization.generate_person(section, seed)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(result)


def _rewrite_save_if_active() -> None:
    year = _default_year()
    if sim_state.is_active(year):
        try:
            save_writer.write(year)
        except Exception:
            pass


@app.post("/api/upload")
def api_upload():
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


# --- NIL / Dynasty Points budget ------------------------------------------
def _dynasty_for_budget(year: int):
    week = sim_state.status(year)["week"]
    return week, adapter.build_dynasty(year, week)


@app.get("/api/budget")
def api_budget():
    year = _default_year()
    if not sim_state.is_active(year):
        return jsonify({"error": "no active season"}), 404
    week, dynasty = _dynasty_for_budget(year)
    return jsonify(budget.snapshot(year, week, dynasty))


@app.post("/api/budget/allocate")
def api_budget_allocate():
    year = _req_year()
    if not sim_state.is_active(year):
        return jsonify({"error": "no active season"}), 404
    body = request.get_json(silent=True) or {}
    week, dynasty = _dynasty_for_budget(year)
    res = budget.set_allocation(year, week, body.get("allocations") or {}, dynasty)
    save_writer.write(year, week)
    return jsonify(res)


@app.post("/api/budget/nil-offer")
def api_budget_nil_offer():
    year = _req_year()
    if not sim_state.is_active(year):
        return jsonify({"error": "no active season"}), 404
    body = request.get_json(silent=True) or {}
    week, dynasty = _dynasty_for_budget(year)
    res = budget.set_nil_offer(year, week, body.get("entity_id", ""), body.get("kind", "recruit"),
                               int(body.get("amount", 0)), dynasty)
    if res.get("error"):
        return jsonify(res), 404
    save_writer.write(year, week)
    return jsonify(res)


@app.post("/api/budget/recruiting-action")
def api_budget_recruiting_action():
    year = _req_year()
    if not sim_state.is_active(year):
        return jsonify({"error": "no active season"}), 404
    body = request.get_json(silent=True) or {}
    week, dynasty = _dynasty_for_budget(year)
    res = budget.spend_recruiting_action(year, week, body.get("entity_id", ""),
                                         body.get("action_key", ""), dynasty)
    if res.get("error"):
        return jsonify(res), 404
    save_writer.write(year, week)
    return jsonify(res)


# --- season simulation ----------------------------------------------------
@app.get("/api/sim/state")
def api_sim_state():
    return jsonify(sim_state.status(_default_year()))


@app.post("/api/sim/new")
def api_sim_new():
    year = _req_year(default=DEFAULT_YEAR)
    body = request.get_json(silent=True) or {}
    seed = body.get("seed")
    seed = int(seed) if seed not in (None, "") else None
    try:
        status = sim_state.new_season(year, seed)
    except RuntimeError as exc:  # league seed not built
        return jsonify({"error": str(exc)}), 409
    # Fresh season: clear that year's budget so spend starts from zero.
    try:
        (config.BUDGET_DIR / f"{year}.json").unlink()
    except OSError:
        pass
    # The new dynasty receives a stable unique id for its exported snapshots.
    save_writer.write(year, 1)
    return jsonify({"status": status, "pointer": {"year": year, "week": 1}})


@app.get("/api/sim/scoreboard")
def api_sim_scoreboard():
    year = _req_year()
    week = request.args.get("week", type=int) or sim_state.status(year)["week"]
    if not sim_state.is_active(year):
        return jsonify({"error": "no active simulated season"}), 404
    return jsonify({"year": year, "week": week, "games": sim_state.scoreboard(year, week)})


@app.post("/api/sim/advance")
def api_sim_advance():
    year = _req_year()
    if not sim_state.is_active(year):
        return jsonify({"error": "no active simulated season"}), 404
    body = request.get_json(silent=True) or {}
    override = body.get("override") or None
    with _lock:
        res = sim_state.advance(year, override=override)
        if res.get("error"):
            return jsonify(res), 400
        new_week = sim_state.status(year)["week"]
        save_writer.write(year, new_week)
    res["pointer"] = {"year": year, "week": new_week}
    return jsonify(res)


@app.post("/api/sim/simulate-game")
def api_sim_simulate_game():
    """Play the current week's games without advancing the week.

    The recruiting cycle does not run until the user advances.
    """
    year = _req_year()
    if not sim_state.is_active(year):
        return jsonify({"error": "no active simulated season"}), 404
    body = request.get_json(silent=True) or {}
    override = body.get("override") or None
    with _lock:
        res = sim_state.simulate_week(year, override=override)
        if res.get("error"):
            return jsonify(res), 400
        week = sim_state.status(year)["week"]  # unchanged: still the current week
        save_writer.write(year, week)
    res["pointer"] = {"year": year, "week": week}
    return jsonify(res)


@app.post("/api/sim/reset")
def api_sim_reset():
    year = _req_year()
    sim_state.reset(year)
    save_writer.clear()
    return jsonify({"reset": True, "status": sim_state.status(year)})


@app.post("/api/sim/delete")
def api_sim_delete():
    """Delete all simulated seasons, budgets, snapshots, and customization."""
    with _lock:
        summary = purge.delete_everything()
    return jsonify({"deleted": True, "status": sim_state.status(_default_year()), **summary})


@app.get("/api/sim/recruits")
def api_sim_recruits():
    from backend.sim import recruiting as sim_recruiting
    year = _default_year()
    st = sim_state.get(year)
    user = st.get("user_team") if st else None
    universe = st.get("teams") if st else None
    return jsonify({"year": year, "user_team": user,
                    "recruits": sim_recruiting.national_list(year, universe)})


def create_app() -> Flask:
    return app
