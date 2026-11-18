#!/usr/bin/env python3
"""Flip rate per scene by ROUTINE ENTRY: count executions of pc=$3868e (the `move.b $38759,$ff8201` of flip sub_03868a) over N VBLs.
Scenes from snapshots: hiscores.sav (title/attract), 1mb_tower.sav at +0.5 s (interlude) and at +9 s (tower).  usage: scenes.py [N=250]"""
import re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
N = int(sys.argv[1]) if len(sys.argv) > 1 else 250
S = HERE.parent / 'snapshots'
for name, snap, wait in (('title(hiscores.sav)', 'hiscores.sav', 1.0), ('interlude(tower.sav+0.5s)', '1mb_tower.sav', 0.3), ('tower(tower.sav+9s)', '1mb_tower.sav', 9.0)):
    h = Nebulus(snapshot=str(S / snap), workdir='/tmp/nb2s')
    try:
        time.sleep(wait)
        h.debug('b all', 0.3)
        h.cmd('hatari-debug b pc = $3868e :trace')
        time.sleep(0.3)
        start = h._arm_vbl(N)
        log = h._wait_removed(start)
        n = len(re.findall(r'pc = \$3868e', log)) - 0
        print(f'{name}: {n} flips in {N} VBL = {n*50/N:.2f} fps, {N/max(n,1):.2f} VBL/flip')
    finally:
        h.close()
