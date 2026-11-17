import sys
from rdlib import *
prefix = sys.argv[1]; nfr = int(sys.argv[2]) if len(sys.argv) > 2 else 60
SITES = [(0x17c42, 0x17c4a)]
def masked(m):
    m = bytearray(m)
    for a, b in SITES: m[a:b] = bytes(b - a)
    return bytes(m)
bad = 0; tot = 0; cs = []; cp = []; first = []; tabs = None
for sc in ['grid', 'start', 'up', 'drive']:
    for p in range(nfr):
        f = load(sc, p); ram = ram_for(f, 'b'); bb = u32(f['a_lo'], 8)
        ram = bytearray(ram); ram[0x1008:0x100c] = bb.to_bytes(4, 'big'); ram = bytes(ram)
        e1 = Emu(ram); c1 = e1.call(0x17c42); m1 = masked(e1.rd(0, 0xE8400))
        e2 = Emu(ram); apply_live(e2, prefix)
        if tabs is not None: e2.wr(0xCB000, tabs)
        c2 = e2.call(0x17c42); m2 = masked(e2.rd(0, 0xCB000)) + e2.rd(0xCB000, 0xE8400 - 0xCB000)
        if tabs is None: tabs = e2.rd(0xCB000, 0xD000)
        tot += 1
        a = m1[:0xB2700]; b = m2[:0xB2700]
        if a != b:
            bad += 1
            d = [i for i in range(0xB2700) if a[i] != b[i]]
            if bad <= 4: print('MISMATCH', sc, p, len(d), [hex(x) for x in d[:10]])
        else:
            cs.append(c1)
            if tabs is not None and (sc, p) != ('grid', 0): cp.append(c2)
        if len(first) < 1: first.append(c2)
print('frames', tot, 'mismatching', bad, '| stock mean', round(sum(cs) / len(cs)), '| patched steady mean', round(sum(cp) / max(1, len(cp))), '| first call', first)
