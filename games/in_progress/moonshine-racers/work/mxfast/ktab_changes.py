import sys, collections
from mflib import *
kt = [int(x, 16) for x in open('ktab.txt').read().split()]
sy = symbols(GAME + '/patches/mf_sync.s')
ch = collections.Counter()
for d, kind in (('start', 'zig'), ('L3', 'rand'), ('L10', 'left')):
    e = Emu(DUMPS[d]); apply_live(e, live_build('M', 'cmp_cand')); e.setb(0xB8F21, 2)
    for p in range(60):
        v = schedule(p, kind); e.setb(0x6105, v); e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
        e.run(0x7a88, 0x7b74); e.run(0x7b74, sy['saveundo']); e.run(sy['saveundo'], sy['restoreundo'])
        for i, a in enumerate(kt):
            pass
        S = e.read(0xb9bf0, 404)  # saved at U_KERN
        for i, a in enumerate(kt):
            if e.read(a, 4) != S[4 * i:4 * i + 4]: ch[(i, a)] += 1
        e.run(sy['restoreundo'], 0x7b7a); e.run(0x7b7a, 0x7a88)
print(len(ch), 'of', len(kt), 'kernel longs changed by extras in these runs; first:', sorted(ch.items())[:6])
