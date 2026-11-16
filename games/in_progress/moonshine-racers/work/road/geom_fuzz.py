import sys, random
from rdlib import *
prefix = sys.argv[1]; N = int(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
random.seed(seed)
SITES = [(0x100b4, 0x100c0)]
def masked(m):
    m = bytearray(m)
    for a, b in SITES: m[a:b] = bytes(b - a)
    return bytes(m)
frames = [load(sc, p) for sc in ['grid', 'start', 'up', 'drive'] for p in (0, 17, 41)]
bad = 0; stockpath = 0; import collections; stats = collections.Counter(); NEG = len(sys.argv) > 4
tabs = None
for it in range(N):
    f = random.choice(frames); ram = bytearray(ram_for(f, 'a'))
    def W(ad, v): ram[ad:ad + 2] = (v & 0xffff).to_bytes(2, 'big')
    mode = random.choice(['smooth', 'rand', 'rand'])
    W(0x1bba, random.randrange(0, 0x800, 2)); W(0x23c6, random.randrange(0, 0x400)); W(0x13ae, random.randrange(0, 0x400))
    W(0x130a, random.randrange(0, 0x10000)); W(0x130c, random.choice([0, 1, 5, 9, 12, 40])); W(0x1308, random.randrange(0, 16))
    W(0x1318, random.choice([0, random.randrange(0, 0x10000), random.randrange(0, 200), (-random.randrange(0, 200)) & 0xffff]))
    W(0x1316, random.choice([9, 9, 9, random.randrange(0, 178), 178, 179, 300, 0xffff]))
    if mode == 'rand':
        for a in range(0x13b0, 0x1bb0): ram[a] = random.randrange(256)
        for a in range(0x23c8, 0x27c8): ram[a] = random.randrange(256)
        for a in range(0x1bbc, 0x23bc, 2): W(a, random.randrange(-3000, 3000))
    else:
        v = random.randrange(256)
        for a in range(0x13b0, 0x1bb0): v = max(0, min(255, v + random.randrange(-3, 4))); ram[a] = v
        v = random.randrange(256)
        for a in range(0x23c8, 0x27c8): v = (v + random.randrange(-5, 6)) & 255; ram[a] = v
        v = 0
        for a in range(0x1bbc, 0x23bc, 2): v += random.randrange(-40, 41); W(a, v)
    ram = bytes(ram)
    e1 = Emu(ram); e1.call(0x17c24); e1.call(0x100b4); m1 = masked(e1.rd(0, 0xB2700))
    e2 = Emu(ram); apply_live(e2, prefix)
    if tabs is not None: e2.wr(0xD0000, tabs)
    if NEG and tabs is not None: e2.wr(0xD1000, bytes([1]) * 0xA000)
    e2.call(0x17c24); e2.call(0x100b4); m2 = masked(e2.rd(0, 0xB2700))
    if tabs is None or int.from_bytes(e2.rd(0xD0004, 2), 'big') != int.from_bytes(tabs[4:6], 'big'): tabs = e2.rd(0xD0000, 0xB000)
    m0 = int.from_bytes(ram[0x1316:0x1318], 'big'); stats['guard' if m0 > 178 else 'fast'] += 1
    nrec = (0x4f78 - int.from_bytes(m1[0x4b84:0x4b88], 'big')) // 8; stats['rec<60' if nrec < 60 else 'rec60+'] += 1
    stats['cut' if int.from_bytes(m1[0x4aa4:0x4aa6],'big') == 0 else 'x'] += 0
    if m1 != m2:
        bad += 1
        d = [i for i in range(0xB2700) if m1[i] != m2[i]]
        if bad <= 5: print('MISMATCH it', it, mode, len(d), [hex(x) for x in d[:10]])
print(dict(stats)); print('fuzz', N, 'cases, mismatches', bad)
