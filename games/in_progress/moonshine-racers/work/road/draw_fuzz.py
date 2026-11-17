import sys, random, struct
from rdlib import *
prefix = sys.argv[1]; N = int(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
NEG = len(sys.argv) > 4
random.seed(seed)
SITES = [(0x17c42, 0x17c4a)]
def masked(m):
    m = bytearray(m)
    for a, b in SITES: m[a:b] = bytes(b - a)
    return bytes(m)
f = load('start', 20)
base = ram_for(f, 'b')
ptrs = [u32(base[0x1362 + 4 * i:], 0) for i in range(15)]
crit = [-80, -64, -48, -40, -33, -32, -31, -20, -17, -16, -15, -1, 0, 1, 15, 16, 17, 31, 32, 48, 100, 150, 270, 287, 288, 289, 300, 303, 304, 305, 319, 320, 321, 336, 340, 400]
def rv():
    return random.choice(crit) + random.choice([0, 0, 0, 1, 2, 7, 15]) if random.random() < 0.7 else random.randint(-90, 420)
bad = 0; tabs = {}
stats = {'rows': 0, 'fast': 0, 'mid': 0}
for it in range(N):
    ptr = ptrs[it % 15]
    ram = bytearray(base)
    ram[0x135a:0x135e] = ptr.to_bytes(4, 'big')
    nrec = random.choice([1, 5, 30, 80, 110, 112])
    recs = []
    for i in range(nrec):
        B = rv(); w = random.choice([0, 20, 40, 60, 100, 200, 400, 600, 33, 800, 1000]) if random.random() < 0.5 else random.randint(0, 120)
        A = B + w if random.random() < 0.8 else rv()
        w0 = random.choice([random.randrange(0, 0x1000, 256)] * 3 + [random.randrange(0, 0x10000)] * (1 if random.random() < 0.03 else 0)) if True else 0
        if random.random() < 0.9: w0 = random.randrange(0x100, 0xc00, 256)
        recs.append((w0, A, B, random.randrange(0, 0x10000)))
        if (A == 0 and B == 0): recs[-1] = (w0, 1, 0, recs[-1][3])
    ram[0x13a0] = 0
    data = b''.join(struct.pack('>HhhH', *r) for r in recs) + bytes(16)
    ram[0x60000:0x60000 + len(data)] = data; ram[0x4b84:0x4b88] = (0x60000).to_bytes(4, 'big'); ram[0x1008:0x100c] = (0x100000).to_bytes(4, 'big')
    ram = bytes(ram)
    e1 = Emu(ram); e1.call(0x17c42); m1 = e1.rd(0, 0xB2700) + e1.rd(0x100000, 0x7d00)
    e2 = Emu(ram); apply_live(e2, prefix)
    if ptr in tabs: e2.wr(0xCB000, tabs[ptr])
    if NEG and ptr in tabs: e2.wr(0xCB000 + 0x800, bytes([0x77]) * 0x4000)
    e2.call(0x17c42)
    if ptr not in tabs: tabs[ptr] = e2.rd(0xCB000, 0xD000)
    m2 = e2.rd(0, 0xB2700) + e2.rd(0x100000, 0x7d00)
    a = bytearray(m1); b = bytearray(m2)
    for x, y in SITES: a[x:y] = bytes(y - x); b[x:y] = bytes(y - x)
    if a != b:
        bad += 1
        d = [i for i in range(len(a)) if a[i] != b[i]]
        if bad <= 5:
            print('MISMATCH it', it, 'ptr', hex(ptr), len(d), [hex(x) for x in d[:8]])
            sa = m1[0xB2700:]; sb = m2[0xB2700:]
            badrows = [k for k in range(len(recs)) if sa[0x7d00 - 160 * (k + 1):0x7d00 - 160 * k] != sb[0x7d00 - 160 * (k + 1):0x7d00 - 160 * k]]
            print('  recs', recs[:6]); print('  records', len(recs), 'bad rows', badrows[:10], [recs[k] for k in badrows[:3]], '$12f0/4 stock', m1[0x12f0:0x12f6].hex(), 'new', m2[0x12f0:0x12f6].hex())
print('draw fuzz', N, 'streams, mismatches', bad)
