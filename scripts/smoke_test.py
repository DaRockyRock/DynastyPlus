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
    paths = [ROOT / "run.py", ROOT / "run_sim.py"]
    for source_dir in ("backend", "simulator", "scripts"):
        paths.extend((ROOT / source_dir).rglob("*.py"))
    for path in sorted(paths):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def check_api() -> None:
    with tempfile.TemporaryDirectory(prefix="dynastyplus-smoke-") as temp_dir:
        data_dir = Path(temp_dir)
        shutil.copy2(ROOT / "data" / "league_seed.json", data_dir / "league_seed.json")
        shutil.copy2(ROOT / "data" / "local_media.json", data_dir / "local_media.json")
        os.environ["CFBMOD_DATA_DIR"] = str(data_dir)

        from simulator.app import create_app as create_simulator_app

        simulator_app = create_simulator_app()
        simulator_app.config.update(TESTING=True)

        with simulator_app.test_client() as client:
            for path in ("/", "/api/config", "/api/sim/state", "/api/customization"):
                assert_ok(client.get(path), f"Simulator GET {path}")

            assert_ok(
                client.post("/api/sim/new", json={"year": 2031, "seed": 42}),
                "Simulator POST /api/sim/new",
            )

            for path in (
                "/api/sim/scoreboard?year=2031",
                "/api/budget?year=2031",
                "/api/sim/recruits?year=2031",
            ):
                assert_ok(client.get(path), f"Simulator GET {path}")

            assert_ok(
                client.post("/api/sim/simulate-game", json={"year": 2031}),
                "Simulator POST /api/sim/simulate-game",
            )
            assert_ok(
                client.post("/api/sim/advance", json={"year": 2031}),
                "Simulator POST /api/sim/advance",
            )

        from backend.app import create_app as create_tools_app

        tools_app = create_tools_app()
        tools_app.config.update(TESTING=True)

        with tools_app.test_client() as client:
            config_response = client.get("/api/config")
            assert_ok(config_response, "Dynasty+ Tools GET /api/config")
            public_config = config_response.get_json()
            forbidden_config = {
                "model", "provider", "base_url", "use_llm", "llm_enabled",
                "llm_configured", "has_api_key",
            }
            leaked_config = forbidden_config.intersection(public_config)
            if leaked_config:
                raise AssertionError(f"Experience model settings leaked through /api/config: {sorted(leaked_config)}")

            for path in (
                "/",
                "/api/schema",
                "/api/state",
                "/api/dynasties",
                "/api/customization",
            ):
                assert_ok(client.get(path), f"Dynasty+ Tools GET {path}")

            if client.get("/api/llm").status_code != 404:
                raise AssertionError("Experience model-connection API is still exposed")

            assert_ok(client.post("/api/scan"), "Dynasty+ Tools POST /api/scan")
            response = client.get("/api/dynasties")
            assert_ok(response, "Dynasty+ Tools GET /api/dynasties after scan")
            if not response.get_json().get("dynasties"):
                raise AssertionError("Dynasty+ Tools scan did not register the sample dynasty")

            assert_ok(client.get("/api/dynasty"), "Dynasty+ Tools GET /api/dynasty")


def main() -> None:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    check_python_syntax()
    check_api()
    print("Dynasty+ smoke checks passed.")


if __name__ == "__main__":
    main()
