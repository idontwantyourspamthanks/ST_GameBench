#!/usr/bin/env python3
"""From work/snapshots/fire_<TAG>_map.sav enter an island and snapshot the 3D view.  usage: from_map.py TAG BUILD MACHINE MEM X Y NAME"""
import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
import mw2raids
from stharness import MACHINE_TOS
tag, bd, machine, mem, x, y, name = sys.argv[1:8]
tt = machine == 'tt'
h = Hatari(snapshot=str(ROOT/'work/snapshots'/f'fire_{tag}_map.sav'), machine=machine, tos=MACHINE_TOS[machine], memsize_kb=int(mem), game_dir=ROOT/bd, extra=['--mmu','true','--joy1','none'] if tt else ['--joy1','none'])
try:
    time.sleep(4)
    r = mw2raids.enter_raid(h, int(x), int(y))
    print('entered', r, flush=True)
    time.sleep(5)
    h.savemem(str(ROOT/'work/snapshots'/f'fire_{tag}_{name}.sav'))
    print('saved', name, flush=True)
finally:
    h.close()
