#!/usr/bin/env python3
"""tt_enter.py X Y NAME : from work/snapshots/fire_tt14fix_map.sav (TT 4 MB, TOS 3.06, --mmu true, v1.4 code in RAM) enter an island; save snap/tt_NAME.sav"""
import sys, time
from cs import *
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
import mw2raids
from stharness import MACHINE_TOS
x, y, name = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
h = Hatari(snapshot=str(SNAP / 'fire_tt14fix_map.sav'), machine='tt', tos=MACHINE_TOS['tt'], memsize_kb=4096, game_dir=GAME / 'build/game', extra=['--mmu', 'true', '--joy1', 'none'])
try:
    time.sleep(4)
    r = mw2raids.enter_raid(h, x, y)
    print('entered', r, flush=True)
    time.sleep(5)
    print('MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    h.savemem(str(HERE / 'snap' / f'tt_{name}.sav'))
    h.shot(str(HERE / 'snap' / f'tt_{name}.png'))
    print('saved', name, flush=True)
finally:
    h.close()
