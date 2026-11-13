import sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
from mm import start, mem
from populous import HOME, CONQUEST_XY, START_XY
cell, medium, path = sys.argv[1:4]
h = start(cell, medium, path)
try:
    time.sleep(16)
    h.key("space", 0.5)
    time.sleep(80)
    h.shot("/tmp/pt/fl3_a.png"); print("a", flush=True)
    h.key("space", 0.5)
    time.sleep(8)
    h.shot("/tmp/pt/fl3_b.png"); print("b", flush=True)
    h.click(hold=0.3)
    time.sleep(8)
    h.shot("/tmp/pt/fl3_c.png"); print("c", flush=True)
    time.sleep(40)
    h.shot("/tmp/pt/fl3_d.png"); print("d", mem(h,0xB3004,4), flush=True)
finally:
    h.close()
