import sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
from mm import start, mem
cell, medium, path, wait, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
h = start(cell, medium, path)
try:
    for i in range(n):
        time.sleep(wait if i == 0 else 15)
        if i == 0: h.key("space", 0.5)
        h.shot(f"/tmp/pt/lk_{cell}_{i:02d}.png"); print(i, mem(h,0xB3004,4), flush=True)
finally:
    h.close()
