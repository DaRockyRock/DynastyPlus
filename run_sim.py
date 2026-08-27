#!/usr/bin/env python3
"""Entry point for the Simulator (a CFB 27 stand-in).

Boots the Simulator Flask server on its own port, opens its UI in the browser,
and watches the companion inbox so coach actions queued in Dynasty+ are drained
and folded into the save between weeks (advancing a week drains them inline too).

    python run_sim.py

Runs alongside Dynasty+ (run.py). They communicate only through files under
data/save/: the Simulator writes dynasty.json; Dynasty+ writes companion_inbox.json.
"""
from __future__ import annotations

import time
from pathlib import Path

from backend import config, inbox
from backend.sim import state as sim_state
from simulator import save_writer
from simulator.app import apply_inbox, create_app, _default_year

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # pragma: no cover
    FileSystemEventHandler = object  # type: ignore
    Observer = None  # type: ignore


class _InboxHandler(FileSystemEventHandler):  # type: ignore[misc]
    """Drain the inbox shortly after it changes, so an NIL offer made in the
    companion shows its effect without waiting for the next advance."""

    def __init__(self, inbox_path: str, debounce: float = 0.8):
        self._path = str(Path(inbox_path).resolve())
        self._debounce = debounce
        self._last = 0.0

    def _maybe(self, src: str) -> None:
        if not src or Path(src).resolve() != Path(self._path):
            return
        now = time.time()
        if now - self._last < self._debounce:
            return
        self._last = now
        for action in inbox.pending():
            year = action.get("year")
            if year is not None:
                apply_inbox(int(year))

    def on_modified(self, event):  # noqa: ANN001
        self._maybe(getattr(event, "src_path", ""))

    def on_created(self, event):  # noqa: ANN001
        self._maybe(getattr(event, "src_path", ""))

    def on_moved(self, event):  # noqa: ANN001
        self._maybe(getattr(event, "dest_path", ""))


def _start_inbox_watcher() -> bool:
    if Observer is None:
        return False
    inbox_dir = Path(config.INBOX_PATH).parent
    inbox_dir.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(_InboxHandler(config.INBOX_PATH), str(inbox_dir), recursive=False)
    observer.daemon = True
    observer.start()
    return True


def main() -> None:
    app = create_app()
    url = f"http://{config.HOST}:{config.SIM_PORT}/"
    watching = _start_inbox_watcher()

    # If a season is already active, ensure the save on disk reflects it so the
    # companion shows the current week immediately on launch (rather than waiting
    # for the next advance/edit).
    year = _default_year()
    if sim_state.is_active(year):
        try:
            save_writer.write(year)
        except Exception:
            pass

    print("=" * 60)
    print(" Simulator - College Football 27 stand-in")
    print("=" * 60)
    print(f" URL          : {url}")
    print(f" Save file    : {config.SAVE_PATH}")
    print(f" Inbox        : {config.INBOX_PATH} (watching: {watching})")
    print(" Open in your browser, drive the season; Scan it into Dynasty+ (run.py).")
    print("=" * 60)

    app.run(host=config.HOST, port=config.SIM_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
