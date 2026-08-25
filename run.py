#!/usr/bin/env python3
"""Entry point for Dynasty+ Tools.

Boots the local Flask server that powers the season simulator, customization,
NIL, and recruiting tools.

    python run.py

Configuration is read from .env (see .env.example).
"""
from __future__ import annotations

from backend import config
from simulator.app import create_app


def main() -> None:
    app = create_app()
    url = f"http://{config.HOST}:{config.PORT}/"

    print("=" * 60)
    print(" Dynasty+ Tools")
    print("=" * 60)
    print(f" Open in your browser : {url}")
    print(f" Data directory       : {config.DATA_DIR}")
    print(f" Dynasty snapshot     : {config.SAVE_PATH}")
    print("=" * 60)

    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
