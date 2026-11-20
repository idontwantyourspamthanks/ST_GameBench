"""every frame (main + extras) of a tick must show the same HUD: compare HUD regions of each extra frame with the tick's main frame"""
import sys
from pix3 import *
dump, kind, ntest, NP = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
e = Emu(dump); apply_live(e); e.setb(0xB8F21, ntest)
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
REG = {'score': (14, 48, 72, 104), 'speedo': (148, 176, 248, 320), 'botleft': (170, 200, 0, 40), 'thermo': (50, 66, 24, 72), 'botright': (178, 196, 264, 312), 'minimap': (14, 66, 16, 100), 'face/msg': (0, 50, 100, 320)}
def region(fr, r):
    y0, y1, x0, x1 = r
    out = bytearray()
    for y in range(y0, y1): out += fr[y*160 + x0//2 : y*160 + x1//2]
    return bytes(out)
groups = {}
for cnt, fr in shots: groups.setdefault(cnt, []).append(fr)
tot = {k: 0 for k in REG}; nf = 0
for cnt, frs in groups.items():
    for fr in frs[1:]:
        nf += 1
        for k, r in REG.items():
            if region(fr, r) != region(frs[0], r): tot[k] += 1
print(f"{dump} {kind} ntest={ntest}: {len(groups)} ticks, {nf} extra frames; frames whose region differs from the tick's main frame:", tot)
print("frames per tick:", sorted(set(len(v) for v in groups.values())))
