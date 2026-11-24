"""Cold boot Mega STE TOS 2.06 4 MB (native 60 Hz) STOCK game to the race (SPACE until the race setup has run: $d0000 = 'RDG1' or $1021==2 and
$135a set), then save a stock snapshot work/snapshots/megaste4m_60hz_race.sav."""
import sys, time
from mxlib import *
from msr import Moonshine, GAME
from stharness import TOS
h = Moonshine(machine="megaste", memsize_kb=4096, game_dir=GAME / "originals/MOONSHR", tos=TOS["2.06"])
def mm(a, n): return h.debug(f"m ${a:x} {n}", 0.7).strip().splitlines()[-1]
try:
    t0 = time.time(); n = 0
    while time.time() - t0 < 420:
        time.sleep(4); v = h.vbl()
        rd = mm(0xd0000, 4)
        if "52 44 47 31" in rd and h.peekw(0x100e) > 20:
            print("race setup ran at vbl", v, "100e", h.peekw(0x100e), "1021", h.peekb(0x1021)); break
        h.keypress(57); n += 1
        if n % 4 == 0: print(f"t={time.time()-t0:.0f}s vbl={v} 1021={h.peekb(0x1021)} 100e={h.peekw(0x100e)} $d0000={rd}")
    else: raise SystemExit("no race")
    print("ff820a", mm(0xff820a, 2), "135a", mm(0x135a, 4), "d0000", mm(0xd0000, 8))
    h.shot(str(GAME / "work/int/mx/shots/nav60_race.png"))
    h.savemem(str(GAME / "work/snapshots/megaste4m_60hz_race.sav")); time.sleep(2)
    print("saved work/snapshots/megaste4m_60hz_race.sav", "pass", h.peekw(0x100e))
finally:
    h.close()
