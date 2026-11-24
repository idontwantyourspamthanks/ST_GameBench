"""Characterise the extra frames of mg_sync (G) that differ from mx_sync (X) below the HUD strip.  python3 char_g.py DUMP KIND NPASS NTEST [png-prefix]"""
import sys, collections
import numpy as np
from unicorn import UC_HOOK_CODE
sys.path.insert(0, '../hud/build'); sys.path.insert(0, '../../tools')
from mflib import *
import msrmask
import emuhud
dumpn, kind, npass, nx = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]); dump = DUMPS[dumpn]
def mk(v, tag):
    e = Emu(dump); apply_live(e, live_build(v, tag)); e.setb(0xB8F21, nx); e.flips = []
    e.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: e.flips.append(bytes(uc.mem_read(e.l(0x1008), 0x7d00))), begin=0xd1ca, end=0xd1ca)
    return e
X = mk('X', 'cmp_ref'); G = mk('G', 'cmp_cand')
names = {0x1315: 'lateral/steer state $1315', 0x1318: 'lateral position $1318', 0x1319: 'lateral position $1318', 0x1324: '$1324', 0x1325: '$1325', 0x10bb: 'HUD $10bb', 0x11ce: 'alarm flag $11ce', 0x10d8: 'speed $10d8', 0x10d9: '$10d9', 0x10da: '$10da', 0x10db: '$10db'}
out = []; worst = (0, None)
for p in range(npass):
    v = schedule(p, kind)
    for e in (X, G): e.setb(0x6105, v); e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1)); e.flips = []; e.run(0x7a88, 0xb8400)
    xa, xb = X.read(0x1000, 0xb1700), G.read(0x1000, 0xb1700)
    dd = [0x1000 + i for i in range(len(xa)) if xa[i] != xb[i] and not (0x70000 <= 0x1000 + i < 0x80000) and not (0x7b00 <= 0x1000 + i < 0x7c00)]
    ent = []
    for a in dd:
        if a in names: ent.append(f'{names[a]}: X {xa[a-0x1000]:02x} / G {xb[a-0x1000]:02x}')
        elif 0x2c68 <= a < 0x36e8:
            s_, o = divmod(a - 0x2c68, 56)
            if o in (0, 1, 2, 3, 0x20, 0x21): ent.append(f'slot {s_} +${o:x}: X {xa[a-0x1000]:02x} / G {xb[a-0x1000]:02x}')
    for e in (X, G): e.run(0xb8400, 0x7b7a)
    for fi, (fx, fg) in enumerate(zip(X.flips, G.flips)):
        if fx == fg: continue
        ix, ig = msrmask.planar_to_idx(fx), msrmask.planar_to_idx(fg)
        dm = ix != ig; rows = np.where(dm.any(1))[0]
        if rows[-1] < 16: continue
        low = dm.copy(); low[:16] = False
        def runs_(idx, gap):
            r = []
            for v in idx:
                if r and v - r[-1][1] <= gap: r[-1][1] = v
                else: r.append([v, v])
            return r
        rects = []
        for r0, r1 in runs_(np.where(low.any(1))[0], 6):
            sub = low[r0:r1 + 1]
            for c0, c1 in runs_(np.where(sub.any(0))[0], 16):
                rects.append((int(r0), int(r1), int(c0), int(c1), int(sub[:, c0:c1 + 1].sum())))
        tot = int(low.sum()); hud = int(dm[:16].sum())
        out.append(dict(p=p, flip=fi, total_px=tot, hud_px=hud, rects=rects, entry=ent[:8]))
        if tot > worst[0]: worst = (tot, (ix, ig, p, fi))
    for e in (X, G): e.run(0x7b7a, 0x7a88)
print(f'{dumpn} {kind} {npass} passes, n={nx}: frames differing below the HUD strip: {len(out)}')
for o in out: print('  pass %d flip %d: %d px below strip (+%d in the strip); rects (row0-row1, col0-col1, px): %s; post-stage changes seen at group entry: %s' % (o['p'], o['flip'], o['total_px'], o['hud_px'], o['rects'], '; '.join(o['entry']) or '-'))
if len(sys.argv) > 5 and worst[1]:
    ix, ig, p, fi = worst[1]
    for nm, im in (('X', ix), ('G', ig)): emuhud.to_png(im, f'shots/{sys.argv[5]}_{nm}.png', scale=2)
    d = np.zeros((200, 320), np.uint8); d[ix != ig] = 15
    emuhud.to_png(d, f'shots/{sys.argv[5]}_diff.png', scale=2)
    print('worst: pass', p, 'flip', fi, 'png shots/' + sys.argv[5] + '_{X,G,diff}.png')
