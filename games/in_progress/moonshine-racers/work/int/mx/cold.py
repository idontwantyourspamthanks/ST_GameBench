"""Cold boot of an HD build to the race, then rate windows at the machine's own clock and with set_cpuclock 16 / 32: passes, extra frames, skip reasons, marker.
python3 cold.py MACHINE MEM TOS GAMEDIR [VBLS=500] [hz=native|force60] [clocks=0,16,32]   (0 = leave the clock as booted)"""
import sys, time, re
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from mxlib import *
from msr import Moonshine, GAME
from stharness import TOS
machine, mem, tos, game = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
vbls = int(sys.argv[5]) if len(sys.argv) > 5 else 500
force60 = len(sys.argv) > 6 and sys.argv[6] == "force60"
clocks = [int(x) for x in (sys.argv[7] if len(sys.argv) > 7 else "0,16,32").split(",")]
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / game, tos=TOS[tos])
def rd(addr, n):
    out = h.debug(f"m ${addr:x} {n}", 0.7); g = {}
    for ln in out.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    return bytes(g[addr + i] for i in range(n))
w = lambda d, o: (d[o] << 8) | d[o + 1]
def sample():
    v = h.vbl(); b = rd(0xb8f38, 12); r = rd(0xb8f54, 18)
    return dict(vbl=v, frames=(w(b, 0) << 16) | w(b, 2), groups=(w(b, 4) << 16) | w(b, 6), pass_=h.peekw(0x100e), pos=h.peekw(0x5ff8), spd=h.peekw(0x130c), rsn=[w(r, 2 * i) for i in range(9)])
try:
    ok = h.boot_to_race(log=lambda *a: None)
    print(f"{machine} {mem} KB TOS {tos} build {game}: boot_to_race {ok} vbl {h.vbl()}", flush=True)
    print("marker $b2700:", rd(0xb2700, 4), "sites:", rd(0xd128, 6).hex(), rd(0x7b0a, 6).hex(), rd(0x7b46, 6).hex(), rd(0x7b74, 6).hex(), "$ff820a:", rd(0xff820a, 2).hex(), flush=True)
    if force60: h.debug("w $ff820a $fc")
    h.keypress(57); time.sleep(8)
    for k in range(6):
        if h.peekb(0x1021) == 2 and h.peekw(0x100e) > 20: break
        h.keypress(57); time.sleep(5)
    print("race loop: $1021", h.peekb(0x1021), "$100e", h.peekw(0x100e), "$ff820a", rd(0xff820a, 2).hex(), flush=True)
    h.drive(True)
    time.sleep(25)
    for mhz in clocks:
        if mhz: h.set_cpuclock(mhz); time.sleep(2)
        a = sample(); time.sleep(vbls / 50 * 1.3); b = sample()
        dv = b['vbl'] - a['vbl']; dp = (b['pass_'] - a['pass_']) & 0xffff; de = b['frames'] - a['frames']
        print(f"RESULT {machine} {mem} TOS {tos} clock {mhz or 'native'}: window {dv} VBL, passes {dp} ({dp*50/dv:.3f}/s @50Hz), extra frames {de}, displayed fps {(dp+de)*50/dv:.3f}, pos {a['pos']}->{b['pos']}, skip reasons {[(y-x)&0xffff for x,y in zip(a['rsn'], b['rsn'])]}", flush=True)
    h.shot(str(GAME / f"work/int/mx/shots/cold_{machine}_{mem}_{tos}.png"))
finally:
    h.close()
