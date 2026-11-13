import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
from mm import start, mem
h = start(sys.argv[2] if len(sys.argv) > 2 else "ste", "gemdos", sys.argv[1], tos=sys.argv[3] if len(sys.argv) > 3 else "2.06", extra=["--trace", "gemdos"], mem=int(sys.argv[4]) if len(sys.argv) > 4 else None)
try:
    time.sleep(8)
    for l in h._logtext().splitlines():
        if "Pexec" in l or "Mshrink" in l or "Malloc" in l: print(l[:160])
finally:
    h.close()
