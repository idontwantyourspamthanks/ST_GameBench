"""Cold boot a build folder, record title-screen shots through the attract cycle. usage: credit_gate.py BUILD OUTDIR [machine mem tos]"""
import sys, time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus, TOS
from pathlib import Path
b, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
mach = sys.argv[3] if len(sys.argv) > 3 else 'ste'; mem = int(sys.argv[4]) if len(sys.argv) > 4 else 1024; tos = sys.argv[5] if len(sys.argv) > 5 else '1.62'
h = Nebulus(workdir=str(out / 'wd'), machine=mach, tos=TOS[tos], memsize_kb=mem, game=b)
try:
    ok = h.boot_to_title(timeout=300 if mem > 1024 else 120)
    print('title', ok, flush=True)
    for i in range(24):
        time.sleep(1.5)
        h.shot(str(out / f's{i:02d}.png'))
    print('done')
finally:
    h.close()
