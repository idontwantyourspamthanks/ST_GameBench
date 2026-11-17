"""Survey: cold boot BUILD, screenshot every ~3 s (no keys) until VBL LIMIT. python3 survey.py BUILD OUTDIR [LIMIT] [machine mem tos]"""
import sys, time
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
from stharness import TOS
build, out = sys.argv[1], sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
machine, mem, tos = (sys.argv[4], int(sys.argv[5]), sys.argv[6]) if len(sys.argv) > 6 else ('ste', 1024, '1.62')
import os; os.makedirs(out, exist_ok=True)
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / build, tos=TOS[tos])
try:
    n = 0
    while True:
        time.sleep(float(os.environ.get("DT","2.5")))
        v = h.vbl()
        h.shot(f"{out}/{n:03d}_vbl{v}.png"); print(n, v, flush=True)
        n += 1
        if v > limit: break
finally:
    h.close()
