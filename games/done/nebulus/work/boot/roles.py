#!/usr/bin/env python3
"""Identify what a function draws: from the baseline snapshot poke `rts` ($4e75) at its entry, let it run 1.5 s, screenshot,
compare to an unpoked run. usage: roles.py OUTDIR HEXADDR[,HEXADDR...]"""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
SNAP = HERE.parent / 'snapshots/1mb_tower.sav'
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
for ad in ['none'] + sys.argv[2].split(','):
    h = Nebulus(snapshot=str(SNAP), workdir='/tmp/nb2r')
    try:
        time.sleep(7.0)
        if ad != 'none':
            h.debug(f'w ${int(ad,16):x} $4e $75', 0.4)
        h._xdo('keydown', 'Right'); time.sleep(0.9)
        h.shot(str(out / f'rts_{ad}.png'))
        h._xdo('keyup', 'Right'); print(ad, 'done')
    finally:
        h.close()
