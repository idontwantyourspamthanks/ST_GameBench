#!/usr/bin/env python3
"""Who writes the Gamex TOS-state backup ($c0108+) after the game entry? Conditional bp on a changing byte."""
import sys, time, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
h = Nebulus(workdir=str(HERE / 'scratch/cap'))
try:
    cf = HERE / 'scratch/cap/arm2.cmd'
    cf.write_text("b ($c0568).b ! $3b :trace :once :file %s/who.cmd\n" % (HERE/'scratch/cap'))
    (HERE/'scratch/cap/who.cmd').write_text("r\nd pc-8 12\n")
    h.cmd("hatari-debug b pc = $33b00 :trace :once :file %s" % cf)
    ok = h.boot_to_game()
    print('tower', ok)
    log = h._logtext()
    i = log.find('CPU breakpoint')
    print(log[i-200:][:6000])
finally:
    h.close()
