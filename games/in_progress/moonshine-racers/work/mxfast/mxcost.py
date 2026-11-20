"""Cycles of the whole pass incl. extras (Musashi, plain 68000) per code range, X_TEST=n extras.  python3 mxcost.py SET DUMP KIND NX PASS... [labels]"""
import sys, collections
import numpy as np
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/viewcrop')
from mflib import *
import mlib
FULL = 'full' in sys.argv
vset, dump, kind, nx = sys.argv[1], DUMPS.get(sys.argv[2], sys.argv[2]), sys.argv[3], int(sys.argv[4])
targets = [int(x) for x in sys.argv[5:] if x.isdigit()]
SRC = {'X': '/patches/mx_sync.s', 'M': '/patches/mf_sync.s', 'G': '/patches/mg_sync.s', 'T': '/patches/mt_sync.s'}[vset]
import mflib
lm = labelmap(mflib.GAME + SRC) if vset != 'T' else []
pre = live_build(vset, 'cost_' + vset)
e = Emu(dump); apply_live(e, pre); e.setb(0xB8F21, nx)
def lab(a):
    best = None
    for x, l in lm:
        if x <= a: best = l if FULL else l.split('.')[0]
        else: break
    return best
RR = [(0xb4000, 0xb5000, 'rd_geom'), (0xb5000, 0xb6000, 'rd_draw'), (0xfe50, 0x100b4, 'ring generators fe50/ff76/1003c'), (0xb6d40, 0xb6e00, 'span clear tc_clr'), (0x18318, 0x18888, 'horizon 18318'),
      (0xe316, 0xe406, 'e316 (tc_proj stub)'), (0xb6c00, 0xb6d00, 'tc_proj'), (0xb6820, 0xb6a00, 'tc_ord'), (0xb6a00, 0xb6a80, 'tc_dist'), (0xb3040, 0xb3100, 'mr_edge'), (0xbb000, 0xbe000, 'HUD stage hd_stage (TOPBAR)'),
      (0xbe000, 0xbf000, 'ta_* (face/ticker/glyph/erase)'), (0xbf000, 0xc0000, 'tb_car'), (0xd8000, 0xe2c00, 'tb_car cache'), (0x12000, 0x16000, 'sprite kernels'), (0xe406, 0xe800, 'e406/e598'), (0x10a5e, 0x10ca6, 'horizon scroll 10a5e/10a98'),
      (0x11ef0, 0x12000, 'ticker 11ef0'), (0xf90c, 0xfa00, 'face f90c'), (0x100b4, 0x10a5e, 'road geometry 100b4 (stock stub)')]
def cls(pc):
    if 'game' in sys.argv and not (0xb8000 <= pc < 0xbb000):
        for lo, hi, n in RR:
            if lo <= pc < hi: return 'game:' + n
        return 'game:other %x' % (pc >> 12)
    if 0xb8000 <= pc < 0xbb000:
        if pc < 0xb8100: return 'mt_clock'
        if 0xb8300 <= pc < 0xb8380: return 'mx_pre'
        return 'blob:' + str(lab(pc))
    return 'game/other'
tot = collections.defaultdict(list)
for p in range(max(targets) + 1):
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
    if p in targets:
        ram = e.read(0, 0x100000); buf = e.l(0x1008); oth = 0x78000 if buf == 0x70000 else 0x70000
        cyc, pcs, cy, rows = mlib.run(ram, 0x7a88, 0x7b7a, scr=(buf, oth))
        flips = [i for i, pc in enumerate(pcs) if pc == 0xd1ca]
        bounds = flips + [len(pcs)]
        for j in range(len(bounds)):
            lo = 0 if j == 0 else bounds[j - 1]; hi = bounds[j]
            d = collections.Counter()
            for pc, c in zip(pcs[lo:hi], cy[lo:hi]): d[cls(int(pc))] += int(c)
            tot[j].append(d)
        tot['all'].append(collections.Counter({'total': int(cyc)}))
    e.run(0x7a88, 0x7b7a); e.run(0x7b7a, 0x7a88)
for j, L in sorted(tot.items(), key=lambda kv: str(kv[0])):
    keys = set(k for d in L for k in d)
    print('--- segment', j, '(0 = main pass to its flip; later = extra frame incl. its flip; last = tail) mean over', len(L), 'passes: total %.0f' % (sum(sum(d.values()) for d in L) / len(L)))
    if j == 'all': continue
    for k, v in sorted(((k, sum(d[k] for d in L) / len(L)) for k in keys), key=lambda kv: -kv[1]):
        if k.startswith('blob') or k in ('mx_pre', 'mt_clock') or k.startswith('game:'): print('   %-36s %8.0f' % (k, v))
