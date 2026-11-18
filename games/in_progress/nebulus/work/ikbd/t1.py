"""Timeline of a cold boot: VBL at key hand-over points, ACIA status there. No input."""
import sys, time, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus')
variant = sys.argv[1]
h = Nebulus(game=G/'work/ikbd/build'/variant, workdir=f'/tmp/strun-ikbd-t1-{variant}')
try:
    f = Path(h.R)/'ev.txt'
    f.write_text('e VBL\nm $fffc00 2\nm $fa11 2\nm $fa13 4\nm $fa07 4\nr\n')
    h.cmd(f'hatari-debug b ($118).l ! ($118).l :trace :file {f}')
    h.cmd(f'hatari-debug b pc = $1b172 :trace :file {f}')   # START S+$35c (SR=$2700)
    h.cmd(f'hatari-debug b pc = $38486 :trace :file {f}')   # game: move.w #$2300,sr
    h.cmd(f'hatari-debug b pc = $38624 :trace :file {f}')   # game entry
    t0=time.time()
    while time.time()-t0 < 60:
        time.sleep(2)
        if h._marker_present(): break
    time.sleep(3)
    log = h._logtext()
    Path(f'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd/t1_{variant}.log').write_text(log)
    print(log[-6000:])
finally:
    h.close()
