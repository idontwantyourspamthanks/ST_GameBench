import sys,time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy')
from nebfloppy import NebFloppy
from pathlib import Path
out=Path(sys.argv[2]).resolve(); out.mkdir(parents=True,exist_ok=True)
h=NebFloppy(Path(sys.argv[1]).resolve(),machine='ste',mem=1024,tos='1.62',workdir=str(out/'wd'),trace='fdc')
try:
    print('title',bool(h.boot_to_title(timeout=400,space_at=20)))
    for i in range(16): time.sleep(1.5); h.shot(str(out/f's{i:02d}.png'))
finally: h.close()
