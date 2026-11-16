import sys, time
sys.path.insert(0, 'tools'); sys.path.insert(0, 'work/timing')
from msr import Moonshine, GAME, flips_pc
h = Moonshine(machine="ste", memsize_kb=1024, game_dir=GAME / sys.argv[1])
try:
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    h.savemem("/tmp/msrtick_posscreen.sav")
    for k in range(6):
        h.keypress(57); time.sleep(6)
        print("after space", k, h.peekb(0x1021), h.peekw(0x100e), "pos", h.peekw(0x5ff8), "1024", h.peekb(0x1024), flush=True)
    print("7b74 hits", flips_pc(h, 100, pc=0x7b74))
finally:
    h.close()
