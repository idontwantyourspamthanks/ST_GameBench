"""Count the screenshots that show the mouse pointer (test scaffolding).  The pointer sprite (shape 1, 16x16, opaque pixels by colour index) is searched in the
320x200 logical picture sampled from the screenshot; the colour index -> RGB map is learned from the screenshots of the fixed build (pointer position known from $24786/8 for the still series)."""
import json, sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ttp

def logical(path, ox, oy):
    im = np.asarray(Image.open(path).convert("RGB"))
    return im[oy:oy + 400:2, ox:ox + 640:2][:200, :320]

def learn(files, x, y, px, offs):
    best = None
    for ox, oy in offs:
        votes = {}
        for f in files:
            L = logical(f, ox, oy)
            for dx, dy, c in px:
                votes.setdefault(c, Counter())[tuple(L[y + dy, x + dx])] += 1
        score = sum(v.most_common(1)[0][1] for v in votes.values())
        if best is None or score > best[0]:
            best = (score, (ox, oy), {c: v.most_common(1)[0][0] for c, v in votes.items()})
    return best

def count(files, px, cmap, off, thr=0.95):
    ox, oy = off
    res = []
    for f in files:
        L = logical(f, ox, oy)
        ok = np.zeros((180, 300), dtype=np.int32)
        for dx, dy, c in px:
            col = np.array(cmap[c])
            ok += (L[dy:dy + 180, dx:dx + 300] == col).all(axis=2)
        mx = int(ok.max())
        res.append((mx / len(px), tuple(int(v) for v in np.unravel_index(ok.argmax(), ok.shape))))
    return [(round(s, 2), p) for s, p in res], sum(s >= thr for s, _ in res)
