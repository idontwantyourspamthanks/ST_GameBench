"""Cold boot BUILD to the first race (SPACE x N), then SPACE into the race loop; print marker, road magic/WPTR/PM, $100e and VBL.
python3 cold_int.py BUILD MACHINE MEM TOS"""
import sys, time, struct
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
from stharness import TOS
build, machine, mem, tos = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / build, tos=TOS[tos])
def mm(a, n): return h.debug(f"m ${a:x} {n}", 0.8).strip().splitlines()[-1]
try:
    ok = h.boot_to_race(log=lambda *a: None)
    print(f"{machine} TOS {tos} {mem} KB: boot_to_race {ok} vbl {h.vbl()}")
    h.keypress(57)
    t0 = time.time(); fc = []
    while time.time() - t0 < 120:
        time.sleep(4)
        try: fc.append(h.peekw(0x100e))
        except Exception: pass
        if len(fc) > 3 and fc[-1] > 40: break
    print("  race: $1021", h.peekb(0x1021), "$100e samples", fc[-4:], "vbl", h.vbl())
    print("  marker  ", mm(0xb2700, 8)); print("  CLK/NEXT/PEND", mm(0xb8f00, 12))
    print("  RDG1 $d0000", mm(0xd0000, 8)); print("  WPTR $e7040 ", mm(0xe7040, 4)); print("  $135a", mm(0x135a, 4))
finally:
    h.close()
