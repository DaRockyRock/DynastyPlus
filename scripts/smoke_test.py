#!/usr/bin/env python3
"""Small CI smoke test for the packaged Tools surface."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_temp = tempfile.TemporaryDirectory(prefix="dynastyplus-tools-smoke-")
os.environ["CFBMOD_DATA_DIR"] = _temp.name
os.environ["CFBMOD_SAVE_PATH"] = str(Path(_temp.name) / "missing-saves")
os.environ["CFBMOD_PLAYOFF_AUTOSYNC"] = "false"

from backend.app import app  # noqa: E402


def main() -> None:
    client = app.test_client()

    config = client.get("/api/config")
    assert config.status_code == 200, config.get_data(as_text=True)
    payload = config.get_json()
    assert payload["app_name"] == "Dynasty+ Tools"
    assert payload["save_present"] is False
    assert "provider" not in payload

    for path in (
        "/api/setup/status",
        "/api/setup/detect",
        "/api/dynasties",
        "/api/playoff/format",
        "/api/status",
        "/",
    ):
        response = client.get(path)
        assert response.status_code == 200, (path, response.get_data(as_text=True))

    required = {
        "/api/conferences/setup",
        "/api/schedule/setup",
        "/api/playoff/format",
        "/api/playoff/live",
        "/api/bowls",
        "/api/polls",
        "/api/rankings/scoreboard",
        "/api/recruiting/tool",
    }
    routes = {rule.rule for rule in app.url_map.iter_rules()}
    assert required <= routes

    # Removed API surfaces return JSON 404s instead of the app shell.
    removed = client.get("/api/not-a-real-route")
    assert removed.status_code == 404
    assert removed.is_json

    print("Dynasty+ Tools smoke test passed")


if __name__ == "__main__":
    main()
