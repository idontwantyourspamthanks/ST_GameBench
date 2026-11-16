import sys
from gate3 import *
from unicorn import *
from unicorn.m68k_const import *
dump, target, ntest, kind = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
ADDR = 0x70000 + 63 * 160 + 49
def go(patched):
    e = Emu(dump)
    if patched: apply_live(e); e.setb(0xB8F21, ntest)
    log = []
    def hk(uc, access, addr, size, value, ud):
        log.append((uc.reg_read(UC_M68K_REG_PC), addr, size, value))
    for p in range(target + 1):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        h = None
        if p == target: h = [e.uc.hook_add(UC_HOOK_MEM_WRITE, hk, begin=a - 1, end=a + 1) for a in (ADDR, ADDR + 0x8000)]; log.append(('buf', hex(e.l(0x1008))))
        if patched:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, 36 * (p + 1)); e.run(0x7a88, 0xb8100); e.run(0xb8100, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); flip(e)
        if h:
            for x in h: e.uc.hook_del(x)
        e.run(0x7b7a, 0x7a88)
    return log
for name, pa in (("stock", False), ("mx", True)):
    print(name)
    for x in go(pa): print("  ", [hex(v) if isinstance(v, int) else v for v in x])
