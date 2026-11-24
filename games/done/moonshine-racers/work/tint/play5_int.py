"""5-minute play of the default HD build: cold boot, SPACE, up held, race start/time-out/restart; samples + extra-frame counters.
python3 play5.py MACHINE MEM TOS GAMEDIR MHZ [VBLS=16700]"""
import sys, time, re
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
from mxlib import *
from msr import Moonshine, GAME, flips_pc
from stharness import TOS
machine, mem, tos, game, mhz = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
N = int(sys.argv[6]) if len(sys.argv) > 6 else 16700
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / game, tos=TOS[tos])
def mm(a, n): return h.debug(f"m ${a:x} {n}", 0.8).strip().splitlines()[-1]
def ctr():
    out = h.debug("m $b8f38 12", 0.8); g = {}
    for ln in out.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    l = lambda o: int.from_bytes(bytes(g[0xb8f38 + o + i] for i in range(4)), "big")
    return l(0), l(4), l(8)
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl(), flush=True)
    print("marker $b2700:", mm(0xb2700, 8)); print("CLK/NEXT/PEND $b8f00:", mm(0xb8f00, 12), flush=True)
    if mhz != 8: h.set_cpuclock(mhz)
    h.keypress(57); time.sleep(6); print('after SPACE: $100e', h.peekw(0x100e))
    h.drive(True); v0 = h.vbl(); c0 = ctr(); t0 = time.time(); shots = 0; ZIG = [0x01, 0x05, 0x01, 0x09]; k = 0; last = 0; prev_pass = h.peekw(0x100e); restarts = 0; pend_shot = None
    while h.vbl() < v0 + N:
        time.sleep(1.5); k += 1
        h.debug(f"w $6105 ${ZIG[(k // 4) % 4]:02x}", 0.1)
        try: p = h.peekw(0x100e)
        except Exception: continue
        if p + 50 < prev_pass:
            restarts += 1; pend_shot = time.time() + 6; print(f"RESTART seen: pass {prev_pass} -> {p} at VBL {h.vbl() - v0}", flush=True)
        prev_pass = p
        if pend_shot and time.time() > pend_shot:
            h.shot(str(GAME / f"work/tint/shots/play5_{machine}_{mem}_{mhz}_after_restart{restarts}.png")); pend_shot = None; print("shot after restart taken", flush=True)
        if time.time() - last > 10:
            last = time.time()
            try: s_ = (h.vbl() - v0, h.peekb(0x1021), h.peekw(0x100e), h.peekb(0x1226), ctr(), h.peekw(0xbf008))
            except Exception as e: s_ = ("err", str(e))
            print(s_, "(vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)", flush=True)
        if time.time() - t0 > 150 and shots == 0:
            h.shot(str(GAME / f"work/tint/shots/play5_{machine}_{mem}_{mhz}_mid.png")); shots = 1
    c1 = ctr()
    print("extras (frames, groups, ticks) at start", c0, "at end", c1, "-> extra frames", c1[0] - c0[0], "in", h.vbl() - v0, "VBL")
    print("marker $b2700:", mm(0xb2700, 8), " CLK/NEXT/PEND:", mm(0xb8f00, 12))
    print("alive, fc advancing:", h.peekw(0x100e)); print("road $c0000:", mm(0xc0000, 8), "WPTR:", mm(0xd7040, 4), "restarts", restarts, "tb_car INIT/NENT/POOLP", mm(0xbf000, 12))
finally:
    h.close()
