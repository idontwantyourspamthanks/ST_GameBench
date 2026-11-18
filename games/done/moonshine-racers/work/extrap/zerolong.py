import sys
from pix3 import *
dump, NP = sys.argv[1], int(sys.argv[2])
for kind in sys.argv[3:]:
    e = Emu(dump); apply_live(e); e.setb(0xB8F21, 0x80|2)
    shots = []
    def hk(uc, addr, size, ud):
        b = struct.unpack('>I', uc.mem_read(0x1008, 4))[0]
        shots.append((e.w(0x100e), bytes(uc.mem_read(b, 0x7d00))))
    h = e.uc.hook_add(UC_HOOK_CODE, hk, begin=0xd1ca, end=0xd1cb)
    for p in range(NP):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        e.setb(0xB8F08,0); e.setl(0xB8F00,36*(p+1))
        try: e.run(0x7a88, 0x7b7a)
        except Exception as ex: print("stop", p, ex); break
        e.run(0x7b7a, 0x7a88)
    groups = {}
    for c, fr in shots: groups.setdefault(c, []).append(fr)
    bad = []; nf = 0
    for c, g in groups.items():
        for i, fr in enumerate(g[1:], 1):
            nf += 1
            d = [j for j in range(0x7d00) if fr[j] != g[0][j] and not (30 <= j//160 <= 52 and 128 <= j%160 < 160) and not (14 <= j//160 <= 66 and 8 <= j%160 < 52) and not (j//160 < 70 and j%160 >= 100) and not (4 <= j//160 < 44 and 56 <= j%160 < 130)]
            if len(d) > 12: bad.append((c, i, len(d), min(j//160 for j in d), max(j//160 for j in d)))
    print(dump, kind, len(groups), "ticks,", nf, "zero-advance extra frames;", len(bad), "with >12 differing bytes (face, minimap box, top-right sky cloud residue and the message text area excluded)", bad[:8])
