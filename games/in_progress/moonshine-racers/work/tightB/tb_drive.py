"""Cold boot a built folder, SPACE into the race, hold Up for ~2 minutes (6100 VBL); report state + tb_* variables.
python3 tb_drive.py GAMEDIR(relative to the game root) MACHINE MEM_KB [TOS] [vbls]"""
import sys, time
from pathlib import Path
GAME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(GAME / "tools")); sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from msr import Moonshine, flips_pc
from stharness import TOS
game, machine, mem = sys.argv[1], sys.argv[2], int(sys.argv[3]); tos = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
vbls = int(sys.argv[5]) if len(sys.argv) > 5 else 6100
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / game, **({"tos": TOS[tos]} if tos else {}))
def mm(a, n): return h.debug(f"m ${a:x} {n}", 0.8).strip().splitlines()[-1]
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl(), flush=True)
    print("marker $b2700:", mm(0xb2700, 8))
    h.keypress(57); time.sleep(6); print('after SPACE: $100e', h.peekw(0x100e), flush=True)
    h.drive(True); v0 = h.vbl(); log = []
    while h.vbl() < v0 + vbls:
        time.sleep(10)
        try: s = (h.vbl() - v0, h.peekb(0x1021), h.peekw(0x100e), h.peekb(0xBF000), h.peekw(0xBF008), h.peekb(0xB5800), h.peekw(0x5ff8))
        except Exception as e: s = ("err", str(e))
        log.append(s); print(s, "  (vbl, mode, pass, INIT, NENT, BST, pos)", flush=True)
    print("tb_car: INIT/LASTP/POOLP/NENT:", mm(0xBF000, 16)); print("tb_blit BST:", mm(0xB5800, 8))
    print("alive, pass counter:", h.peekw(0x100e))
finally:
    h.close()
