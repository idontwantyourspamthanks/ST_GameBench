#!/usr/bin/env python3
"""Per-pass cloud slot state (slots 0-11 at $29c8, 56 B each) at the entry of $de1c, for a snapshot: raw -> work/sprite/raw/cloud_<snap>.log"""
import sys, re, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
from msr import Moonshine
import msrabtest as ab
snap = sys.argv[1]; wait = float(sys.argv[2]) if len(sys.argv) > 2 else 25
h = Moonshine(snapshot=ab.snap_path(snap))
time.sleep(2)
(h.R / "c.txt").write_text("e $c10d\nm $100e 2\nm $29c8 672\n")
h.debug("b all", 0.3)
n0 = len(h._logtext())
h.cmd(f"hatari-debug b pc = $de1c :trace :file {h.R}/c.txt")
time.sleep(wait)
h.debug("b all", 1)
log = h._logtext()[n0:]
h.close()
(HERE / "raw").mkdir(exist_ok=True)
(HERE / "raw" / f"cloud_{snap}.log").write_text(log)
print(len(log), log.count("Reading debugger"))
