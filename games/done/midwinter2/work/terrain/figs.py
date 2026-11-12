#!/usr/bin/env python3
"""figs.py: figures for terrain.md into work/shots/ (git-ignored): world map, subdivision levels, final window, colour ramps."""
import sys, struct
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/terrain')
from PIL import Image, ImageDraw
import replica as R
OUT = '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/shots/'
d = open('/tmp/terr/entry.bin', 'rb').read()
PAL12 = [d[0x4a6a + 2 * i:0x4a6a + 2 * i + 2].hex() for i in range(16)]
PAL = [tuple(int(c) * 36 for c in p[1:]) for p in PAL12]

def hcol(h):
    """height -> RGB: sea blues, land green->brown->white"""
    if h < 0:
        t = min(1.0, -h / 4600)
        return (int(20 + 10 * (1 - t)), int(60 + 60 * (1 - t)), int(150 + 90 * (1 - t)))
    t = min(1.0, h / 5000)
    if t < 0.4:
        a = t / 0.4; return (int(40 + 120 * a), int(130 + 40 * a), int(40 + 20 * a))
    a = (t - 0.4) / 0.6; return (int(160 + 95 * a), int(170 + 85 * a), int(60 + 195 * a))

def img_from(rows, scale, fn, col=hcol):
    H = len(rows); W = len(rows[0])
    im = Image.new('RGB', (W, H))
    im.putdata([col(v) for r in rows for v in r])
    im = im.resize((W * scale, H * scale), Image.NEAREST)
    im.save(OUT + fn)
    return im

# 1. world base map (83x53, 128 world units / sample) with the player window rectangle
base = [list(struct.unpack('>83h', d[0x49c80 + 166 * r:0x49c80 + 166 * r + 166])) for r in range(53)]
f = open('/tmp/world96.bin', 'rb').read()      # pristine file 96
base = [list(struct.unpack('>83h', f[166 * r:166 * r + 166])) for r in range(53)]
im = img_from(base, 10, 'world_base_83x53.png')
dr = ImageDraw.Draw(im)
X, Y = 1072, 2888
px, py = X / 128 * 10, Y / 128 * 10
dr.rectangle([px - 8, py - 8, px + 8, py + 8], outline=(255, 0, 0), width=2)
im.save(OUT + 'world_base_83x53_marked.png')

# 2. levels
g = R.Gen([r[:] for r in R.struct.unpack('>83h', b'') ] if False else [list(struct.unpack('>83h', d[0x49c80 + 166 * r:0x49c80 + 166 * r + 166])) for r in range(53)])
g.run(X, Y)
tiles = []
for k, lv in enumerate(g.levels):
    crop = lv
    if k >= 1:
        ox, oy = g.origins[k - 1]
    tiles.append(lv)
# show each level's 106x166 array scaled to common width 332
W = 332
panels = []
for k, lv in enumerate(g.levels):
    im = Image.new('RGB', (166, 106)); im.putdata([hcol(v) for r in lv for v in r]); im = im.resize((W, 212), Image.NEAREST)
    panels.append(im)
sheet = Image.new('RGB', (W * 3 + 20, 212 * 2 + 10), (0, 0, 0))
for k, p in enumerate(panels): sheet.paste(p, ((k % 3) * (W + 10), (k // 3) * 222))
sheet.save(OUT + 'levels_L0_L5_arrays.png')

# 3. final window (rows flipped) with lighting classes: land ramp for band 0
raw = R.window_from_L5(g.levels[5])
sh = R.load_grid('/tmp/terr/grid_shaded.bin')
def cls_col(h, a, b):
    # approximate: use shade A value and the class ramp colours at band 0
    ramp = {0: [1, 3, 7], 1: [2, 6, 14], 2: [4, 12], 4: [8, 9]}
    if h < -128:
        return PAL[4]
    c = a >> 4; s = a & 15
    r = ramp.get(c, [1])
    idx = r[min(len(r) - 1, int(s / 16 * len(r)))]
    return PAL[idx]
im = Image.new('RGB', (100, 100)); im.putdata([cls_col(sh[0][y][x], sh[1][y][x], sh[2][y][x]) for y in range(100) for x in range(100)])
im = im.resize((600, 600), Image.NEAREST); im.save(OUT + 'window_100x100_lit.png')
img_from(sh[0], 6, 'window_100x100_height.png')
print('ok')
