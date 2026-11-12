import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
snap, out = sys.argv[1:3]
h = Hatari(snapshot=str(ROOT/'work/snapshots'/snap), memsize_kb=2048)
try:
    time.sleep(4); h.shot(out)
    print(hex(h.peekw(0x700a)), hex(h.peekw(0x6fae)), hex(h.peekw(0x6fb2)), hex(h.peekw(0xeb9c)))
finally: h.close()
