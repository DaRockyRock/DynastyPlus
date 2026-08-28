"""Offline extraction of art assets from the CFB 27 game install.

Separate from `backend/saveparse` (which reads the dynasty *save*). This package
reads the game's packed Frostbite bundles on disk to pull out team art (logos,
etc.) so Dynasty+ can present real marks without an external CDN.

This is datamining a locally-installed game the user owns: it only reads files on
disk and never touches the running game, so it does not interact with anti-cheat.
The extracted art is EA/school trademarked, so it is for personal use; do not
redistribute it in a shipped build.

Pipeline stages (see `frostbite/`):
  1. read the DICE-headed .toc/.sb catalogs (fixed 0x22C header)   (`frostbite.toc`, done)
  2a. parse layout.toc's plaintext DbObject -> superbundle list    (`frostbite.dbobject`, planned)
  2b. parse each bundle .toc's binary chunk/asset table            (planned; format being reversed)
  3. read CAS blobs + Oodle-decompress (oo2core_9 ships with game) (planned)
  4. decode Frostbite RES textures -> PNG                          (planned)
  5. identify + map logo textures to teams                         (planned)

Note: the .toc payloads are NOT encrypted (an early XOR attempt was a false
positive); the shared hex value in the header is a format GUID, not a key.
"""
from __future__ import annotations

__all__ = ["frostbite"]
