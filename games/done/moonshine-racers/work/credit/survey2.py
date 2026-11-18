"""Cold boot BUILD, SPACE every 4 s once VBL>5000, screenshot every 2 s. python3 survey2.py BUILD OUTDIR"""
import sys, time, os
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
from stharness import TOS
build, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
h = Moonshine(machine='ste', memsize_kb=1024, game_dir=GAME / build, tos=TOS['1.62'])
try:
    n = 0
    while n < 70:
        time.sleep(2)
        v = h.vbl()
        if v > 5000 and n % 3 == 0: h.keypress(57)
        h.shot(f"{out}/{n:03d}_vbl{v}.png"); print(n, v, flush=True); n += 1
finally:
    h.close()
