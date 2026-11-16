import sys, time
sys.path.insert(0, 'tools'); sys.path.insert(0, 'work/timing')
from msr import Moonshine, GAME
h = Moonshine(machine="ste", memsize_kb=1024, game_dir=GAME / sys.argv[1])
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    for a in ("b2700 8", "d128 6", "7b74 6", "7b0a 6", "b8f00 12"):
        print(a, "|", h.debug(f"m ${a.split()[0]} {a.split()[1]}", 0.8).strip().splitlines()[-1])
    time.sleep(2); print("clk again", h.debug("m $b8f00 12", 0.8).strip().splitlines()[-1])
    v0, f0 = h.vbl(), h.peekw(0x100e); time.sleep(20); print("passes", h.peekw(0x100e)-f0, "vbl", h.vbl()-v0)
finally:
    h.close()
