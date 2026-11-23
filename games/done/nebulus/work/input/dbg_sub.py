import sys, time, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus
h = Nebulus(game=Path('build/both'), workdir='/tmp/strun-nin2gdbg')
try:
    print(h.boot_to_game())
    for c in ('w $3792c $4e $75','w $3398c 0 0 0 0 0 0 0 0','w $3b0aa $60'): h.debug(c,0.2)
    R=h.R
    (R/'subB.txt').write_text('r d0=$00\ne VBL\ne FrameCycles\nm $76d00 2\n')
    (R/'subA.txt').write_text(f'r d0=$80\ne VBL\ne FrameCycles\nb pc = $38514 :once :trace :file {R}/subB.txt\n')
    h.debug('b all',0.3)
    n0=len(h._logtext())
    h.cmd(f'hatari-debug b pc = $38514 :once :trace :file {R}/subA.txt'); time.sleep(0.3)
    h._xdo('keydown','--window',h.win,'Control_R'); time.sleep(0.05); h._xdo('keyup','--window',h.win,'Control_R')
    time.sleep(1.5)
    print(h._logtext()[n0:][:3500])
finally:
    h.close()
