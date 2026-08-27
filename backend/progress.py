"""Shared sub-step progress state written by generation modules, read by pipeline.status()."""
from __future__ import annotations

_current: str | None = None


def set_sub_step(label: str | None) -> None:
    global _current
    _current = label


def get_sub_step() -> str | None:
    return _current
