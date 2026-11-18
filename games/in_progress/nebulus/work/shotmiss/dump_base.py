"""Dump 1 MB RAM of a snapshot at the loop-top poll ($3dcf4) -> /tmp or work/shotmiss/base_*.bin"""
import sys, time
from pathlib import Path
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
snap, out = sys.argv[1], sys.argv[2]
wd = '/tmp/sr-dump'
cmdf = Path(wd)/'dump.txt'
Path(wd).mkdir(exist_ok=True)
cmdf.write_text(f'savebin {out} 0 $100000\nm $33900 80\nm $3ad98 6\n')
h = Nebulus(snapshot=snap, workdir=wd)
try:
    time.sleep(1.0)
    h.debug('b all', 0.2)
    h.cmd(f'hatari-debug b pc = $3dcf4 :once :trace :file {cmdf}'); time.sleep(0.5)
    t0=time.time()
    while time.time()-t0 < 20 and not Path(out).exists(): time.sleep(0.3)
    time.sleep(1.0)
    print(h._logtext()[-1500:])
finally:
    h.close()
