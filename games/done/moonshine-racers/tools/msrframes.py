#!/usr/bin/env python3
"""Capture N consecutive presented frames (both screen buffers at every flip $d1ca) from a snapshot.

    python3 tools/msrframes.py work/snapshots/ste1m_race_grid.sav work/frames/grid --n 12 [--drive]
Chain of `b pc = $d1ca :once :file` breakpoints, each saving $70000/$78000 (32000 bytes) then arming the next.
At the flip, $1008 (the buffer just drawn) is about to become the displayed one.  Writes <dir>/f<k>_70.bin, f<k>_78.bin and
<dir>/order.txt with `$1008` at each flip (which buffer was the freshly drawn one)."""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, GAME

ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("out"); ap.add_argument("--n", type=int, default=12)
ap.add_argument("--drive", action="store_true"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
a = ap.parse_args()
out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
h = Moonshine(snapshot=a.snap, machine=a.machine, memsize_kb=a.mem)
try:
    time.sleep(3)
    if a.drive: h.drive(True)
    for k in range(a.n):
        lines = [f"savebin {out}/f{k:02d}_70.bin $70000 $7d00", f"savebin {out}/f{k:02d}_78.bin $78000 $7d00", "m $1008 4"]
        if k + 1 < a.n:      # arm the next flip from $7b7a (after the flip call returns): arming $d1ca while AT $d1ca fires at once
            lines.append(f"b pc = $7b7a :trace :once :file {h.R}/fr_w{k}.txt")
        (h.R / f"fr_{k}.txt").write_text("\n".join(lines) + "\n")
        (h.R / f"fr_w{k}.txt").write_text(f"b pc = $d1ca :trace :once :file {h.R}/fr_{k + 1}.txt\n")
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $d1ca :trace :once :file {h.R}/fr_0.txt")
    time.sleep(a.n * 0.8 + 8)
    log = h._logtext()[n0:]
    (out / "log.txt").write_text(log)
finally:
    h.close()
print(len(list(out.glob("f*_70.bin"))), "frames captured in", out)
