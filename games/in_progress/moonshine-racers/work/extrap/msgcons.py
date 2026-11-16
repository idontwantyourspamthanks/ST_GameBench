"""message text region of every extra frame must equal the same region of the tick's main frame or of the next tick's main frame"""
import sys
from pix3 import *
dump, NP, kind, ntest = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
e = Emu(dump); apply_live(e); e.setb(0xB8F21, ntest)
shots = []; mains = {}
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
for c, fr in shots: groups.setdefault(c, []).append(fr)
def reg(fr): 
    out = bytearray()
    for y in range(4, 44):
        row = fr[y*160+56: y*160+130]
        out += bytes(b for i, b in enumerate(row) if (56 + i) % 8 >= 2)    # planes 1-3 only (the clouds live in plane 0)
    return bytes(out)
keys = sorted(groups)
bad = []; ne = 0; changed_ticks = 0; nonmono = []; pats = {}
for i, c in enumerate(keys[:-1]):
    g = groups[c]; nxt = groups[keys[i+1]][0]
    if reg(g[0]) != reg(nxt): changed_ticks += 1
    pat = ''
    for j, fr in enumerate(g[1:], 1):
        ne += 1
        if reg(fr) != reg(g[0]) and reg(fr) != reg(nxt): bad.append((c, j))
        pat += 'N' if reg(fr) == reg(g[0]) else 'A'
    if reg(g[0]) != reg(nxt):
        pats[pat] = pats.get(pat, 0) + 1
        if 'AN' in pat: nonmono.append((c, pat))
print('patterns of extra frames in ticks where the message changes (N = still shows this tick, A = already shows the next):', pats, 'non-monotone ticks:', len(nonmono), nonmono[:5])
print(f"{dump} {kind} ntest={ntest}: {len(keys)} ticks, {ne} extra frames, ticks where the message region changes {changed_ticks}; extra frames whose message region matches neither neighbour main frame: {len(bad)} {bad[:8]}")
