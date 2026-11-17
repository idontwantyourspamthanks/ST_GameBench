#!/usr/bin/env python3
"""Render a captured buffer (cap_sb.py directory) to a 3x PNG: view_sb.py DIR PASS OUT.png [buf 0|1]  (palette A + sky gradient of the drvsp frame; rows >= 65 from the capture are drawn with the road palette guess = unchanged colours of drvsp)"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbart import *
d = Path(sys.argv[1]); P = int(sys.argv[2]); out = sys.argv[3]
meta = json.load(open(d / 'meta.json'))
i = next(k for k, m in enumerate(meta) if m['pass_'] == P)
buf = ('70000' if meta[i]['back'] == 0x70000 else '78000') if len(sys.argv) < 5 else ('70000' if sys.argv[4] == '0' else '78000')
I = planar_to_idx((d / f'p{i:03d}_{buf}.bin').read_bytes())
fr = Frame('drvsp')
base = fr.base
img = np.zeros((200, 320, 3), np.uint8)
for y in range(200):
    p = base if y < 74 else fr.road
    lut = np.array([p[v] if v < 15 else fr.sky[y] for v in range(16)], np.uint8)
    img[y] = lut[I[y]]
Image.fromarray(img).resize((960, 600), Image.NEAREST).save(out)
