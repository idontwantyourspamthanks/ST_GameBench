#!/usr/bin/env python3
"""Trace START's file calls on a cold boot (frozen recipe): non-stopping breakpoints with register/arg dumps.
START text base on 1 MB STE / TOS 1.62 / HDDRIVER = $1ae16 (verified: text matches RAM there)."""
import sys, time, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
B = 0x1ae16
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
sites = {'fopen_tit': 0x2b4, 'fread_tit': 0x2d0, 'fopen_exe': 0x30e, 'fread_exe': 0x33e, 'setpal_tit': 0x2fa,
         'fopen_pch_tt': 0x126e, 'fopen_pch_st': 0x1834, 'fread_pch_st': 0x1850, 'stage_pch_tt_read': 0x1288,
         'hook_copy': 0x3a2, 'jmp_game': 0x3b2, 'f9_sub': 0x1206}
h = Nebulus(workdir=str(HERE / 'scratch/cap'))
try:
    for nm, off in sites.items():
        cf = out / f'{nm}.cmd'
        cf.write_text(f"r\nm a7 16\nm $ff8201 1\nm $ff8203 1\nm $ff820d 1\nm $ff8260 1\nm $ff8240 32\nm $42e 4\nm $436 4\nsavebin {out}/ram_{nm}.bin 0 $100000\n" if nm in ('fopen_tit','jmp_game') else "r\nm a7 16\nm $ff8201 1\nm $ff8203 1\nm $ff8260 1\n")
        h.cmd(f"hatari-debug b pc = ${B+off:x} :trace :once :file {cf}")
        h.cmd(f"hatari-debug b pc = ${B+off:x} :trace :once :file {cf}") if False else None
    ok = h.boot_to_game(shots=out)
    print('tower', ok)
    (out / 'trace.log').write_text(h._logtext())
finally:
    h.close()
