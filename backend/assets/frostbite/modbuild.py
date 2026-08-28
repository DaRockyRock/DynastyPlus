"""Write a Frostbite asset mod: replace conference logo textures in a ModData
mirror the game loads via `-dataPath ModData`.

The read path (extract.py) is inverted here. For each conference whose logo the
user changed:
  1. encode the new image to BC7 at the original texture's exact dimensions,
     format and mip chain (bc7enc) -> a decompressed chunk identical in size to
     the one the game expects, so the ITexture RES header never changes;
  2. wrap it in cas blocks and APPEND it to a copy of the target cas file (never
     disturbing existing chunk offsets);
  3. repoint that chunk's entry in the superbundle .toc chunk table to the new
     (offset, compressed size).

Only the touched .toc and .cas files are written as real files; everything else
in the ModData tree is hardlinked from the install, so the mirror costs a few
megabytes and builds in seconds. The game, launched with `-dataPath ModData`,
reads the patched chunk and renders the custom mark. Chunks are stored as
uncompressed cas blocks (type 0x00), which the block reader handles generically
and which needs no proprietary compressor.
"""
from __future__ import annotations

import os
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path

from . import superbundle, texture, toc
from .bundle import parse_bundle
from .cas import CasReader
from .extract import IMAGE_SB, ImageLibrary
from .gamefs import DEFAULT_GAME_ROOT, CasRef, GameFS
from .reader import Reader

# max decompressed bytes per cas block (24-bit field); keep a safe round size
_BLOCK = 0x40000  # 256 KiB
_BLOCK_TYPE_NONE = 0x00


def _cas_blocks(data: bytes) -> bytes:
    """Wrap raw bytes as uncompressed cas blocks (8-byte BE header each:
    flags(8)|decompSize(24)|type(8)|0x7(4)|compSize(20))."""
    out = bytearray()
    for i in range(0, len(data), _BLOCK):
        chunk = data[i:i + _BLOCK]
        n = len(chunk)
        header = (n << 32) | (_BLOCK_TYPE_NONE << 24) | (0x7 << 20) | n
        out += header.to_bytes(8, "big")
        out += chunk
    return bytes(out)


@dataclass
class LogoEdit:
    asset: str        # image-library bundle name, e.g. "teamconferences/assets/tcon_sec"
    image_path: Path  # the user's uploaded logo on disk


@dataclass
class _ChunkPatch:
    guid: str
    asset: str           # image-library bundle the chunk belongs to
    cas: CasRef          # original location (for install_chunk + cas_index)
    new_offset: int
    new_size: int


