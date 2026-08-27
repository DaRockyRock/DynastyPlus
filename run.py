#!/usr/bin/env python3
"""Entry point for Dynasty+ Tools.

Boots the Flask server, opens the local web UI in the default browser, and
starts the save-file watcher when a save path is configured.

    python run.py

Configuration is read from .env (see .env.example). With no API key the app
runs entirely on mock content, which is ideal for building out the UI.
"""
from __future__ import annotations

from backend import config
from backend.app import create_app


def main() -> None:
    app = create_app()
    url = f"http://{config.HOST}:{config.PORT}/"

    summary = config.runtime_summary()
    print("=" * 60)
    print(" Dynasty+ Tools")
    print("=" * 60)
    print(f" Open in your browser : {url}")
    print(f" Model                : {summary['model']}")
    print(f" LLM enabled          : {summary['use_llm']} (API key present: {summary['has_api_key']})")
    print(" Opens to your dynasty library. Scan the configured dynasty save")
    print(" to import it, or use run_sim.py to create a local sample save.")
    print("=" * 60)
    if not summary["use_llm"]:
        print(" Running on MOCK content. Set CFBMOD_USE_LLM=true and add an")
        print(" ANTHROPIC_API_KEY in .env to enable live generation.")
        print("=" * 60)

    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
