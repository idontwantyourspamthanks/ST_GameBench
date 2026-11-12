#!/usr/bin/env python3
"""Cycles per VBL of the jag blob (profile): 1mb_ski_stand_J + live set, pad idle and a pad button held.
  prof_pad.py"""
import sys, time
from jlib import *

h = MW1(snapshot=str(SNAP / '1mb_ski_stand_J.sav'), extra=PAD)
P = lambda *a: print(*a, flush=True)
try:
    time.sleep(2)
    apply_live(h, str(HERE / 'jaglive'))
    time.sleep(1.5)
    for tag, key in (('pad idle', None), ('pad B held', 'B'), ('pad Left held', 'left')):
        if key:
            kd(h, key); time.sleep(1.0)
        cpv, pct, mine, totv = blob_cost(h, 100)
        P(f'{tag:14s}: {cpv:8.1f} cycles/VBL in $b6900-$b6c3f = {pct:.3f} % of the profiled cycles ({totv:.0f}/VBL profiled; VBL = 160256 cycles = {100 * cpv / 160256:.3f} %)')
        if key:
            ku(h, key); time.sleep(0.5)
    # break-down: top addresses of the last run
    P('hot addresses (last run):', sorted(mine, key=lambda x: -x[1])[:8])
finally:
    h.close()
