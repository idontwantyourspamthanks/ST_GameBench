"""PCs and slot offsets written into the slots by e406 (7b46->7b4c) / HUD / post stages, with the written value changing or not."""
import sys, collections
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_PC
from mflib import *
dump = DUMPS[sys.argv[1]]; kind = sys.argv[2]; npass = int(sys.argv[3])
e = Emu(dump)
cur = {'ph': None}; res = collections.defaultdict(collections.Counter)
def hk(uc, access, addr, size, value, ud):
    if 0x2c68 <= addr < 0x36e8:
        pc = uc.reg_read(UC_M68K_REG_PC)
        old = bytes(uc.mem_read(addr, size))
        res[cur['ph']][(hex(pc), (addr - 0x2c68) % 56, size)] += 1
e.uc.hook_add(UC_HOOK_MEM_WRITE, hk)
for p in range(npass):
    v = schedule(p, kind); e.setb(0x6105, v)
    e.run(0x7a88, 0x7b46); cur['ph'] = 'e406'; e.run(0x7b46, 0x7b4c); cur['ph'] = 'hud'; e.run(0x7b4c, 0x7b52); cur['ph'] = 'post'; e.run(0x7b52, 0x7b74); cur['ph'] = None
    e.call(0xd1ca); e.run(0x7b7a, 0x7a88)
for ph in ('e406', 'hud', 'post'):
    print(ph, sorted(res[ph].items())[:60])
