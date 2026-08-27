"""Save-file watcher (the Dynasty+ companion).

Monitors the dynasty save the Simulator (or, later, CFB 27) writes. On any change
it asks the pipeline to reconcile against the save: a new week advances and
regenerates, a new season resets, a same-week edit refreshes the current week.
The UI polls the state/status endpoints to mirror generation progress.

`read_save` is the single seam to replace with a binary parser once the real
CFB 27 save format is known; everything downstream consumes the dynasty schema.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # pragma: no cover
    FileSystemEventHandler = object  # type: ignore
    Observer = None  # type: ignore

from . import config, pipeline, schema


def read_save(save_path: str) -> dict[str, Any] | None:
    """Load and validate the full dynasty dict from the save file.

    Returns None when the file is missing, unreadable, partially written, or does
    not conform to the dynasty schema. Replace this with the binary save parser
    once the CFB 27 format is known.
    """
    path = Path(save_path)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or schema.validate(data):
        return None
    return data


class _Handler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, save_path: str, on_change: Callable[[], None], debounce: float = 1.0):
        self.save_path = str(Path(save_path).resolve())
        self.on_change = on_change
        self.debounce = debounce
        self._last_fire = 0.0

    def on_modified(self, event):  # noqa: ANN001
        self._maybe_handle(getattr(event, "src_path", ""))

    def on_created(self, event):  # noqa: ANN001
        self._maybe_handle(getattr(event, "src_path", ""))

    def on_moved(self, event):  # noqa: ANN001
        # Atomic saves (write temp file, then rename into place) arrive as a move
        # whose destination is the watched file - the common pattern for games and
        # the Simulator's own atomic writes - so it must trigger just like a write.
        self._maybe_handle(getattr(event, "dest_path", ""))

    def _maybe_handle(self, src_path: str) -> None:
        if Path(src_path).resolve() != Path(self.save_path):
            return
        now = time.time()
        if now - self._last_fire < self.debounce:
            return
        self._last_fire = now
        self.on_change()


class SaveWatcher:
    """Background watchdog observer that reconciles the pipeline on save changes."""

    def __init__(self, save_path: str | None = None):
        self.save_path = save_path or config.SAVE_PATH
        self._observer = None
        self.last_event: dict[str, Any] = {}

    def _on_change(self) -> None:
        # Reconcile in a worker so the watcher thread stays responsive.
        def _run() -> None:
            outcome = pipeline.sync_from_save()
            if outcome:
                self.last_event = {**outcome, "at": time.time()}
        threading.Thread(target=_run, daemon=True).start()

    def start(self) -> bool:
        if not self.save_path or Observer is None:
            return False
        watch_dir = Path(self.save_path).parent
        if not watch_dir.exists():
            return False
        handler = _Handler(self.save_path, self._on_change)
        self._observer = Observer()
        self._observer.schedule(handler, str(watch_dir), recursive=False)
        self._observer.daemon = True
        self._observer.start()
        return True

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

    def info(self) -> dict[str, Any]:
        return {
            "active": self._observer is not None,
            "save_path": self.save_path or None,
            "last_event": self.last_event or None,
        }
