"""Game filesystem view: layout.toc -> superbundles, install chunks, cas paths.

CFB 27 ships everything unpatched under <install>/Data; install chunks are keyed
by a 32-bit persistentIndex (hash-like, so cas references use the two-uint
identifier encoding from Manifest2019).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import dbobject, toc

DEFAULT_GAME_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\College Football 27")


@dataclass
class InstallChunk:
    persistent_index: int
    name: str
    install_bundle: str  # e.g. "Win32/superbundlelayout/football_installpackage_00"
    superbundles: list = field(default_factory=list)


@dataclass(frozen=True)
class CasRef:
    """A slice of a cas file: which archive, and where in it."""
    is_patch: bool
    install_chunk: int  # persistentIndex
    cas_index: int
    offset: int
    size: int


class GameFS:
    def __init__(self, game_root: Path | str = DEFAULT_GAME_ROOT):
        self.root = Path(game_root)
        self.data = self.root / "Data"
        layout = dbobject.parse(toc.read_payload(self.data / "layout.toc"))
        self.superbundles = [sb["name"] for sb in layout.get("superBundles", [])]
        self.install_chunks: dict[int, InstallChunk] = {}
        manifest = layout.get("installManifest") or {}
        for ic in manifest.get("installChunks", []):
            info = InstallChunk(
                persistent_index=ic.get("persistentIndex", 0),
                name=ic.get("name", ""),
                install_bundle=ic.get("installBundle", ""),
                superbundles=list(ic.get("superbundles", [])),
            )
            self.install_chunks[info.persistent_index] = info

    def toc_path(self, superbundle: str) -> Path:
        return self.data / f"{superbundle}.toc"

    def cas_path(self, ref: CasRef) -> Path:
        ic = self.install_chunks[ref.install_chunk]
        return self.data / ic.install_bundle / f"cas_{ref.cas_index:02d}.cas"
