#!/usr/bin/env python3
"""Exp 1/2: change-watch on the bank header ($bb000.l) and on the first tail byte ($e2b6a.b); dump the bank + regs at each hit.
   usage: watch1.py NAME MACHINE TOS MEM [cpuclock] [secs]"""
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
    bank = bt.BANKF.read_bytes()
    cmds = h.R / "hit_hdr.txt"
    cmds.write_text(f"r\nsavebin {h.R}/hdr_{{n}}.bin ${bt.BANK:x} $10\n")
    log = h.R / "events.txt"
    h.cmd(f"hatari-debug b ($bb000).l ! ($bb000).l :trace")
    time.sleep(0.3)
    h.cmd(f"hatari-debug b ($e2b6a).b ! ($e2b6a).b :trace")
    t0 = time.time(); n0 = 0
    while time.time() - t0 < secs:
        time.sleep(1)
    print(h.logpath.read_text(errors="replace")[-3000:])
finally:
    h.close()
