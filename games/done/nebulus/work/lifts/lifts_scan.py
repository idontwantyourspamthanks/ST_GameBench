#!/usr/bin/env python3
"""Scan the shipped towers for lifts: bottom $85, top $08, optional station $0c, same column.
usage: lifts_scan.py [NEBEXE.FIC]  (needs work/level/tools/nebedit.py)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'level' / 'tools'))
import nebedit
path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[2] / 'originals/NEBULGX/NEBEXE.FIC')
nb = nebedit.Nebulus(path)
for m in (1, 2):
    for t in range(8):
        g, _, _ = nb.grid(m, t)
        H = len(g[0])
        print(f"== mission {m} tower {t+1} rows {H}")
        used = set()
        for a in range(16):
            col = g[a]
            for r in range(H):
                if col[r] == 0x85:
                    # next row above with &c in (8,c) and bit7 clear
                    top = None; mids = []
                    for r2 in range(r + 1, H):
                        v = col[r2]
                        if v & 0x80 == 0 and (v & 0x0c) == 0x08 and v in (0x08, 0x09, 0x0a, 0x0b, 0x18,0x28,0x38,0x48):
                            top = r2; break
                        if v & 0x80 == 0 and (v & 0x0c) == 0x0c: mids.append(r2)
                    between = [(r2, '%02x' % col[r2]) for r2 in range(r + 1, (top if top is not None else H)) if col[r2]]
                    # neighbours: cell value left/right at start row and top row
                    def nb_(rr): return ('%02x' % g[(a - 1) % 16][rr], '%02x' % g[(a + 1) % 16][rr])
                    print(f"  col {a:2d}: bottom row {r:2d}  top row {top}  stations {mids}  len {None if top is None else top-r}  between {between}  L/R@bottom {nb_(r)}  L/R@top {nb_(top) if top is not None else None}  L/R@top+? {nb_(top+0) if top else ''}")
                    used.add((a, r)); 
                    if top is not None: used.add((a, top))
                    for x in mids: used.add((a, x))
        for a in range(16):
            for r in range(H):
                v = g[a][r]
                if v in (0x08, 0x0c) and (a, r) not in used:
                    print(f"  UNPAIRED marker {v:02x} at col {a} row {r}")
