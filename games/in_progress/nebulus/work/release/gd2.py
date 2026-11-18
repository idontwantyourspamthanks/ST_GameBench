"""Release folder on a plain Hatari GEMDOS drive (no HDDRIVER): tower + NEPO."""
import sys, time, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'tools')
from stharness import Hatari
from nebulus import Nebulus
from pathlib import Path
class G(Hatari):
    _marker_present = Nebulus._marker_present; boot_to_title = Nebulus.boot_to_title; boot_to_game = Nebulus.boot_to_game; TIMER = Nebulus.TIMER
h = G(game_dir=Path(sys.argv[1]).resolve(), workdir='work/release/gd2wd', machine='ste', memsize_kb=1024, autorun='C:\\START.TOS', extra=['--joy1','keys'])
try:
    print('tower', h.boot_to_game())
    o = h.debug('m $b0020 4', 0.6); print(o.strip().splitlines()[-1][:60])
    o = h.debug('m $b0024 2', 0.6); print(o.strip().splitlines()[-1][:60])
finally: h.close()
