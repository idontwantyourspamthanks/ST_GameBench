#!/usr/bin/env python3
"""Exp 2b: break at the HAGA copy loop entry ($fb1f0) and exit ($fb204); regs, stack, VBL.
   usage: watch3.py NAME MACHINE TOS MEM [cpuclock] [secs]"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bt
name, machine, tos, mem = sys.argv[1:5]
clk = int(sys.argv[5]) if len(sys.argv) > 5 else 0
secs = int(sys.argv[6]) if len(sys.argv) > 6 else 60
h = bt.start(name, machine, tos, mem)
try:
    if clk: h.set_cpuclock(clk)
    R = h.R
    fe = R / "fe.txt"
    fe.write_text("e VBL\nr\nm $15380 96\nsavebin %s/at_entry.bin 0 $100000\n" % R)
    fx = R / "fx.txt"
    fx.write_text("e VBL\nr\nsavebin %s/at_exit.bin 0 $100000\n" % R)
    fh = R / "fh.txt"
    fh.write_text("e VBL\nr\n")
    h.cmd(f"hatari-debug b ($bb000).l ! ($bb000).l :trace :once :file {fh}")
    time.sleep(0.3)
    h.cmd(f"hatari-debug b pc = $fb1f0 :trace :once :file {fe}")
    time.sleep(0.3)
    h.cmd(f"hatari-debug b pc = $fb204 :trace :once :file {fx}")
    t0 = time.time()
    while time.time() - t0 < secs and not (R / "at_exit.bin").exists():
        time.sleep(1)
    time.sleep(2)
    print("\n".join(l for l in h.logpath.read_text(errors="replace").splitlines() if not l.startswith(">")))
finally:
    h.close()
