#!/usr/bin/env python3
"""Viewer gate: the editor's top-down map (a Hatari screenshot of the viewer at zoom 1) against the PNG `tools/msrtrack.py render` draws for the same track.
   python3 work/edgate/cmpmap.py SHOT.png SRC [--entry K] [-o OUT.png]        SRC = level number 0..14 | FILE.trk (with --entry)
Method: (1) `msrtrack.py render` writes its PNG; the road path of its panel A (760x760) is taken by colour (the elevation gradient and the grey tail, nothing else in the panel has them);
(2) the road pixels of the editor's map window (ST rows 8..111) are taken from the screenshot (road, dim tail, the white of the highlighted segment; the yellow highlight / cursor,
the start and BAR boxes and the 1000-unit dots are left out; for the reverse direction every lit pixel of the window counts, since the boxes and the cursor cover a few road pixels); (3) both point sets are brought to the same frame by their bounding boxes (both programs fit the path into a window, so
the bounding boxes correspond) and compared both ways: for every editor pixel the distance to the nearest PNG path pixel and the reverse, in ST pixels.  The two bounding-box aspect
ratios are compared as well (a wrong heading scale or a mirrored axis changes them).  OUT.png = the PNG panel and the screenshot side by side."""
import argparse, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

G = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(); ap.add_argument("shot"); ap.add_argument("src"); ap.add_argument("--entry", type=int); ap.add_argument("-o", "--out")
a = ap.parse_args()
png = Path("/tmp/msred") / (Path(a.shot).stem + "_render.png"); png.parent.mkdir(exist_ok=True)
cmd = [sys.executable, str(G / "tools" / "msrtrack.py"), "render", a.src, "-o", str(png)] + (["--entry", str(a.entry)] if a.entry is not None else [])
subprocess.run(cmd, check=True, capture_output=True)

# ---- the PNG's path (panel A)
P = np.asarray(Image.open(png).convert("RGB")).astype(int)[:760, :760]
R, Gc, B = P[..., 0], P[..., 1], P[..., 2]
hv = (R - 60) / 1.6                                                     # the render's colour: (60 + 1.6 h, 120 + 60 (1 - h / 127), 255 - 1.8 h), h = height 0..127
grad = (hv >= -1) & (hv <= 128) & (np.abs(B - (255 - 1.8 * hv)) <= 3) & (np.abs(Gc - (120 + 60 * (1 - hv / 127))) <= 3)
tail = (R == 70) & (Gc == 70) & (B == 85)
py, px = np.nonzero(grad | tail)
# ---- the editor's map: the screenshot holds the 320x200 screen doubled at (96, 58)
S = np.asarray(Image.open(a.shot).convert("RGB")).astype(int)
if S.shape[1] != 832: raise SystemExit(f"unexpected screenshot size {S.shape}")
scr = S[58:458:2, 96:736:2]
win = scr[8:112]
road = win[..., 2] > 100                                                # road $567, tail $444, highlighted road $777: blue present; yellow / green / red / orange have none
box = (win[..., 2] < 60) & ((win[..., 0] < 60) ^ (win[..., 1] < 60))    # the start (green) and BAR (red) boxes: where the yellow cursor cross runs over a box outline the pixel is white too,
near = np.zeros_like(box)                                               # two pixels off the road: white pixels touching a box pixel are not counted as road
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1):
        near |= np.roll(np.roll(box, dy, 0), dx, 1)
sy, sx = np.nonzero(road & ~near)
if len(px) < 50 or len(sx) < 50: raise SystemExit(f"too few path pixels: png {len(px)}, editor {len(sx)}")
pw, ph = px.max() - px.min(), py.max() - py.min()
sw, sh = sx.max() - sx.min(), sy.max() - sy.min()
# PNG points in the editor's frame: bounding boxes aligned (the PNG line is 2 px wide: half a pixel of bias at most)
qx = sx.min() + (px - px.min()) * (sw / max(pw, 1)); qy = sy.min() + (py - py.min()) * (sh / max(ph, 1))


def nearest(ax, ay, bx, by):
    out = np.empty(len(ax))
    for i in range(0, len(ax), 2000):
        d = (ax[i:i + 2000, None] - bx[None, :]) ** 2 + (ay[i:i + 2000, None] - by[None, :]) ** 2
        out[i:i + 2000] = np.sqrt(d.min(axis=1))
    return out


d1 = nearest(sx.astype(float), sy.astype(float), qx, qy)                # editor pixel -> PNG path
ay, ax = np.nonzero(win.sum(axis=2) > 60)                               # coverage: every lit pixel of the map window (the boxes and the cursor cover a few road pixels)
d2 = nearest(qx, qy, ax.astype(float), ay.astype(float))               # PNG path -> editor pixel
asp_p, asp_s = pw / max(ph, 1), sw / max(sh, 1)
big = max(sw, sh)
ok = d1.max() <= 3.0 and d2.max() <= 3.0 and np.percentile(d1, 99) <= 2.0 and np.percentile(d2, 99) <= 2.0 and abs(asp_p / asp_s - 1) <= 3.0 / big + 0.02
print(f"{Path(a.shot).name} vs render {a.src}{'' if a.entry is None else ' entry ' + str(a.entry)}: editor path pixels {len(sx)} bbox {sw + 1}x{sh + 1} px, PNG path pixels {len(px)} bbox {pw + 1}x{ph + 1} px, "
      f"aspect PNG {asp_p:.3f} editor {asp_s:.3f}; editor->PNG mean {d1.mean():.2f} p99 {np.percentile(d1, 99):.2f} max {d1.max():.2f} px; PNG->editor mean {d2.mean():.2f} p99 {np.percentile(d2, 99):.2f} max {d2.max():.2f} px: "
      f"{'MATCH' if ok else 'MISMATCH'}")
if a.out:
    A = Image.open(png).convert("RGB").crop((0, 0, 760, 760)).resize((400, 400))
    Bm = Image.fromarray(S[58:458, 96:736].astype("uint8"))
    out = Image.new("RGB", (400 + 640 + 12, 400), (0, 0, 0)); out.paste(A, (0, 0)); out.paste(Bm, (412, 0)); out.save(a.out)
sys.exit(0 if ok else 1)
