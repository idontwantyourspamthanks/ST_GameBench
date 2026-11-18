import sys, struct
from gate3 import *
from unicorn import *
from unicorn.m68k_const import *
dump, target, ntest, kind = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
PCS = [0x17c24, 0x17c42, 0x10a5e, 0x10a98, 0xe2e8, 0xe316, 0xdd50, 0x18318, 0xe406, 0xef7a, 0xde1c, 0xde6c, 0x18888]
def go(patched):
    e = Emu(dump)
    if patched: apply_live(e); e.setb(0xB8F21, ntest)
    snaps = {}
    for p in range(target + 1):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        hs = []
        if p == target:
            def hk(uc, addr, size, ud):
                if addr not in snaps:
                    b = struct.unpack('>I', bytes(uc.mem_read(0x1008, 4)))[0]
                    snaps[addr] = (b, bytes(uc.mem_read(b, 0x7d00)))
            for a in PCS: hs.append(e.uc.hook_add(UC_HOOK_CODE, hk, begin=a, end=a))
        if patched:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, 36 * (p + 1)); e.run(0x7a88, 0xb8100); e.run(0xb8100, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); flip(e)
        for x in hs: e.uc.hook_del(x)
        e.run(0x7b7a, 0x7a88)
    return snaps
A = go(False); X = go(True)
for pc in PCS:
    if pc in A and pc in X:
        a, x = A[pc][1], X[pc][1]
        d = [(i // 160, i % 160) for i in range(0x7d00) if a[i] != x[i]]
        rows = sorted(set(r for r, c in d))
        print(f"stage ${pc:x}: buffers {A[pc][0]:x}/{X[pc][0]:x}; differing bytes {len(d)}; rows {rows[:3]}..{rows[-3:]}; row 63 diff {[c for r,c in d if r==63]}")
