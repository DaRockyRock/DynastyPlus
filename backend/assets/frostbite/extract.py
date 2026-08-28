"""High-level asset extraction API over the Frostbite readers.

Usage:
    lib = ImageLibrary()                       # opens imageassetlibrarysb
    for name in lib.names(): ...
    img = lib.image("teamlogos/teamlogos/assets/ncaa/tmlg_ncaa_primary_charlotte")
"""
from __future__ import annotations

from pathlib import Path

from . import bundle as bundle_mod
from . import superbundle, texture, toc
from .cas import CasReader
from .gamefs import DEFAULT_GAME_ROOT, GameFS

IMAGE_SB = "Win32/imageassetlibrarysb"
NAME_PREFIX = "win32/content/ui/imageassetlibraries/global/"


class ImageLibrary:
    def __init__(self, game_root: Path | str = DEFAULT_GAME_ROOT,
                 superbundle_name: str = IMAGE_SB):
        self.fs = GameFS(game_root)
        self.cas = CasReader(self.fs)
        self._payload = toc.read_payload(self.fs.toc_path(superbundle_name))
        sb = superbundle.parse(self._payload)
        self.sb = sb
        # short name (after .../global/, minus the _assetlibrary_* suffix) -> BundleRef
        self.by_name = {}
        for b in sb.bundles:
            self.by_name[self.short_name(b.name)] = b

    @staticmethod
    def short_name(bundle_name: str) -> str:
        name = bundle_name
        if name.startswith(NAME_PREFIX):
            name = name[len(NAME_PREFIX):]
        for marker in ("_assetlibrary_", "_assestlibrary_"):
            if marker in name:
                name = name.split(marker)[0]
        return name

    def names(self):
        return self.by_name.keys()

    def find(self, needle: str):
        return [n for n in self.by_name if needle in n]

    def bundle(self, name: str) -> bundle_mod.Bundle:
        ref = self.by_name[name]
        return bundle_mod.parse_bundle(self._payload, ref.offset, ref.size,
                                       read_cas=self.cas.read_raw)

    def texture_res(self, name: str):
        """Return (TextureInfo, res_entry, bundle) for the bundle's texture RES."""
        b = self.bundle(name)
        for res in b.res:
            if res.res_type == 0x6BDE20BA:  # ITexture
                return texture.parse_header(self.cas.read(res.cas)), res, b
        raise KeyError(f"no texture RES in bundle {name}")

    def image(self, name: str):
        """Decode the bundle's texture into a PIL RGBA image."""
        info, _res, b = self.texture_res(name)
        chunk = next((c for c in b.chunks if c.guid == info.chunk_guid), None)
        if chunk is None:
            # fall back to the superbundle-level chunk index
            ref = self.sb.chunks.get(info.chunk_guid)
            if ref is None:
                raise KeyError(f"chunk {info.chunk_guid} not found for {name}")
            data = self.cas.read(ref)
        else:
            data = self.cas.read(chunk.cas)
        return texture.decode(info, data)
