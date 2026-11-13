import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
from mm import start, mem
h = start("ste", "gemdos", sys.argv[1], tos="2.06")
try:
    for t in (12,):
        time.sleep(t if t == 6 else 6 if t == 12 else 6 if t == 18 else 8)
        h.shot(f"/tmp/ste60_{t}.png"); print(t, mem(h, 0xb3000, 4), flush=True)
    h.key("space", 0.5); time.sleep(5); h.shot("/tmp/ste60_key.png")
finally:
    h.close()
