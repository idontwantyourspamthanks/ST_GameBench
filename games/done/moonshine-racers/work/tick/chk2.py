import sys, time
sys.path.insert(0, 'tools'); sys.path.insert(0, 'work/timing')
from msr import Moonshine, GAME, flips_pc
h = Moonshine(machine="ste", memsize_kb=1024, game_dir=GAME / sys.argv[1])
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    for pc in (0xd1ca, 0xd1e4, 0x7b74, 0xb8100, 0xb8200, 0xb8000):
        print(hex(pc), flips_pc(h, 100, pc=pc), flush=True)
    print("b8f00", h.debug("m $b8f00 12", 0.8).strip().splitlines()[-1])
finally:
    h.close()
