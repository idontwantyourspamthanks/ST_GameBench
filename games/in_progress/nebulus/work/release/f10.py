import sys, time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'tools')
from nebulus import Nebulus
from pathlib import Path
h = Nebulus(workdir='work/release/f10wd', game=Path(sys.argv[1]).resolve())
try:
    print(h.boot_to_title(timeout=100)); time.sleep(2)
    h.key('F10', hold=0.5); time.sleep(2.5); h.shot('work/release/f10_a.png')
    print(h.debug('m $38498 2',0.5)[-80:], h.debug('m $75740 4',0.5)[-60:])
finally: h.close()
