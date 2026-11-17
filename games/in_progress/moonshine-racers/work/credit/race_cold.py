"""Cold boot a HD build to the first race and report (marker, race counter). CPU=16: the clock is raised after TOS init (VBL>200) like tools/play.sh.
   python3 race_cold.py BUILD MACHINE MEM TOS"""
import sys, time, os
sys.path.insert(0, 'tools')
import msr
from msr import Moonshine, GAME
from stharness import TOS
build, machine, mem, tos = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / build, tos=TOS[tos])
try:
    if os.environ.get("CPU"):
        f = h.R / "clk.txt"; f.write_text(f"setopt --cpuclock {os.environ['CPU']}\n")
        h.cmd(f"hatari-debug b VBL > 200 :trace :once :file {f}")
    ok = h.boot_to_race(log=lambda *a: None)
    print(f"{machine} {mem} KB TOS {tos} cpu {os.environ.get('CPU', '8')}: boot_to_race {ok} vbl {h.vbl()}", flush=True)
    h.keypress(57)
    t0 = time.time(); fc = []
    while time.time() - t0 < 120:
        time.sleep(4)
        try: fc.append(h.peekw(0x100e))
        except Exception: pass
        if len(fc) > 3 and fc[-1] > 40: break
    print("  race: $1021", h.peekb(0x1021), "$100e samples", fc[-4:], "vbl", h.vbl())
    print("  marker", h.debug("m $b2700 8", 0.8).strip().splitlines()[-1])
    h.shot(f"work/credit/race_{machine}_{mem}_{os.environ.get('CPU','8')}.png")
finally:
    h.close()
