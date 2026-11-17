"""Who reads [$4b88,$4f88)?  Unicorn read hook with PC.  python3 rtrace.py DUMP NPASS LIVE sched"""
import sys, collections
sys.path.insert(0,'../extrap'); sys.path.insert(0,'.')
from emu import Emu
from proto import flip
from unicorn import UC_HOOK_MEM_READ
from unicorn.m68k_const import *
import emgate
dump, npass, live, kind = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
e = Emu(dump)
if live != 'none': emgate.apply_live(e, live)
st = collections.defaultdict(lambda: [0, 1 << 30, 0, 0])   # pc -> [reads, min addr, max addr, reads below the current stream start]
def hk(uc, access, addr, size, val, ud):
    pc = uc.reg_read(UC_M68K_REG_PC)
    r = st[pc]; r[0] += 1; r[1] = min(r[1], addr); r[2] = max(r[2], addr + size - 1)
    p = e.l(0x4b84)
    if addr < p and 0x4b88 <= p <= 0x4f78: r[3] += 1
e.uc.hook_add(UC_HOOK_MEM_READ, hk, None, 0x4b88, 0x4f87)
for p in range(npass):
    v = emgate.schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.run(0x7a88, 0x7b74); flip(e); e.run(0x7b7a, 0x7a88)
print(f'{live} {kind} {npass} passes: reads of $4b88-$4f87 by PC (reads, min addr, max addr, reads below the current stream start $4b84):')
for pc, r in sorted(st.items()): print(f'  pc ${pc:06x}: {r[0]:7d} reads, ${r[1]:05x}-${r[2]:05x}, below stream start: {r[3]}')
