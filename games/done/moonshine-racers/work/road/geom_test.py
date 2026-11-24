import sys
from rdlib import *
prefix = sys.argv[1] if len(sys.argv) > 1 else 'live_geom'
nfr = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SITES = [(0x100b4, 0x100c0)]
def masked(m): 
    m = bytearray(m)
    for a, b in SITES: m[a:b] = bytes(b - a)
    return bytes(m)
# first-run path (tables generated) on frame 0 of every scene, then steady state with the tables preloaded
bad = 0; tot = 0; cs = []; cp = []; first = []
tabs = None
for sc in ['grid', 'start', 'up', 'drive']:
    for p in range(0, nfr):
        f = load(sc, p)
        ram = ram_for(f, 'a')
        e1 = Emu(ram); e1.call(0x17c24); c1 = e1.call(0x100b4); m1 = masked(e1.rd(0, 0xB2700))
        e2 = Emu(ram); apply_live(e2, prefix)
        if tabs is not None and p > 0: e2.wr(0xC0000, tabs)
        e2.call(0x17c24); c2 = e2.call(0x100b4)
        m2 = masked(e2.rd(0, 0xB2700))
        if tabs is None: tabs = e2.rd(0xC0000, 0xB000)
        if p == 0: first.append(c2)
        tot += 1
        if m1 != m2:
            bad += 1
            d = [i for i in range(0xB2700) if m1[i] != m2[i]]
            if bad <= 3: print('MISMATCH', sc, p, len(d), [hex(x) for x in d[:12]])
        else:
            cs.append(c1)
            if p > 0: cp.append(c2)
print('frames', tot, 'mismatching', bad, '| stock cycles mean', round(sum(cs) / len(cs)), '| patched steady mean', round(sum(cp) / len(cp)), '| first call (table generation)', first)
