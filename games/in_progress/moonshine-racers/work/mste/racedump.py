"""Stock (or given) game on machine/mem/TOS to the race, then dump all RAM. python3 racedump.py MACHINE MEM TOS OUT.bin [GAMEDIR]"""
import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/tools'); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from msr import Moonshine, GAME
from stharness import TOS
m, mem, tos, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
game = GAME / sys.argv[5] if len(sys.argv) > 5 else None
h = Moonshine(machine=m, memsize_kb=mem, tos=TOS[tos], game_dir=game)
try:
    ok = h.boot_to_race(log=lambda *a: None)
    print("in_race", ok, "vbl", h.vbl())
    if ok:
        time.sleep(2); h.dump(out, 0, mem * 1024); time.sleep(3); print("dumped", out)
finally:
    h.close()
