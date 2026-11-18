import sys, random
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
from emuhud import *
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ
live = sys.argv[1]; N = int(sys.argv[2]); liveA = sys.argv[3]; POKE = sys.argv[4] if len(sys.argv) > 4 else None
def mk(patched, L):
    e = Emu(DUMPS % L)
    apply_live_p(e, live if patched else liveA)
    if patched and POKE: e.write(int(POKE.split('=')[0], 16), bytes.fromhex(POKE.split('=')[1]))
    e.setb(0x1020, 1)
    chip = {'sel': 0, 'regs': [0xaa] * 16, 'log': []}
    def hw(uc, access, addr, size, val, ud):
        if addr == 0xff8800: chip['sel'] = val & 0xff
        elif addr == 0xff8802:
            chip['regs'][chip['sel'] & 15] = val & 0xff; chip['log'].append((chip['sel'], val & 0xff))
    def hr(uc, access, addr, size, val, ud):
        if addr == 0xff8800: uc.mem_write(0xff8800, bytes([chip['regs'][chip['sel'] & 15]]))
    e.uc.hook_add(UC_HOOK_MEM_WRITE, hw, begin=0xff8800, end=0xff8803)
    e.uc.hook_add(UC_HOOK_MEM_READ, hr, begin=0xff8800, end=0xff8803)
    return e, chip
tot = 0; bad = 0; nw0 = nw1 = 0
for L in (0, 5, 12, 14):
    ea, ca = mk(False, L); eb, cb = mk(True, L)
    rnd = random.Random(L)
    for i in range(N):
        if i % 17 == 3:   # sound triggers, same on both
            sid = rnd.randrange(0, 60); ch = rnd.choice([0, 1, 2])
            for e in (ea, eb):
                e.uc.reg_write(UC_M68K_REG_D0, sid); e.uc.reg_write(UC_M68K_REG_D1, ch)
                try: e.call(0x7bb2)
                except Exception: pass
        if i % 29 == 5:   # perturb tuning word and mixer high bits in chips (R7 I/O bits changed by someone else is NOT modelled as supported)
            pass
        for e, c in ((ea, ca), (eb, cb)): c['log'].clear(); e.call(0x8bf2)
        tot += 1; nw0 += len(ca['log']); nw1 += len(cb['log'])
        if ca['regs'][:14] != cb['regs'][:14]: bad += 1; print('CHIP DIFF level', L, 'call', i, ca['regs'], cb['regs'])
        ra = ea.read(0x8000, 0x1a000); rb = eb.read(0x8000, 0x1a000)
        diff = [j for j in range(len(ra)) if ra[j] != rb[j] and not (0x8e2c <= 0x8000 + j < 0x8e36)]
        if diff: bad += 1; print('RAM DIFF', [hex(0x8000 + j) for j in diff[:8]])
print('calls', tot, 'bad', bad, 'chip writes stock', nw0, 'patched', nw1)
