#!/usr/bin/env python3
"""Cold boot (frozen recipe) with a non-stopping breakpoint at the game entry pc=$33b00 that saves RAM there.
usage: capture.py OUTDIR [machine memKB tos]"""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus, TOS
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
h = Nebulus(workdir=str(HERE / 'scratch/cap'))
try:
    cmdf = out / 'entry.cmd'
    cmdf.write_text(f"savebin {out}/ram_entry.bin 0 $100000\n")
    h.cmd(f"hatari-debug b pc = $33b00 :trace :once :file {cmdf}")
    ok = h.boot_to_game(shots=out)
    print('in tower', ok)
    h.dump(str(out / 'ram_tower.bin'), 0, 0x100000)
    print((out/'ram_entry.bin').exists())
finally:
    h.close()
