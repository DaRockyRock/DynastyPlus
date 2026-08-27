#!/usr/bin/env python3
"""Entry point for Dynasty+ Tools.

Boots the Flask server, opens the local web UI in the default browser, and
starts the save-file watcher when a save path is configured.

    python run.py

Configuration is read from .env (see .env.example).
"""
from __future__ import annotations

from backend import config
from backend.app import create_app


def main() -> None:
    app = create_app()
    url = f"http://{config.HOST}:{config.PORT}/"

    print("=" * 60)
    print(" Dynasty+ Tools")
    print("=" * 60)
    print(f" Open in your browser : {url}")
    print(" Opens to your dynasty library. Scan the configured dynasty save")
    print(" to import it, or use run_sim.py to create a local sample save.")
    print("=" * 60)

    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
