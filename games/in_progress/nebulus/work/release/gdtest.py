import sys, time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'tools')
from stharness import Hatari, TOS
from nebulus import Nebulus
from pathlib import Path
class G(Hatari):
    _marker_present = Nebulus._marker_present
    boot_to_title = Nebulus.boot_to_title
    boot_to_game = Nebulus.boot_to_game
    TIMER = Nebulus.TIMER
src = sys.argv[1]
h = G(game_dir=Path(src), workdir='work/release/gd', machine='ste', memsize_kb=1024,
      autorun='C:\\START.TOS', extra=['--trace','gemdos','--trace-file','work/release/gd_trace.txt','--joy1','keys'])
try:
    print('title', h.boot_to_title(timeout=120))
    h.shot('work/release/gd_title.png')
finally:
    h.close()
