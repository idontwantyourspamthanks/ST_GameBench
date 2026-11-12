"""dumps.py : dump 1 MB RAM of each ski snapshot (no patches) to /tmp/p7s/d_<name>.bin"""
import sys, time
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/done/midwinter/tools']
from mw1 import MW1
from pathlib import Path
for n in sys.argv[1:]:
    h = MW1(snapshot=f'../snapshots/1mb_ski_{n}.sav')
    try:
        time.sleep(1)
        h.debug("b all", 0.3)
        h.dump(f'/tmp/p7s/d_{n}.bin', 0, 0x100000)
        time.sleep(1)
    finally:
        h.close()
    print(n, Path(f'/tmp/p7s/d_{n}.bin').stat().st_size)
