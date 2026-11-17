import sys, random
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
from emuhud import *
from unicorn import UC_HOOK_MEM_WRITE
def mk(live):
    e = Emu(DUMPS % 0); apply_live_p(e, live)
    log = []
    def hw(uc, access, addr, size, val, ud):
        if addr in (0xfffffa21, 0xfffffa07, 0xfffffa1b, 0xfffffa13): log.append((addr, val & 0xff))
    e.uc.hook_add(UC_HOOK_MEM_WRITE, hw, begin=0xfffffa00, end=0xfffffa30)
    return e, log
def decode(fa21, e, lst_addr, col_ptr):
    """-> {line: colour15}, palette lines"""
    line = fa21; cur = e.w(0x3cc4); ev = []; i = lst_addr; j = col_ptr; pal = []
    colour_at = {}
    for _ in range(40):
        flag = e.w(i); cnt = e.w(i + 2); i += 4
        if flag in (0, 2): cur = e.w(j); j += 2
        if flag in (1, 2): pal.append(line)
        ev.append((line, cur))
        if cnt == 0: break
        line += cnt
    # colour per line
    c0 = e.w(0x3cc4); out = []
    for ln in range(0, 256):
        c = c0
        for (l, cc) in ev:
            if l <= ln: c = cc
        out.append(c)
    return out, pal, len(ev)
live = sys.argv[1]; liveA = sys.argv[2]; N = int(sys.argv[3])
ea, la = mk(liveA); eb, lb = mk(live)
rnd = random.Random(5)
bad = 0; evA = evB = 0; hits = 0
keys = []
for t in range(N):
    if t % 5 == 0 or not keys:   # new input set; else repeat last (cache hit)
        L0 = rnd.randrange(34, 71); L1 = L0 + rnd.choice([rnd.randrange(9, 70), 29, 24, 25, 28 + 4 * rnd.randrange(0, 6)])
        base = rnd.randrange(0x100, 0x777)
        T = [base] * 9
        for k in range(1, 9):
            T[k] = T[k - 1] if rnd.random() < 0.55 else rnd.randrange(0x100, 0x777)
        keys = (L0, L1, T)
    L0, L1, T = keys
    for e, lg in ((ea, la), (eb, lb)):
        e.setw(0x12fe, L0); e.setw(0x1300, L1)
        for k in range(9): e.setw(0x3cc4 + 2 * k, T[k])
        e.write(0x3d0e, bytes(64))
        e.uc.reg_write(UC_M68K_REG_A0, 0x3d0e)
        # d0/d1/d2 are set by the code itself
        del lg[:]
        try: e.call(0xd57c)
        except Exception as ex:
            print('EXC', ex, 'L0', L0, 'L1', L1, hex(e.uc.reg_read(UC_M68K_REG_PC)), 'live', e is eb); raise SystemExit
    fa_a = [v for a, v in la if a == 0xfffffa21][-1]; fa_b = [v for a, v in lb if a == 0xfffffa21][-1]
    ca, pa, na = decode(fa_a, ea, 0x3d0e, ea.l(0x3cbc) - 0 if False else 0x3cc6)
    cb, pb, nb = decode(fa_b, eb, 0x3d0e, eb.l(0x3cbc))
    evA += na; evB += nb
    if ca != cb or pa != pb:
        bad += 1
        if bad < 4: print('DIFF L0', L0, 'L1', L1, 'T', [hex(x) for x in T], 'stock', pa, na, 'new', pb, nb)
print('cases', N, 'bad', bad, 'interrupts stock', evA, 'new', evB)
