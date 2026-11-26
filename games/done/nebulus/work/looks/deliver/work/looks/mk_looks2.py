#!/usr/bin/env python3
"""Fixtures for the per-level look gate (NebLooksBuild).  All grids identical (mk_looks.grid); levels differ in base tower / colours / enemies only.
usage: mk_looks2.py DIR   -> DIR/looks15.ovl (15 levels, campaign LOOKS), DIR/base8.ovl (levels T1..T8 flags 0, campaign BASE), DIR/orig16.ovl (campaign ORIG: 16 original towers),
                              DIR/all12.ovl (12 levels: every nibble extreme + odd/even records)
looks15 cells (b = base tower index 0..7, c = colours 0..8, e = enemies 0..4):  A: b=2 e=2 c=1..8 | B: b=0 c=3 e=1..4 | C: (5,0,0) (1,0,3) (6,4,0)"""
import sys, importlib.util
sys.path.insert(0, 'work/editor')
import ovl
spec = importlib.util.spec_from_file_location('mk_looks', 'work/looks/mk_looks.py')
src = open('work/looks/mk_looks.py').read().replace("main(sys.argv[1], len(sys.argv)>2 and sys.argv[2]=='even')", "")
ns = {}; exec(compile(src, 'mk_looks.py', 'exec'), ns)
grid, ROWS = ns['grid'], ns['ROWS']
CELLS = [(2, c, 2) for c in range(1, 9)] + [(0, 3, e) for e in range(1, 5)] + [(5, 0, 0), (1, 0, 3), (6, 4, 0)]
def mk(out, cells, cname, even=False, order=None):
    lv = [ovl.level(1, b, ROWS, grid(even), time=0x0600, name="LOOK", colours=c, enemies=e) for b, c, e in cells]
    open(out, 'wb').write(ovl.build(lv, [ovl.camp(cname, list(range(len(lv))))]))
d = sys.argv[1]
mk(f'{d}/looks15.ovl', CELLS, 'LOOKS')
mk(f'{d}/base8.ovl', [(t, 0, 0) for t in range(8)], 'BASE')
open(f'{d}/orig16.ovl', 'wb').write(ovl.build([], [ovl.camp('ORIG', [ovl.orig(m, t) for m in (1, 2) for t in range(8)])]))
# all12: every nibble extreme, alternating odd/even record sizes, base towers cycling
c12 = [((i * 3) % 8, (0, 8, 1, 7, 4, 2, 8, 0, 5, 3, 6, 8)[i], (0, 4, 4, 0, 1, 2, 3, 4, 2, 1, 3, 0)[i]) for i in range(12)]
lv = [ovl.level(1 + (i & 1), c12[i][0], ROWS, grid(i & 1), time=0x0500, name=f"K{i}", colours=c12[i][1], enemies=c12[i][2]) for i in range(12)]
open(f'{d}/all12.ovl', 'wb').write(ovl.build(lv, [ovl.camp('ALL12', list(range(12)))]))
# eyes4: base tower T1, colours 0, enemies 0..4 (same grid with two vertical eyes next to the frog: play WITHOUT the enemies-off trainer to see the discs)
mk(f'{d}/eyes5.ovl', [(0, 0, e) for e in range(5)], 'EYES')
for f in ('looks15', 'base8', 'orig16', 'all12', 'eyes5'):
    raw = open(f'{d}/{f}.ovl', 'rb').read(); print(f, ovl.validate(raw) or 'valid', 'odd starts', ovl.odd_starts(raw))
