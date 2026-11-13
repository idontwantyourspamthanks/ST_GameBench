import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
from mm import start, mem
h = start("falcon", "floppy", sys.argv[1])
try:
    time.sleep(10)
    print("vec", mem(h, 0xb4, 8), mem(h,0x84,4), "savptr", mem(h, 0x4a2, 4))
finally:
    h.close()
