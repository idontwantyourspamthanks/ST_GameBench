import sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
from mm import start, mem
cell, medium, path = sys.argv[1:4]
h = start(cell, medium, path)
try:
    time.sleep(16); h.key("space", 0.5)
    time.sleep(80); h.key("space", 0.5)
    for i in range(14):
        time.sleep(15)
        h.shot(f"/tmp/pt/fl4_{i:02d}.png"); print(i, 95+(i+1)*15, flush=True)
finally:
    h.close()
