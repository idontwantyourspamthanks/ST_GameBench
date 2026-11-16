"""TT (68030, caches) cold boot of build/render_default, SPACE, hold Up ~1500 VBL; the game must run and mr_edge's generated slots must exist.
python3 work/render/tt_drive.py [machine mem tos]"""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
from msr import Moonshine, GAME
from stharness import TOS
mach, mem, tos = (sys.argv[1:4] + ["tt", "4096", "3.06"][len(sys.argv) - 1:])[:3] if len(sys.argv) > 3 else ("tt", "4096", "3.06")
h = Moonshine(machine=mach, memsize_kb=int(mem), game_dir=GAME / "build/render_default", tos=TOS[tos])
def mm(a, n): return h.debug(f"m ${a:x} {n}", 0.8).strip().splitlines()[-1]
try:
    print(mach, mem, tos, "in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    print("marker $b2700:", mm(0xb2700, 8))
    h.keypress(57); time.sleep(6); h.drive(True); v0 = h.vbl()
    while h.vbl() < v0 + 1500:
        time.sleep(6)
        try: print((h.vbl() - v0, h.peekb(0x1021), h.peekw(0x100e), h.peekw(0x5ff8)), flush=True)
        except Exception as e: print("err", e)
    print("slots $b3186:", mm(0xb3186, 16), "lastptr area $b3340:", mm(0xb3340, 8))
    print("table $102ba:", mm(0x102ba, 16))
finally:
    h.close()
