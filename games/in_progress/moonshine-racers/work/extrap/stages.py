import sys, pickle
from emu import *
snap = sys.argv[1] if len(sys.argv) > 1 else 'h_start_7a88.bin'
e = Emu(snap)
e.trace(True)
sites = [0x7a8c + 6*i for i in range(0x7b52 - 0x7a8c) if 0x7a8c + 6*i < 0x7b52]
names = []
res = []
def region(a):
    if a < 0x7000: return 'low'
    if 0x70000 <= a < 0x80000: return 'scr'
    if a >= 0xff0000: return 'io'
    return 'other'
cur = 0x7a88
stages = []
x = 0x7a8c
while x < 0x7b52:
    stages.append((x, e.l(x+2), x + 6)); x += 6
stages.append((0x7b52, 0x18888, 0x7b5e)); stages.append((0x7b5e, 0x18c86, 0x7b64)); stages.append((0x7b64, 0x18f0e, 0x7b6a))
cur = 0x7a88
for site, tgt, until in stages:
    e.rd.clear(); e.wr.clear()
    if site == 0x7b52 or site == 0x7b5e or site == 0x7b64: cur = site
    start = cur
    e.run(start, until)
    cur = until
    res.append((tgt, dict(e.rd), dict(e.wr)))
pickle.dump(res, open('stage_rw.pkl', 'wb'))
for tgt, rd, wr in res:
    lw = sorted(a for a in wr if region(a) == 'low'); ow = sorted(a for a in wr if region(a) == 'other')
    def runs(l):
        r = []
        for a in l:
            if r and a - r[-1][1] <= 1: r[-1][1] = a
            else: r.append([a, a])
        return ' '.join(f"{s:x}" + (f"-{t:x}" if t != s else '') for s, t in r)
    print(f"{tgt:06x} W low: {runs(lw)[:600]}  other: {runs(ow)[:200]}  nscr={sum(1 for a in wr if region(a)=='scr')}")
