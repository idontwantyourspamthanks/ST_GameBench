#!/usr/bin/env python3
"""Run a unit-test blob inside a snapshot: python3 run_unit.py SNAP LIVE_NAME TEST.bin RESULT_ADDR LEN [DONE_ADDR]
Applies the live patch (msrabtest.live_build), loadbin TEST.bin at $C0000, hooks $7b74 (jsr $d1e4 -> jsr $C0000), waits for 'DONE' at DONE_ADDR, prints `m`."""
import sys, time, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
from msr import Moonshine
import msrabtest as ab
snap, names, binf, raddr, rlen = sys.argv[1], sys.argv[2].split(","), sys.argv[3], int(sys.argv[4], 16), int(sys.argv[5], 16)
done = int(sys.argv[6], 16) if len(sys.argv) > 6 else 0xC4114
live = ab.live_build(names)
h = Moonshine(snapshot=ab.snap_path(snap))
try:
    time.sleep(1.5)
    ab.apply_live(h, live, 0x7A88)
    f = h.R / "t.txt"
    f.write_text(f"loadbin {Path(binf).resolve()} $c0000\nw $7b74 $4e $b9 $00 $0c $00 $00\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7a88 :trace :once :file {f}")
    t0 = time.time()
    while time.time() - t0 < 120:
        time.sleep(2)
        out = h.debug(f"m ${done:x} 4", 0.5)
        if "44 4f 4e 45" in out: break
    out = h.debug(f"m ${raddr:x} {rlen:x}", 0.8)
    print(out)
finally:
    h.close()
