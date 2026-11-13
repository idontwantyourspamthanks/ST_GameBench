import sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
from mm import start, mem
cell, medium, path = sys.argv[1:4]
h = start(cell, medium, path)
try:
    for i in range(int(sys.argv[4]) if len(sys.argv)>4 else 8):
        time.sleep(30)
        p = h.shot(f"/tmp/pt/fl_{cell}_{i}.png")
        print(i*30+30, p, mem(h,0xB3004,4), flush=True)
finally:
    h.close()
