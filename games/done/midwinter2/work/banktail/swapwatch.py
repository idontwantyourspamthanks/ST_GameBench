#!/usr/bin/env python3
"""Evidence that HAGA's area at [$f8094 start, ...) is a live TOS<->game low-memory SWAP buffer, not a one-off backup: breakpoints on the exchange loops
($f92ee / $f93e4 = `move.l (a5),d1 / move.l (a6),(a5)+ / move.l d1,(a6)+`, a5 = $8.., a6 = the area) and on the routine's rts ($f9370 / $f9460 end).
Counts the swaps over the boot + logo + M/J/K + hall walk and prints the first swap's area content before and after.
   usage: swapwatch.py NAME MACHINE TOS MEM_KB"""
import sys, time, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bt
name, machine, tos, mem = sys.argv[1:5]
h = bt.start(name, machine, tos, mem, game=Path("/tmp/mw2tail/rel/hd/MW2PATCH"))
try:
    R = h.R
    f1 = R / "s1.txt"; f1.write_text("e VBL\nr\nm $e2b6a 16\nm $8 16\nm $400 16\n")
    f2 = R / "s2.txt"; f2.write_text("e VBL\nm $e2b6a 16\nm $8 16\nm $400 16\n")
    h.cmd("hatari-debug b pc = $f92ee :trace :once :file %s" % f1); time.sleep(0.3)
    h.cmd("hatari-debug b pc = $f936c :trace :once :file %s" % f2); time.sleep(0.3)
    h.cmd("hatari-debug b pc = $f93e4 :trace"); time.sleep(0.3)      # the other direction, counted only
    t0 = time.time()
    while time.time() - t0 < 200: time.sleep(5)
    txt = h.logpath.read_text(errors="replace")
    print("\n".join(l for l in txt.splitlines() if not l.startswith(">")))
    print("matches of pc=$f93e4:", re.findall(r"pc = \$f93e4 :trace", txt)[-1:] , re.findall(r"(\d+)\. CPU breakpoint condition\(s\) matched (\d+) times", txt)[-3:])
finally:
    h.close()