class ConferenceLogoMod:
    """Builds a ModData tree that re-skins conference logo textures."""

    def __init__(self, game_root: Path | str = DEFAULT_GAME_ROOT):
        self.fs = GameFS(game_root)
        self.cas = CasReader(self.fs)
        self.lib = ImageLibrary(game_root)

    # -- resolve one asset's texture spec + chunk location ------------------
    def _resolve(self, asset: str) -> tuple[texture.TextureInfo, CasRef]:
        info, _res, b = self.lib.texture_res(asset)
        chunk = next((c for c in b.chunks if c.guid == info.chunk_guid), None)
        ref = chunk.cas if chunk else self.lib.sb.chunks.get(info.chunk_guid)
        if ref is None:
            raise KeyError(f"no chunk located for {asset}")
        return info, ref

    def encode(self, edit: LogoEdit) -> tuple[texture.TextureInfo, CasRef, bytes]:
        """Encode one logo to a replacement chunk payload (uncompressed)."""
        from PIL import Image
        from . import bc7enc

        info, ref = self._resolve(edit.asset)
        img = Image.open(edit.image_path)
        payload = bc7enc.encode_texture(img, info)  # exactly info.chunk_size bytes
        return info, ref, payload

    # -- superbundle toc chunk-table patching -------------------------------
    def _toc_word_offsets(self, guid: str) -> tuple[Path, int, int]:
        """Return (toc path, byte offset of the chunk's offset word, byte offset
        of its size word) inside the superbundle .toc file on disk."""
        toc_path = self.fs.toc_path(IMAGE_SB)
        raw = toc_path.read_bytes()
        payload_start = toc.HEADER_LEN if raw[:3] == toc.MAGIC_PREFIX else 0
        payload = raw[payload_start:]
        r = _Reader(payload)
        r.skip(4)
        r.u32()                       # bundleDataOffset
        r.i32()                       # bundlesCount
        r.skip(4)
        chunk_guid_offset = r.u32()
        chunks_count = r.i32()
        r.skip(8)
        r.u32()                       # namesOffset
        chunk_data_offset = r.u32()
        r.i32(); r.i32()              # dataCount, flags
        # walk the chunk guid table to find this guid's data-word index
        from .reader import guid_from_dotnet_bytes
        r.seek(chunk_guid_offset)
        for _ in range(chunks_count):
            g = guid_from_dotnet_bytes(r.read(16)[::-1])
            index = r.i32()
            if index == -1:
                continue
            id_flag = (index >> 24) & 0xFF
            widx = index & 0x00FFFFFF
            widx += 2 if id_flag == 0x80 else 1
            if g == guid:
                off_word = payload_start + chunk_data_offset + widx * 4
                return toc_path, off_word, off_word + 4
        raise KeyError(f"chunk {guid} not in {IMAGE_SB} toc")

    def _bundle_word_offsets(self, asset: str, guid: str) -> tuple[int, int]:
        """Byte offsets (in the .toc file) of a chunk's (offset, size) words in
        its BUNDLE's file-info stream, the pointer the game actually reads.

        The bundle region is inline in the toc payload. The file-info stream at
        region+dataOffset lists, in order, an optional meta entry then every
        ebx/res/chunk, each as [cas-id (0/4/8 bytes per its flag)] + u32 offset
        + u32 size. We walk to the target chunk and return its word offsets."""
        ref = self.lib.by_name[asset]
        payload = self.lib._payload
        r = Reader(payload, ref.offset)
        bundle_offset = r.i32()
        bundle_size = r.i32()
        location_offset = r.u32()
        total_count = r.i32()
        data_offset = r.u32()
        inline_meta = not (bundle_offset == 0 and bundle_size == 0)
        flags = Reader(payload, ref.offset + location_offset).read(total_count)
        b = self.lib.bundle(asset)
        chunk_pos = next(i for i, c in enumerate(b.chunks) if c.guid == guid)
        target = (0 if inline_meta else 1) + len(b.ebx) + len(b.res) + chunk_pos
        pos = ref.offset + data_offset
        for i in range(total_count):
            flag = flags[i]
            pos += 8 if (flag & 0x80) else (4 if (flag & 0x01) else 0)  # cas-id width
            if i == target:
                return toc.HEADER_LEN + pos, toc.HEADER_LEN + pos + 4
            pos += 8  # offset + size
        raise KeyError(f"chunk {guid} not found in bundle {asset}")

    # -- build ---------------------------------------------------------------
    def build(self, edits: list[LogoEdit], out_dir: Path | str) -> dict:
        """Write the ModData mirror. Returns a report dict."""
        out = Path(out_dir)
        data_out = out / "Data"
        # group edits by the cas file they append to
        by_cas: dict[tuple[int, int], list[tuple[LogoEdit, texture.TextureInfo, CasRef, bytes]]] = {}
        for edit in edits:
            info, ref, payload = self.encode(edit)
            by_cas.setdefault((ref.install_chunk, ref.cas_index), []).append((edit, info, ref, payload))

        self._mirror(data_out)  # hardlink the whole Data tree first

        patches: list[_ChunkPatch] = []
        touched_cas: list[str] = []
        for (install_chunk, cas_index), group in by_cas.items():
            src_cas = self.fs.cas_path(group[0][2])
            rel = src_cas.relative_to(self.fs.data)
            dst_cas = data_out / rel
            self._unlink_copy(src_cas, dst_cas)          # real, writable copy
            with dst_cas.open("ab") as fh:
                for edit, info, ref, payload in group:
                    blocks = _cas_blocks(payload)
                    new_offset = fh.tell()
                    fh.write(blocks)
                    patches.append(_ChunkPatch(info.chunk_guid, edit.asset, ref, new_offset, len(blocks)))
            touched_cas.append(str(rel).replace(os.sep, "/"))

        # patch the toc: repoint each chunk to its appended copy. The chunk is
        # referenced twice, and the game reads the BUNDLE-level pointer first,
        # so we MUST patch the bundle file-info words; the superbundle chunk map
        # is patched too as a belt-and-braces fallback.
        toc_src = self.fs.toc_path(IMAGE_SB)
        toc_rel = toc_src.relative_to(self.fs.data)
        toc_dst = data_out / toc_rel
        self._unlink_copy(toc_src, toc_dst)
        buf = bytearray(toc_dst.read_bytes())
        for p in patches:
            b_off, b_size = self._bundle_word_offsets(p.asset, p.guid)
            struct.pack_into(">I", buf, b_off, p.new_offset)
            struct.pack_into(">I", buf, b_size, p.new_size)
            try:
                _toc, off_word, size_word = self._toc_word_offsets(p.guid)
                struct.pack_into(">I", buf, off_word, p.new_offset)
                struct.pack_into(">I", buf, size_word, p.new_size)
            except KeyError:
                pass  # not every chunk is in the superbundle map
        toc_dst.write_bytes(buf)

        return {
            "mod_dir": str(out),
            "data_path_arg": f"-dataPath {out.name}",
            "logos": [e.asset for e in edits],
            "touched": [str(toc_rel).replace(os.sep, "/"), *touched_cas],
        }

    # -- ModData mirror helpers ---------------------------------------------
    def _mirror(self, data_out: Path) -> None:
        """Hardlink-mirror the install's Data tree into data_out (idempotent).
        Skips the (slow) full walk once a mirror is complete, so only the first
        build pays for it; delete the marker to force a fresh mirror after a
        game patch."""
        marker = data_out / ".dynplus_mirror_complete"
        if marker.exists():
            return
        src = self.fs.data
        for root, _dirs, files in os.walk(src):
            rel = Path(root).relative_to(src)
            (data_out / rel).mkdir(parents=True, exist_ok=True)
            for name in files:
                s = Path(root) / name
                d = data_out / rel / name
                if d.exists():
                    continue
                try:
                    os.link(s, d)
                except OSError:
                    shutil.copy2(s, d)  # cross-volume fallback
        marker.write_text("ok")

    @staticmethod
    def _unlink_copy(src: Path, dst: Path) -> None:
        """Replace a (possibly hardlinked) mirror file with a private writable
        copy, so appends/patches never touch the original install."""
        if dst.exists():
            dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


class _Reader:
    """Minimal big-endian reader for the toc word walk."""
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def seek(self, pos: int) -> None:
        self.pos = pos

    def skip(self, n: int) -> None:
        self.pos += n

    def read(self, n: int) -> bytes:
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def u32(self) -> int:
        return struct.unpack_from(">I", self.data, self._adv(4))[0]

    def i32(self) -> int:
        return struct.unpack_from(">i", self.data, self._adv(4))[0]

    def _adv(self, n: int) -> int:
        p = self.pos
        self.pos += n
        return p
