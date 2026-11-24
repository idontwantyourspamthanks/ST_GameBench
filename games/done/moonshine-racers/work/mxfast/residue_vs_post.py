"""Reorder feasibility: (R) addresses an extras group leaves different from before it (mx build, X_TEST=n) vs (Q) addresses the post stages ($7b52-$7b74, stock game) read.
python3 residue_vs_post.py DUMP KIND NPASS NX"""
import sys, collections
from mflib import *
dump, kind, npass, nx = DUMPS.get(sys.argv[1], sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
sy = symbols(GAME + '/patches/mx_sync.s')
x = Emu(dump); apply_live(x, live_build('X', 'cmp_X')); x.setb(0xB8F21, nx)
s = Emu(dump)
R = collections.Counter(); Q = collections.Counter()
for p in range(npass):
    v = schedule(p, kind)
    for e in (x, s): e.setb(0x6105, v)
    x.setb(0xB8F08, 0); x.setl(0xB8F00, 30 * (p + 1))
    x.run(0x7a88, 0x7b74); before = x.read(0, 0xb2700)
    x.run(0x7b74, sy['extras']); x.run(sy['extras'], 0x7b7a)
    after = x.read(0, 0xb2700)
    for a in range(0x1000, 0xb2700):
        if before[a] != after[a] and not (0x70000 <= a < 0x80000): R[a] += 1
    x.run(0x7b7a, 0x7a88)
    s.run(0x7a88, 0x7b52); s.trace(True); s.run(0x7b52, 0x7b74)
    for a in s.rd: Q[a] += 1
    s.trace(False); s.call(0xd1ca); s.run(0x7b7a, 0x7a88)
inter = sorted(set(R) & set(Q))
print(sys.argv[1:], 'residue addresses', len(R), 'post-stage read addresses', len(Q), 'intersection', len(inter))
def runs(l):
    r = []
    for a in l:
        if r and a - r[-1][1] <= 1: r[-1][1] = a
        else: r.append([a, a])
    return r
print(' residue runs:', ' '.join(f'{a:x}-{b:x}' for a, b in runs(sorted(R))[:60]))
print(' intersection runs:', ' '.join(f'{a:x}-{b:x}' for a, b in runs(inter)))
