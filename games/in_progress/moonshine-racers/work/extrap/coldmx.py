"""Cold boot of a build, then a real race: counters of the extra-frame blob. python3 coldmx.py MACHINE MEM TOS GAMEDIR [VBLS]
Reports: marker, patched sites, pass rate / frame rate over a window (passes from $100e, frames from the blob counters), CLK, skip reasons."""
import sys, time, re
sys.path.insert(0, '../../tools'); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from msr import Moonshine, GAME
from stharness import TOS
machine, mem, tos, game = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
vbls = int(sys.argv[5]) if len(sys.argv) > 5 else 900
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / game, tos=TOS[tos])
def rd(addr, n):
    out = h.debug(f"m ${addr:x} {n}", 0.7)
    g = {}
    for ln in out.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    return bytes(g[addr + i] for i in range(n))
try:
    ok = h.boot_to_race(log=lambda *a: None)
    print("in_race(position screen)", ok, "vbl", h.vbl(), flush=True)
    print("marker $b2700:", rd(0xb2700, 4), "sites:", rd(0xd128, 6).hex(), rd(0x7b0a, 6).hex(), rd(0x7b46, 6).hex(), rd(0x7b74, 6).hex(), flush=True)
    h.keypress(57); time.sleep(8)
    for k in range(6):
        if h.peekb(0x1021) == 2 and h.peekw(0x100e) > 20: break
        h.keypress(57); time.sleep(5)
    print("race loop: $1021", h.peekb(0x1021), "$100e", h.peekw(0x100e), flush=True)
    h.drive(True)
    # wait for the lights (race start) then sample
    time.sleep(25)
    def sample():
        v = h.vbl(); b = rd(0xb8f38, 12); r = rd(0xb8f54, 18); pc = h.peekw(0x100e); pos = h.peekw(0x5ff8); sp = h.peekw(0x130c)
        w = lambda d, o: (d[o] << 8) | d[o+1]
        return dict(vbl=v, frames=(w(b,0)<<16)|w(b,2), groups=(w(b,4)<<16)|w(b,6), ticks=(w(b,8)<<16)|w(b,10), pass_=pc, pos=pos, spd=sp, rsn=[w(r,2*i) for i in range(9)])
    a = sample(); print("A", a, flush=True)
    time.sleep(vbls / 50 * 1.1)
    b = sample(); print("B", b, flush=True)
    dv = b['vbl'] - a['vbl']; dp = (b['pass_'] - a['pass_']) & 0xffff; de = b['frames'] - a['frames']
    print(f"RESULT {machine} {mem} TOS {tos}: window {dv} VBL, passes {dp} ({dp*50/dv:.3f}/s), extra frames {de}, displayed fps {(dp+de)*50/dv:.3f}, pos/s {(b['pos']-a['pos'])*50/dv:.1f}, skip reasons delta {[ (y-x)&0xffff for x,y in zip(a['rsn'], b['rsn'])]}")
    h.shot(str(GAME / f"work/extrap/ab/cold_{machine}_{mem}_{tos}.png"))
finally:
    h.close()
