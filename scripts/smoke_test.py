#!/usr/bin/env python3
"""Run isolated syntax and API smoke checks without touching local game data."""

from __future__ import annotations

import ast
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def assert_ok(response, label: str) -> None:
    if 200 <= response.status_code < 300:
        return
    body = response.get_data(as_text=True)[:500]
    raise AssertionError(f"{label} returned {response.status_code}: {body}")


def check_python_syntax() -> None:
    paths = [ROOT / "run.py"]
    for source_dir in ("backend", "simulator", "scripts"):
        paths.extend((ROOT / source_dir).rglob("*.py"))
    for path in sorted(paths):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def check_api() -> None:
    with tempfile.TemporaryDirectory(prefix="dynastyplus-smoke-") as temp_dir:
        data_dir = Path(temp_dir)
        shutil.copy2(ROOT / "data" / "league_seed.json", data_dir / "league_seed.json")
        os.environ["CFBMOD_DATA_DIR"] = str(data_dir)

        from simulator.app import create_app

        app = create_app()
        app.config.update(TESTING=True)

        with app.test_client() as client:
            for path in ("/", "/api/config", "/api/sim/state", "/api/customization"):
                assert_ok(client.get(path), f"GET {path}")

            assert_ok(
                client.post("/api/sim/new", json={"year": 2031, "seed": 42}),
                "POST /api/sim/new",
            )

            for path in (
                "/api/sim/scoreboard?year=2031",
                "/api/budget?year=2031",
                "/api/sim/recruits?year=2031",
            ):
                assert_ok(client.get(path), f"GET {path}")

            assert_ok(
                client.post("/api/sim/simulate-game", json={"year": 2031}),
                "POST /api/sim/simulate-game",
            )
            assert_ok(
                client.post("/api/sim/advance", json={"year": 2031}),
                "POST /api/sim/advance",
            )


def main() -> None:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    check_python_syntax()
    check_api()
    print("Dynasty+ smoke checks passed.")


if __name__ == "__main__":
    main()
