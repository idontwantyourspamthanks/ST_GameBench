"""Cold boot (default patched build, STE TOS1.62 1MB), then drive for 330 emulated seconds; sample race state; peek marker/clock."""
import sys, time, re
sys.path.insert(0, 'tools'); sys.path.insert(0, "work/timing")
from msr import Moonshine, GAME, flips_pc
h = Moonshine(machine="ste", memsize_kb=1024, game_dir=GAME / "build/hd")
def mm(a, n):
    return h.debug(f"m ${a:x} {n}", 0.8).strip().splitlines()[-1]
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    print("marker $b2700:", mm(0xb2700, 8), " CLK/NEXT/PEND $b8f00:", mm(0xb8f00, 12))
    h.keypress(57); time.sleep(6); print('after SPACE: $100e', h.peekw(0x100e), '7b74 hits/100vbl', flips_pc(h, 100, pc=0x7b74))
    h.drive(True); v0 = h.vbl(); last = None; log = []
    while h.vbl() < v0 + 16500:
        time.sleep(10)
        try: s = (h.vbl() - v0, h.peekb(0x1021), h.peekw(0x100e), h.peekb(0x1226))
        except Exception as e: s = ("err", str(e)); 
        log.append(s); print(s, flush=True)
    print("marker $b2700:", mm(0xb2700, 8), " CLK/NEXT/PEND:", mm(0xb8f00, 12))
    print("alive, fc advancing:", h.peekw(0x100e)); print("road $d0000:", mm(0xd0000, 8), "WPTR:", mm(0xe7040, 4))
finally:
    h.close()
