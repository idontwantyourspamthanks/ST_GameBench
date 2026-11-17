"""Slot bytes (by field offset) that differ at the end of an extra frame (its flip) from S (state at group start) and from P (the pre-draw copy).  python3 slots_trace2.py KIND NPASS NX [dump]"""
import sys, collections
from mflib import *
kind, npass, nx = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); dump = DUMPS[sys.argv[4]] if len(sys.argv) > 4 else DUMPS['start']
pre = live_build('X'); sy = symbols(GAME + '/patches/mx_sync.s')
e = Emu(dump); apply_live(e, pre); e.setb(0xB8F21, nx)
SL0 = 0x2c68
dS = collections.Counter(); dP = collections.Counter(); nslots = collections.Counter(); act = collections.Counter()
for p in range(npass):
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
    e.run(0x7a88, 0x7b74)
    e.run(0x7b74, sy['saveundo']); S = e.read(SL0, 2688); P = e.read(0xB9E00, 2688)
    # run to each extra's flip
    for j in range(nx):
        e.run(e.uc.reg_read(__import__('unicorn').m68k_const.UC_M68K_REG_PC) if j else sy['saveundo'], 0xd1ca) if False else None
    # simpler: step to flips by hooking: run from saveundo to restoreundo is one call; use code hook on 0xd1ca
    flips = []
    from unicorn import UC_HOOK_CODE
    def hk(uc, addr, size, ud):
        if addr == 0xd1ca: flips.append(bytes(uc.mem_read(SL0, 2688)))
    h = e.uc.hook_add(UC_HOOK_CODE, hk, begin=0xd1ca, end=0xd1ca)
    e.run(sy['saveundo'], sy['restoreundo']); e.uc.hook_del(h)
    if p >= 3:
        for X in flips:
            for i in range(2688):
                if X[i] != S[i]: dS[i % 0x38] += 1
                if X[i] != P[i]: dP[i % 0x38] += 1
        # active slot count: flag byte +4 bit0
        for s in range(48): act[(S[s * 0x38 + 4] & 1)] += 1
    e.run(sy['restoreundo'], 0x7b7a); e.run(0x7b7a, 0x7a88)
print('extra end vs S, by field offset:', sorted(dS.items()))
print('extra end vs P, by field offset:', sorted(dP.items()))
print('flag bit0 per slot (0 / 1):', dict(act))
