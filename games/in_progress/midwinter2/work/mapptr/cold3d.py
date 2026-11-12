#!/usr/bin/env python3
"""Cold boot of a build to the 3D view; checks MWPO, the p8_tt_ptr site / TT_F byte, and that walking works.
usage: cold3d.py NAME BUILD MACHINE MEM MODE   (MODE boot = Hatari.boot_to_game('M') campaign Lobos; raid = Raids map -> Dhafra (446,177))"""
import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
import mw2raids
from stharness import MACHINE_TOS
name, bd, machine, mem, mode = sys.argv[1:6]
out = ROOT/'work/mapptr'/name; out.mkdir(exist_ok=True)
tt = machine == 'tt'
h = Hatari(snapshot=None, machine=machine, tos=MACHINE_TOS[machine], memsize_kb=int(mem), game_dir=ROOT/bd, extra=['--mmu','true'] if tt else None)
try:
    if mode == 'boot':
        h.boot_to_game('M')
    else:
        mw2raids.cold_to_raid_map(h) if not tt else None
        if tt:
            time.sleep(70)
            ref = ROOT / 'work/ref/mode_select.png'
            for i in range(60):
                h.cmd('hatari-event keypress 57'); time.sleep(5)
                if h.screen_matches(ref, (280, 350, 560, 420)): break
            for i in range(6):
                time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
                if not h.screen_matches(ref, (280, 350, 560, 420)): break
            time.sleep(45); mw2raids._enter_raids_from_hall(h)
        print(mw2raids.enter_raid(h, 446, 177), flush=True)
    time.sleep(10)
    print('vehicle $6220 =', hex(h.peekw(0x6220)), 'view $700a =', hex(h.peekw(0x700a)))
    print('MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    print('site $26ea2', h.debug('m $26ea2 6').strip().splitlines()[-1])
    print('TT_F $b4f80', h.debug('m $b4f80 2').strip().splitlines()[-1])
    h.shot(str(out/'3d.png'))
    h.rel(0, -200); h.center(); h.rel(0, -200); time.sleep(8)
    h.shot(str(out/'walk.png'))
    print('world rate', h.world_rate(vbls=250), flush=True)
finally:
    h.close()
