#!/usr/bin/env python3
"""Cold boot of a build to the Raids map, snapshot it, enter Zafriya (on foot), snapshot.
usage: cold_fire.py TAG BUILD MACHINE MEM  -> work/snapshots/fire_<TAG>_map.sav, fire_<TAG>_foot.sav"""
import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
import mw2raids
from stharness import MACHINE_TOS
tag, bd, machine, mem = sys.argv[1:5]
tt = machine == 'tt'
h = Hatari(snapshot=None, machine=machine, tos=MACHINE_TOS[machine], memsize_kb=int(mem), game_dir=ROOT/bd, extra=['--mmu','true','--joy1','none'] if tt else ['--joy1','none'])
try:
    t0 = time.time()
    time.sleep(70 if tt else 25)
    ref = ROOT / 'work/ref/mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): break
    time.sleep(45 if tt else 4)
    mw2raids._enter_raids_from_hall(h)
    print('map after %.0f s' % (time.time()-t0), flush=True)
    h.savemem(str(ROOT/'work/snapshots'/f'fire_{tag}_map.sav'))
    r = mw2raids.enter_raid(h, 591, 231)
    print('entered', r, flush=True)
    time.sleep(5)
    print('MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    h.savemem(str(ROOT/'work/snapshots'/f'fire_{tag}_foot.sav'))
    print('saved', flush=True)
finally:
    h.close()
