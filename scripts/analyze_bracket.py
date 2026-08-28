"""Compute exact logo placements on the bracket art.

Both sides put the seed number on the LEFT of each box with the team area empty
to the right. For each seed we find the box's gold bounding box inside a tight
window, then place the logo in the center of the empty area (right of the
number) at the box's vertical center. Outputs SEED_POS percentages.
"""
import numpy as np
from PIL import Image

img = Image.open("frontend/public/cfb_bracket.png").convert("RGB")
W, H = img.size
a = np.asarray(img).astype(int)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
gold = (R > 120) & (G > 95) & (B < 175) & ((R - B) > 30)

# tight windows (x0,y0,x1,y1) around each seed box, from the mask layout
WIN = {
    8: (20, 45, 210, 132), 9: (20, 134, 210, 212),
    1: (228, 165, 450, 240), 4: (240, 352, 450, 430),
    5: (20, 450, 210, 520), 12: (20, 522, 210, 600),
    7: (978, 50, 1190, 132), 10: (978, 134, 1190, 212),
    2: (760, 165, 1000, 240), 3: (760, 352, 1000, 430),
    6: (995, 450, 1190, 520), 11: (995, 522, 1190, 600),
}

pos = {}
for seed, (wx0, wy0, wx1, wy1) in WIN.items():
    sub = gold[wy0:wy1, wx0:wx1]
    ys, xs = np.where(sub)
    if len(xs) == 0:
        print(f"seed {seed}: NO GOLD in window"); continue
    bx0, bx1 = xs.min() + wx0, xs.max() + wx0
    by0, by1 = ys.min() + wy0, ys.max() + wy0
    w = bx1 - bx0
    # column gold fraction over box height -> find where the empty area starts
    box = gold[by0:by1 + 1, bx0:bx1 + 1]
    colfrac = box.mean(axis=0)
    # number sits at left; empty area is a long high-gold run. find first column
    # (scanning from left, past the number) where the next 20px stay mostly gold.
    empty_start = 0
    for c in range(len(colfrac)):
        run = colfrac[c:c + 22]
        if len(run) and run.mean() > 0.78:
            empty_start = c
            break
    ex0 = bx0 + empty_start
    cx = (ex0 + bx1) / 2
    cy = (by0 + by1) / 2
    pos[seed] = (round(cx / W * 100, 1), round(cy / H * 100, 1))
    print(f"seed {seed:2d}: box x[{bx0},{bx1}] y[{by0},{by1}] w={w} "
          f"emptyStart=+{empty_start} -> x%={pos[seed][0]} y%={pos[seed][1]}")

print("\nSEED_POS = {")
for seed in [8, 9, 1, 4, 5, 12, 7, 10, 2, 3, 6, 11]:
    if seed in pos:
        print(f"  {seed}: {{ x: {pos[seed][0]}, y: {pos[seed][1]} }},")
print("};")
