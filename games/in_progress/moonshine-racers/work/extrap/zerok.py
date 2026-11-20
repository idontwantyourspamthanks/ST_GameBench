"""zero-advance extras must reproduce the main frame exactly (every HUD part, clouds, objects...). python3 zerok.py DUMP KIND NEXTRA NP"""
import sys
from pix3 import *
dump, kind, n, NP = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
e = Emu(dump); apply_live(e); e.setb(0xB8F21, 0x80 | n)
shots = []
def hk(uc, addr, size, ud):
    b = struct.unpack('>I', uc.mem_read(0x1008, 4))[0]
    shots.append((e.w(0x100e), bytes(uc.mem_read(b, 0x7d00))))
e.uc.hook_add(UC_HOOK_CODE, hk, begin=0xd1ca, end=0xd1cb)
for p in range(NP):
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.setb(0xB8F08,0); e.setl(0xB8F00,36*(p+1))
    e.run(0x7a88, 0x7b7a); e.run(0x7b7a, 0x7a88)
groups = {}
for cnt, fr in shots: groups.setdefault(cnt, []).append(fr)
bad = 0; nf = 0; worst = 0; ex = []
for cnt, frs in groups.items():
    for i, fr in enumerate(frs[1:], 1):
        nf += 1
        d = [j for j in range(0x7d00) if fr[j] != frs[0][j] and not (30 <= j // 160 <= 52 and 128 <= j % 160 < 160) and not (14 <= j // 160 <= 66 and 8 <= j % 160 < 52)]   # the talking face (random mouth per frame) and the minimap box (stock draws the step after a commit one frame later) excluded
        if d:
            bad += 1; worst = max(worst, len(d))
            if len(ex) < 6: ex.append((cnt, i, len(d), d[0] // 160, d[-1] // 160, min(j % 160 for j in d), max(j % 160 for j in d)))
print(f"{dump} {kind}: {len(groups)} ticks, {nf} zero-advance extra frames, differing from main: {bad}, worst {worst} bytes; first {ex}")
