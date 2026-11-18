#!/usr/bin/env python3
"""Cold boot with `--trace gemdos`, break at the game's first instruction `$6f60` (init: clears MFP, installs vectors) and dump
registers, the stack, the low-RAM stubs and all RAM at that instant (before PP's patcher area is overwritten).
    python3 tools/msrentry.py [--machine ste --mem 1024]  -> work/notes/entry_<machine>_<mem>.txt, work/dumps/ram_entry_<mem>.bin"""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, GAME
ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
ap.add_argument("--pc", default="6f60"); a = ap.parse_args()
dump = GAME / f"work/dumps/ram_entry_{a.mem}.bin"
h = Moonshine(machine=a.machine, memsize_kb=a.mem, extra=["--trace", "gemdos"])
try:
    cmds = h.R / "entry.txt"
    cmds.write_text(f"r\nm $%x 64\nsavebin {dump} 0 ${a.mem * 1024:x}\n" % (0,) if False else f"r\nsavebin {dump} 0 ${a.mem * 1024:x}\n")
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${a.pc} :trace :once :file {cmds}")
    t = time.time()
    while time.time() - t < 400 and "Removed CPU breakpoint" not in h._logtext(): time.sleep(2)
    time.sleep(8)
    log = h._logtext()
finally:
    h.close()
(GAME / f"work/notes/entry_{a.machine}_{a.mem}.txt").write_text(log)
import re
print("\n".join(l for l in log.splitlines() if re.search(r"GEMDOS|Fopen|Fread|Fseek|Pexec|Fclose|PC=|^\s+D0|^\s+A0|SR=|USP|Removed", l))[:6000])
