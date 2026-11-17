"""HD cold boot; from VBL 5000 press SPACE every 4 s and dump both screen buffers + palette each time (work/credit/fontcap/): to find the game's own text drawn with the message font."""
import sys, time, os
sys.path.insert(0, 'tools')
import msr
from msr import Moonshine, GAME
from stharness import TOS
out = os.path.abspath("work/credit/fontcap"); os.makedirs(out, exist_ok=True)
h = Moonshine(machine="ste", memsize_kb=1024, game_dir=GAME / "build/credit_hd", tos=TOS["1.62"])
try:
    k = 0
    while k < 9:
        time.sleep(3)
        v = h.vbl()
        if v < 5000: continue
        h.debug(f"savebin {out}/{k}_70000.bin $70000 $7d00", 0.7)
        h.debug(f"savebin {out}/{k}_78000.bin $78000 $7d00", 0.7)
        o = h.debug("m $ff8240 32", 0.7); open(f"{out}/{k}.pal", "w").write(o); open(f"{out}/{k}.txt", "w").write(h.debug("m $ff8200 16", 0.7))
        h.shot(f"{out}/{k}.png"); print(k, v, flush=True)
        h.keypress(57); k += 1
finally:
    h.close()
