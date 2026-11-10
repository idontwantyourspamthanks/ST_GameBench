#!/usr/bin/env python3
"""Checks the click points of patches/qol_keys.s (table KT) against the game's own hit test: every grid point must resolve to the icon id named in
its comment (pmtt_grid.icon = the loops of $13506 + table $19bde), every rotate / zoom point must lie in its rectangle of $13250, every map
point in the top-bar icon x >> 4.   python3 tools/qol_points.py"""
import re
import struct
import sys
from pathlib import Path

import pmtt_grid as g

src = (Path(__file__).resolve().parent.parent / "patches" / "qol_keys.s").read_text()
d = g.d
rects = [[struct.unpack(">h", d[0x13250 + 8 * r + 2 * i:0x13252 + 8 * r + 2 * i])[0] for i in range(4)] for r in range(4)]
bad = 0
n = 0
for m in re.finditer(r"^[ \t]+key[ \t]+\$([0-9a-f]+),(\d),(\d+),(\d+)[ \t]*;?[ \t]*(.*)$", src, re.M):
    sc, fl, x, y, c = int(m.group(1), 16), int(m.group(2)), int(m.group(3)), int(m.group(4)), m.group(5)
    n += 1
    if y < 6:
        got = f"map icon {24 + (x >> 4)}"
        ok = 0 <= x < 64
    elif x >= 64 and y >= 129:
        i = g.icon(x, y)
        got = f"icon {i}"
        ok = bool(re.search(rf"\b{i}\b", c)) or c.startswith("keypad")
    else:
        r = [k for k, (x0, y0, x1, y1) in enumerate(rects) if x0 <= x < x1 and y0 <= y < y1]
        got = f"rect {r}"
        ok = len(r) == 1
    print(f"{'ok ' if ok else 'BAD'} scan ${sc:02x} flags {fl} ({x:3d},{y:3d}) -> {got:12s} | {c}")
    bad += not ok
print(f"{n} entries, {bad} problems")
sys.exit(1 if bad else 0)
