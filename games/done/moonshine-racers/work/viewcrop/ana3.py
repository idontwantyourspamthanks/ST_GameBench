"""Slot (16-px group) identity by pose gap, and the fills share of rd_draw.  python3 ana3.py PKL"""
import sys, numpy as np
from ana import load
for p in sys.argv[1:]:
    F, nx, w = load(p); by = {f['idx']: f for f in F}; acc = {}
    for f in F:
        if f['kind'] != 'extra' or f['rowcyc'] is None: continue
        for d in range(1, 3 * (nx + 1) + 1):
            g = by.get(f['idx'] - d)
            if g is None or 'final' not in g or g['pass_'] < 1: continue
            gap = round(f['t'] - g['t'], 2)
            gi = np.frombuffer(g['final'], np.uint8).reshape(200, 20, 8); fx = np.frombuffer(f['exit'], np.uint8).reshape(200, 20, 8)
            n = len(f['recs']); rows = 199 - np.arange(n)
            eq = (gi[rows] == fx[rows]).all(axis=2)          # n x 20
            # same-F rows: rows whose F stripe bits equal (grass/road colours unchanged)
            fs = np.array([(f['recs'][k][3] >> 13) == (g['recs'][k][3] >> 13) if k < len(g['recs']) else False for k in range(n)])
            a = acc.setdefault(gap, [0, 0, 0, 0, 0])
            a[0] += eq.sum(); a[1] += eq.size; a[2] += eq[fs].sum(); a[3] += eq[fs].size; a[4] += fs.sum()
    print('==', p.split('/')[-1])
    for gap in sorted(acc):
        a = acc[gap]
        print(f"  gap {gap:4.2f} tick: road slots equal {100*a[0]/a[1]:5.1f}%   rows with equal stripe bits {100*a[4]/(a[1]/20):5.1f}%, slots equal in those rows {100*a[2]/max(a[3],1):5.1f}%")
