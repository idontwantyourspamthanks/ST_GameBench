#!/usr/bin/env python3
"""Same run, 16 MHz: in-game timer word $3ad9c rate per VBL with pacer table 2, then poke table=1 and measure again (game speed vs frame rate)."""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
h = Nebulus(snapshot=str(HERE.parent / 'snapshots/1mb_tower.sav'), workdir='/tmp/nb2m')
try:
    time.sleep(1.0); h.set_cpuclock(16); time.sleep(5.0)
    def sample(label, secs):
        v0 = h.vbl(); a = [h.peekw(x) for x in (0x3AD98, 0x3AD9A, 0x3AD9C)]
        time.sleep(secs)
        v1 = h.vbl(); b = [h.peekw(x) for x in (0x3AD98, 0x3AD9A, 0x3AD9C)]
        print(label, [hex(x) for x in a], '->', [hex(x) for x in b], 'over', v1 - v0, 'VBL')
    sample('table=2 (shipped)', 6)
    h.debug('w $3821c $00 $01', 0.4)
    sample('table=1', 6)
    h.debug('w $3821c $00 $02', 0.4)
    sample('table=2 again', 6)
finally:
    h.close()
