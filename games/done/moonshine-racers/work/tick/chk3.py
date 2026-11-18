import sys, time
sys.path.insert(0, 'tools'); sys.path.insert(0, 'work/timing')
from msr import Moonshine, GAME
h = Moonshine(machine="ste", memsize_kb=1024, game_dir=GAME / sys.argv[1])
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    h.debug("b all", 0.3)
    f = h.R / "who.txt"; f.write_text("r\nm a7 8\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $d1ca :trace :once :file {f}")
    time.sleep(12)
    print(h._logtext()[n0:][-1500:])
    print("state", h.peekb(0x1021), h.peekw(0x100e), h.peekw(0x5ff8), h.peekw(0x130c))
finally:
    h.close()
