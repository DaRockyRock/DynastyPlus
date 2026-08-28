#!/usr/bin/env python3
"""Generate the Dynasty+ application icon.

Renders a professional, styled "D+" app mark and writes it out as the icon set
electron-builder consumes (a 1024x1024 PNG and a multi-size Windows .ico). The
mark is drawn as vectors with Pillow (no font dependency) at 4x supersampling
and downsampled, so edges stay crisp at every size.

Design: a deep charcoal-navy rounded square (the app's field color) with a soft
diagonal light beam, a bold monoline cream "D", and a gold "+" accent, matching
the CFB 27 second-screen aesthetic (charcoal panels, cream selected states, a
team-color field with light beams).

    python scripts/make_icon.py

Output: electron/build/icon.png and electron/build/icon.ico.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "electron" / "build"

SIZE = 1024          # final icon edge, px
SS = 4               # supersample factor for antialiasing
S = SIZE * SS        # working canvas edge

# Palette (matches frontend/src/styles/tokens.css field + cream + gold accent).
BG_TOP = (30, 41, 61)        # #1e293d charcoal navy, lit corner
BG_BOTTOM = (10, 14, 20)     # #0a0e14 deep field, matches app background
CREAM = (244, 236, 216)      # #f4ecd8 the "selected" cream
GOLD = (240, 178, 64)        # #f0b240 warm accent for the plus
BEAM = (255, 255, 255, 26)   # faint diagonal light streak


def _vertical_gradient(w: int, h: int, top: tuple, bottom: tuple) -> Image.Image:
    """A smooth top-to-bottom gradient between two RGB colors."""
    grad = Image.new("RGB", (1, h))
    px = grad.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return grad.resize((w, h))


def _rounded_mask(w: int, h: int, radius: int) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    return mask


# Bold, geometric/condensed faces first (closest to the game's compressed UI
# type), falling back to Arial Bold, then whatever Pillow can find.
_FONT_PATHS = [
    r"C:\Windows\Fonts\bahnschrift.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "arialbd.ttf",
    "DejaVuSans-Bold.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_PATHS:
        try:
            font = ImageFont.truetype(path, size)
        except OSError:
            continue
        # Bahnschrift is a variable font; pick its boldest condensed instance.
        for variation in ("Bold Condensed", "Bold SemiCondensed", "Bold"):
            try:
                font.set_variation_by_name(variation)
                break
            except Exception:
                pass
        return font
    return ImageFont.load_default(size)


def _glyph_mask(text: str, font: ImageFont.FreeTypeFont, cx: int, cy: int) -> Image.Image:
    """An 'L' mask with `text` rendered centered on (cx, cy)."""
    mask = Image.new("L", (S, S), 0)
    draw = ImageDraw.Draw(mask)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    x = cx - (right + left) // 2
    y = cy - (bottom + top) // 2
    draw.text((x, y), text, font=font, fill=255)
    return mask


def _mark_masks() -> tuple[Image.Image, Image.Image]:
    """Masks for the 'D' (cream) and '+' (gold) that form the D+ wordmark,
    laid out and centered together as one unit."""
    d_font = _font(int(S * 0.62))
    p_font = _font(int(S * 0.36))

    probe = ImageDraw.Draw(Image.new("L", (S, S)))
    dl, dt, dr, db = probe.textbbox((0, 0), "D", font=d_font)
    pl, pt, pr, pb = probe.textbbox((0, 0), "+", font=p_font)
    d_w, p_w = dr - dl, pr - pl
    gap = int(S * 0.03)
    total = d_w + gap + p_w

    cy = int(S * 0.50)
    d_cx = (S - total) // 2 + d_w // 2
    p_cx = (S - total) // 2 + d_w + gap + p_w // 2

    return _glyph_mask("D", d_font, d_cx, cy), _glyph_mask("+", p_font, p_cx, cy)


def build_icon() -> Image.Image:
    # Field: gradient clipped to a rounded square.
    field = _vertical_gradient(S, S, BG_TOP, BG_BOTTOM).convert("RGBA")

    # Diagonal light beam, blurred for softness.
    beam = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(beam).polygon(
        [(int(S * 0.02), int(S * 0.34)), (int(S * 0.46), int(-S * 0.06)),
         (int(S * 0.62), int(S * 0.06)), (int(S * 0.18), int(S * 0.46))],
        fill=BEAM,
    )
    beam = beam.filter(ImageFilter.GaussianBlur(S // 40))
    field = Image.alpha_composite(field, beam)

    # Soft inner vignette at the bottom for depth.
    vign = Image.new("L", (S, S), 0)
    ImageDraw.Draw(vign).ellipse([int(-S * 0.3), int(S * 0.55), int(S * 1.3), int(S * 1.5)], fill=90)
    vign = vign.filter(ImageFilter.GaussianBlur(S // 20))
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    field = Image.composite(shadow, field, vign)

    # Drop shadow behind the mark for a raised, premium feel.
    mark = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d_mask, p_mask = _mark_masks()
    shadow_mask = Image.new("L", (S, S), 0)
    shadow_mask.paste(d_mask, (0, 0), d_mask)
    shadow_mask.paste(p_mask, (0, 0), p_mask)
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh.paste((0, 0, 0, 150), (0, 0), shadow_mask)
    sh = sh.filter(ImageFilter.GaussianBlur(S // 90))
    sh = _offset(sh, 0, int(S * 0.008))
    mark = Image.alpha_composite(mark, sh)

    # The D (cream) and + (gold).
    cream_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cream_layer.paste(CREAM + (255,), (0, 0), d_mask)
    gold_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gold_layer.paste(GOLD + (255,), (0, 0), p_mask)
    mark = Image.alpha_composite(mark, cream_layer)
    mark = Image.alpha_composite(mark, gold_layer)

    field = Image.alpha_composite(field, mark)

    # Clip to a rounded square (transparent corners) and add a subtle rim light.
    corner = int(S * 0.20)
    field.putalpha(_rounded_mask(S, S, corner))
    rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle(
        [int(S * 0.006), int(S * 0.006), S - int(S * 0.006), S - int(S * 0.006)],
        radius=corner, outline=(255, 255, 255, 30), width=max(2, S // 340))
    field = Image.alpha_composite(field, rim)

    return field.resize((SIZE, SIZE), Image.LANCZOS)


def _offset(img: Image.Image, dx: int, dy: int) -> Image.Image:
    """Offset an RGBA image, leaving transparent fill (small drop-shadow nudge)."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (dx, dy))
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    icon = build_icon()

    png_path = OUT_DIR / "icon.png"
    icon.save(png_path)
    print(f"wrote {png_path} ({icon.width}x{icon.height})")

    ico_path = OUT_DIR / "icon.ico"
    icon.save(ico_path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                               (64, 64), (128, 128), (256, 256)])
    print(f"wrote {ico_path}")


if __name__ == "__main__":
    main()
