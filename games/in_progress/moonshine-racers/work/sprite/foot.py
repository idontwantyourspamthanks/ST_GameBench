#!/usr/bin/env python3
"""Sky-band writes between the cloud erase (return of $de1c, bp $ef84) and the cloud draw (entry of $de6c, bp $efb6): per pass, which bytes of rows 0-69 of the back buffer change."""
import sys, re, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
from msr import Moonshine
import msrabtest as ab
snap = sys.argv[1]; wait = float(sys.argv[2])
h = Moonshine(snapshot=ab.snap_path(snap)); time.sleep(2)
(h.R / "a.txt").write_text("e $a0001\nm $100e 2\nm a5 11200\n")
(h.R / "b.txt").write_text("e $b0001\nm $100e 2\nm a5 11200\n")
(h.R / "c.txt").write_text("e $c0001\nm $100e 2\nm a5 11200\n")
h.debug("b all", 0.3); n0 = len(h._logtext())
for pc, f in ((0xde1c, 'a'), (0xef84, 'b'), (0xefb6, 'c')):
    h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {h.R}/{f}.txt"); time.sleep(0.1)
time.sleep(wait)
h.debug("b all", 1); log = h._logtext()[n0:]; h.close()
(HERE / "raw").mkdir(exist_ok=True)
(HERE / "raw" / f"foot_{snap}.log").write_text(log)
print(len(log))
