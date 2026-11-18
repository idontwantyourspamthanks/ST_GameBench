#!/usr/bin/env python3
"""Restore a snapshot and dump RAM + print the zero runs (free RAM map).
    python3 tools/msrdump.py work/snapshots/ste4m_race_start.sav work/dumps/ram_ste4m_start.bin --machine ste --mem 4096"""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine
ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("out")
ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
a = ap.parse_args()
h = Moonshine(snapshot=a.snap, machine=a.machine, memsize_kb=a.mem)
try:
    time.sleep(3); h.dump(str(Path(a.out).resolve()), 0, a.mem * 1024); time.sleep(2)
finally:
    h.close()
d = open(a.out, "rb").read(); s = None
for o in range(0, len(d), 0x100):
    z = not any(d[o:o + 0x100])
    if z and s is None: s = o
    if not z and s is not None:
        if o - s >= 0x2000: print(f"zero run ${s:06x}-${o:06x} ({(o - s) // 1024} KB)")
        s = None
if s is not None: print(f"zero run ${s:06x}-${len(d):06x} ({(len(d) - s) // 1024} KB)")
