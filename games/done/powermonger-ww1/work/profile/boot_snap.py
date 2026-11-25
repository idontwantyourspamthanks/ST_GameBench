import sys, time, shutil
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1")
sys.path.insert(0, str(G/"tools"))
import pmww
from pmww import PMW
W = Path("/tmp/pmww1prof/boot"); shutil.rmtree(W, ignore_errors=True)
h = PMW(workdir=str(W), memsize_kb=1024)
try:
    h.boot_to_map(noprot=False)
    print("iter", hex(h.counter()), flush=True)
    time.sleep(2)
    h.shot("/tmp/pmww1prof/map_idle.png")
    h.savemem("/tmp/pmww1prof/map_idle.sav")
    print("saved", flush=True)
finally:
    h.close()
