"""Main frames of a candidate build (with X_TEST extras) vs the stock game, per pass (emulator).  python3 pixmain.py SET LEVEL|name KIND NPASS NTEST
Also the residue enumeration of work/int/mx/residue2.py in one number: differing main-frame pixels (bytes) per pass; expected 0 (the HUD build removed the clouds)."""
import sys
from unicorn import UC_HOOK_CODE
from mflib import *
vs, dump, kind, npass, nx = sys.argv[1], DUMPS.get(sys.argv[2], sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
S = Emu(dump); C = Emu(dump); apply_live(S, live_build('F', 'pix_F')); apply_live(C, live_build(vs, 'pix_' + vs)); C.setb(0xB8F21, nx)
C.fl = []
C.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: C.fl.append(bytes(uc.mem_read(C.l(0x1008), 0x7d00))), begin=0xd1ca, end=0xd1ca)
bad = 0; worst = 0; n = 0
for p in range(npass):
    v = schedule(p, kind)
    for e in (S, C): e.setb(0x6105, v)
    S.run(0x7a88, 0x7b74); fs = S.read(S.l(0x1008), 0x7d00); S.call(0xd1ca)
    C.setb(0xB8F08, 0); C.setl(0xB8F00, 30 * (p + 1)); C.fl = []; C.run(0x7a88, 0x7b7a)
    fc = C.fl[0]; n += 1
    d = sum(1 for i in range(0x7d00) if fs[i] != fc[i])
    if d: bad += 1; worst = max(worst, d)
    S.run(0x7b7a, 0x7a88); C.run(0x7b7a, 0x7a88)
print(f'{vs} {sys.argv[2]} {kind} ntest {nx}: {n} main frames vs stock, differing {bad}, worst {worst} bytes; extra frames drawn {C.l(0xB8F38)}')
