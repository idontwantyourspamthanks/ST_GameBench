"""mutation tests: same pokes to stock and patched emulator at pass 0, compare RAM each pass. python3 emmut.py DUMP LIVE npass MODE"""
import sys, json, numpy as np
sys.path.insert(0,'../extrap'); sys.path.insert(0,'.')
from emu import Emu
from proto import flip
import emgate
dump, live, npass, mode = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
a = Emu(dump); b = Emu(dump); spec = emgate.apply_live(b, live)
mask = np.ones(0x100000, bool)
for lo, hi in emgate.MASK: mask[lo:min(hi,0x100000)] = False
for s in spec['sites']: mask[s['addr']:s['addr']+len(bytes.fromhex(s['new']))] = False
def mutate(e):
    slots = [0x2d80 + n*0x38 for n in range(32) if e.b(0x2d80+n*0x38+4) & 1 and e.w(0x2d80+n*0x38+0xc) == 0]
    for i, sl in enumerate(slots):
        d = e.l(sl+0x34)
        if mode == 'flag2' and i % 3 == 0: e.setb(sl+4, e.b(sl+4) | 4)
        if mode == 'noflag7' and i % 2 == 0: e.setb(sl+4, e.b(sl+4) & 0x7f)
        if mode == 'both' and i % 2 == 1: e.setb(sl+4, (e.b(sl+4) | 4) & 0x7f)
        if mode == 'cf' and i % 4 == 0:
            fr = e.w(sl+6) + e.w(sl+8)
            if e.b(sl+4) & 0x80: fr = fr*8 + e.w(sl+0x12)
            e.setw(d + fr*14 + 0xc, 0xf)
        if mode == 'cbad' and i % 4 == 0:
            fr = e.w(sl+6) + e.w(sl+8)
            if e.b(sl+4) & 0x80: fr = fr*8 + e.w(sl+0x12)
            e.setw(d + fr*14 + 0xc, 0x9)
for e in (a, b): mutate(e)
from unicorn import UC_HOOK_CODE
COV = {x: 0 for x in (0xb69a4, 0xb69bc, 0xb698e, 0xb6996, 0xb69b2, 0xb69ac)}
def hk(uc, addr, size, ud): COV[addr] += 1
for x in COV: b.uc.hook_add(UC_HOOK_CODE, hk, None, x, x)
bad = {}
for p in range(npass):
    for e in (a, b):
        e.setb(0x6105, 1)
        try: e.run(0x7a88, 0x7b74); flip(e)
        except Exception as ex: print('stop', p, str(ex)[:80]); break
    x = np.frombuffer(a.read(0,0x100000), np.uint8); y = np.frombuffer(b.read(0,0x100000), np.uint8)
    d = np.nonzero((x != y) & mask)[0]
    for q in d: bad.setdefault(int(q), p)
    for e in (a, b):
        try: e.run(0x7b7a, 0x7a88)
        except Exception: pass
print({hex(k): v for k, v in COV.items()}); print(mode, live, 'passes', npass, 'differing addrs', len(bad), sorted(bad)[:8])
