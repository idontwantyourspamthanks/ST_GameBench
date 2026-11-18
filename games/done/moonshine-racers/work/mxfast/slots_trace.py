"""Which slot bytes change between the pre-draw copy P and the end of the pass S, and which does an extra write?  python3 slots_trace.py KIND NPASS NX [dump]"""
import sys, collections
from mflib import *
kind, npass, nx = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); dump = DUMPS[sys.argv[4]] if len(sys.argv) > 4 else DUMPS['start']
pre = live_build('X'); sy = symbols(GAME + '/patches/mx_sync.s')
e = Emu(dump); apply_live(e, pre); e.setb(0xB8F21, nx)
SL0, SL1 = 0x2c68, 0x36e8
wpost = collections.Counter(); wext = collections.Counter(); diffPS = collections.Counter(); other = collections.Counter()
nslot = 56
def sloff(a): return (a - SL0) % 0x38
for p in range(npass):
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
    e.run(0x7a88, 0x7b46)
    e.trace(True); e.run(0x7b46, 0x7b74)
    wr = dict(e.wr); e.trace(False)
    P = e.read(0xB9E00, 2688); S = e.read(SL0, 2688)
    if p >= 3:
        for a in wr:
            if SL0 <= a < SL1: wpost[sloff(a)] += 1
        for i in range(2688):
            if P[i] != S[i]: diffPS[(i % 0x38)] += 1
    e.run(0x7b74, sy['saveundo'])
    e.trace(True); e.run(sy['saveundo'], sy['restoreundo'])
    wr = dict(e.wr); e.trace(False)
    if p >= 3:
        for a in wr:
            if SL0 <= a < SL1: wext[sloff(a)] += 1
    e.run(sy['restoreundo'], 0x7b7a); e.run(0x7b7a, 0x7a88)
print('slot field offsets written by e406/post stages (count over passes):', sorted(wpost.items()))
print('slot field offsets where P != S:', sorted(diffPS.items()))
print('slot field offsets written by the extras:', sorted(wext.items()))
