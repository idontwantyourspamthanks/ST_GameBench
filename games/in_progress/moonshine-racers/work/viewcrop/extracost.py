"""Whole extra frame cost by code range (Musashi): X_TEST=n extras, pass $7a88 -> $7b7a.  python3 extracost.py DUMP KIND NX PASS..."""
import sys, json, collections
import numpy as np
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/work/extrap'); sys.path.insert(0, GAME + '/work/viewcrop')
from gate3 import *
import mlib
dump, kind, nx = sys.argv[1], sys.argv[2], int(sys.argv[3]); targets = [int(x) for x in sys.argv[4:]]
LIVE = GAME + '/work/viewcrop/live/X'
e = Emu(dump); spec = json.load(open(LIVE + '.json')); e.write(spec['img_base'], open(LIVE + '.img', 'rb').read())
for s in spec['sites']: e.write(s['addr'], bytes.fromhex(s['new']))
e.setb(0xB8F21, nx)
R = [(0xb4000, 0xb5000, 'rd_geom'), (0xb5000, 0xb6000, 'rd_draw'), (0xfe50, 0xff76, 'ring fe50'), (0xff76, 0x1003c, 'ring ff76'), (0x1003c, 0x100b4, 'ring 1003c'),
     (0xb6d40, 0xb6e00, 'span clear'), (0x18318, 0x18888, 'horizon 18318'), (0xe316, 0xe406, 'e316'), (0xb6c00, 0xb6d00, 'tc_proj'), (0xb6820, 0xb6a00, 'tc_ord'), (0xb6a00, 0xb6a80, 'tc_dist'),
     (0xb3040, 0xb3100, 'mr_edge'), (0xbb000, 0xbe000, 'HUD stage (hd_stage)'), (0xbe000, 0xbf000, 'ta_*'), (0xbf000, 0xc0000, 'tb_car'), (0xd8000, 0xe2c00, 'tb_car cache'),
     (0xb8000, 0xbb000, 'mx/mt blobs'), (0x12000, 0x16000, 'sprite kernels'), (0xe406, 0xe800, 'e406'), (0x10a5e, 0x10ca6, 'raster/horizon scroll 10a5e/10a98'), (0xe2e8, 0xe316, 'e2e8'), (0x1182e, 0x11a3c, 'cars 1182e'),
     (0x11ef0, 0x12000, 'ticker 11ef0'), (0xf90c, 0xfa00, 'face f90c')]
def cls(pc):
    for lo, hi, n in R:
        if lo <= pc < hi: return n
    return 'other %x' % (pc >> 12)
tot = collections.defaultdict(list)
for p in range(max(targets) + 1):
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
    if p in targets:
        ram = e.read(0, 0x100000); buf = e.l(0x1008); oth = 0x78000 if buf == 0x70000 else 0x70000
        cyc, pcs, cy, rows = mlib.run(ram, 0x7a88, 0x7b7a, scr=(buf, oth))
        flips = [i for i, pc in enumerate(pcs) if pc == 0xd1ca]
        print('pass', p, 'total', cyc, 'flips at instr', flips, file=sys.stderr)
        bounds = flips + [len(pcs)]
        # frame 0 = start..first flip; frame j = flip j-1 .. flip j
        for j in range(len(bounds)):
            lo = 0 if j == 0 else bounds[j - 1]; hi = bounds[j]
            d = collections.Counter()
            for pc, c in zip(pcs[lo:hi], cy[lo:hi]): d[cls(int(pc))] += int(c)
            tot[j].append(d)
    e.run(0x7a88, 0x7b7a); e.run(0x7b7a, 0x7a88)
for j, L in sorted(tot.items()):
    keys = set(k for d in L for k in d)
    print('--- segment', j, '(0 = main pass up to its flip; later = extra frame incl. its flip; last = tail), mean over', len(L), 'passes: total %.0f' % (sum(sum(d.values()) for d in L) / len(L)))
    for k, v in sorted(((k, sum(d[k] for d in L) / len(L)) for k in keys), key=lambda kv: -kv[1])[:14]:
        print('   %-36s %8.0f' % (k, v))
