"""Cold boot a built game folder (STE TOS 1.62 1 MB), SPACE into the race, hold Up for ~2 minutes (3600 VBL), sample race state; peek the marker.
python3 work/render/drive2min.py build/render_default"""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from msr import Moonshine, GAME, flips_pc
h = Moonshine(machine="ste", memsize_kb=1024, game_dir=GAME / sys.argv[1])
def mm(a, n):
    return h.debug(f"m ${a:x} {n}", 0.8).strip().splitlines()[-1]
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    print("marker $b2700:", mm(0xb2700, 8))
    h.keypress(57); time.sleep(6); print('after SPACE: $100e', h.peekw(0x100e), '7b74 hits/100vbl', flips_pc(h, 100, pc=0x7b74))
    h.drive(True); v0 = h.vbl(); log = []
    while h.vbl() < v0 + 3600:
        time.sleep(8)
        try: s = (h.vbl() - v0, h.peekb(0x1021), h.peekw(0x100e), h.peekb(0x1226), h.peekw(0x5ff8))
        except Exception as e: s = ("err", str(e))
        log.append(s); print(s, flush=True)
    print("marker $b2700:", mm(0xb2700, 8))
    print("alive, fc advancing:", h.peekw(0x100e))
    print("RDG magic $d0000:", mm(0xd0000, 8), "PM $d0004:", mm(0xd0004, 4), "WPTR $e7040:", mm(0xe7040, 4), "T2 $d0100:", mm(0xd0100, 8))
finally:
    h.close()
