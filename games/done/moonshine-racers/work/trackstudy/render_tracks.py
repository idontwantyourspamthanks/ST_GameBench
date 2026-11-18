#!/usr/bin/env python3
"""Render decoded tracks with PIL (no matplotlib here): per-level 6-panel PNG + contact sheet."""
import os, numpy as np
from PIL import Image, ImageDraw
from msrtrack import *
K = 600.0     # heading = c/K radians: ARBITRARY visual scale (the game has no world-space geometry)

def path(c, length):
    n = int(length); th = c[:n] / K
    return np.cumsum(np.sin(th)), np.cumsum(np.cos(th))

def panel(d, box, title, series, equal=False, colors=None, pts=None, marks=None):
    x0, y0, w, h = box
    d.rectangle([x0, y0, x0+w, y0+h], outline=(120, 120, 120)); d.text((x0+4, y0+2), title, fill=(255, 255, 255))
    allx = np.concatenate([s[0] for s in series]); ally = np.concatenate([s[1] for s in series])
    xmin, xmax, ymin, ymax = allx.min(), allx.max(), ally.min(), ally.max()
    pad = 16
    sx = (w-2*pad)/max(xmax-xmin, 1e-9); sy = (h-2*pad-10)/max(ymax-ymin, 1e-9)
    if equal: sx = sy = min(sx, sy)
    T = lambda X, Y: (x0+pad+(X-xmin)*sx, y0+h-pad-(Y-ymin)*sy)
    for i, (X, Y) in enumerate(series):
        col = (colors or [(80, 200, 255), (255, 160, 60), (120, 255, 120)])[i % 3]
        pp = [T(a, b) for a, b in zip(X[::max(1, len(X)//1500)], Y[::max(1, len(X)//1500)])]
        d.line(pp, fill=col, width=1)
    for (X, Y, col, r) in (marks or []):
        px, py = T(X, Y); d.ellipse([px-r, py-r, px+r, py+r], outline=col)
    d.text((x0+4, y0+h-12), f'x {xmin:.0f}..{xmax:.0f}  y {ymin:.0f}..{ymax:.0f}', fill=(160, 160, 160))

def level_figure(lev, cell=None):
    t, b = parse(lev); m = minimap(lev)
    c = curve_arrays(t); L = int(m['len'])
    left = ring_arrays(t['left'], 'slew'); right = ring_arrays(t['right'], 'slew'); hill = ring_arrays(t['hill'], 'hill')
    x, y = path(c, L)
    img = Image.new('RGB', (1500, 900), (20, 20, 30)); d = ImageDraw.Draw(img)
    s = np.arange(L)
    mk = [(x[0], y[0], (0, 255, 0), 5), (x[-1], y[-1], (255, 0, 0), 5)] + [(x[k], y[k], (255, 255, 0), 2) for k in range(1000, L, 1000)]
    panel(d, (0, 0, 500, 450), f'L{lev} top-down path from curve data (theta=c/{K:.0f}; arbitrary scale), yellow = every 1000 units', [(x, y)], equal=True, marks=mk)
    P = m['pts']; panel(d, (500, 0, 500, 450), f"L{lev} the game's own minimap polyline ($57890 block, {m['n']} nibble steps)", [(P[:, 0], -P[:, 1])], equal=True)
    panel(d, (1000, 0, 500, 450), 'curve value c(s) (source of ring $1bbc)', [(s, c[:L])])
    panel(d, (0, 450, 500, 450), 'elevation byte 0..127 (source of ring $23c8)', [(s, hill[:L])])
    panel(d, (500, 450, 500, 450), 'half-width profiles left/right (rings $13b0/$17b0)', [(s, left[:L]), (s, right[:L])])
    od = np.cumsum([t['obj_first']] + [g for _, _, g in t['objs']][:-1]); ol = np.array([o[1] for o in t['objs']])  # (type,lat,gap): lat = 2nd? see msrtrack
    panel(d, (1000, 450, 500, 450), f"objects: distance vs 2nd field ({len(t['objs'])} objects)", [(od[:len(ol)], ol)])
    img.save(f'png/level{lev:02d}.png')
    if cell is not None:
        cimg = Image.new('RGB', (300, 300), (20, 20, 30)); dd = ImageDraw.Draw(cimg)
        panel(dd, (0, 0, 300, 300), f'L{lev} len {L}', [(x, y)], equal=True)
        return cimg

if __name__ == '__main__':
    os.makedirs('png', exist_ok=True)
    sheet = Image.new('RGB', (1500, 900))
    for lev in range(NLEV):
        ci = level_figure(lev, cell=True); sheet.paste(ci, ((lev % 5)*300, (lev//5)*300))
    sheet.save('png/contact_sheet.png')
