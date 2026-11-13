import sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
from mm import start, mem
cell, medium, path = sys.argv[1:4]
h = start(cell, medium, path)
try:
    time.sleep(16)
    h.key("space", 0.5)
    for i in range(10):
        time.sleep(10)
        p = h.shot(f"/tmp/pt/fl2_{cell}_{i}.png")
        print((i+1)*10+16, p, mem(h,0xB3004,4), flush=True)
finally:
    h.close()
