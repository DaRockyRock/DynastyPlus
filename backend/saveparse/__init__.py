"""Readers for the real EA Sports College Football 27 dynasty save.

This package is the concrete implementation behind the save-reading seam that
`backend/watcher.read_save` was always meant to grow into (see the module
docstring there and CLAUDE.md). Early development used a synthetic save writer
that emitted the dynasty schema directly as JSON; now the game writes its own binary save and
these readers turn it back into the same schema so nothing downstream changes.

Layers, outer to inner (see `container` for the fully-solved outer layer and
`cfb27` for the in-progress record mapping):

  DYNASTY-*-AUTOSAVE           file on disk (Documents/EA SPORTS College Football 27/saves)
  └─ "FBCHUNKS" container       plaintext header (version, timestamp, build id) + one zlib stream
     └─ "FrTk" object graph     big-endian, fixed-size records with inline NUL-terminated strings

Import the submodules directly (`from backend.saveparse import cfb27, container`);
they are not imported here so running `python -m backend.saveparse.cfb27` stays clean.
"""
from __future__ import annotations

__all__ = ["cfb27", "conferences", "container", "teams"]
