#!/usr/bin/env python3
"""Find which RAM words count real time (VBL) vs frames: restore a snapshot, dump $1000-$7000 twice N VBLs apart, list the
words that grew by 1..60.   python3 tools/msrclock.py work/snapshots/ste1m_race_grid.sav --clock 8 --vbls 500
Run at two clocks: a word whose delta stays equal is VBL/real-time driven, one whose delta scales with fps is frame driven."""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, GAME, peeks

ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("--clock", type=int, default=8)
ap.add_argument("--vbls", type=int, default=500); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
a = ap.parse_args()
h = Moonshine(snapshot=a.snap, machine=a.machine, memsize_kb=a.mem)
try:
    time.sleep(3)
    if a.clock: h.set_cpuclock(a.clock)
    h.dump("/tmp/msrclk_a.bin", 0, 0x7000); w0 = peeks(h); v0 = h.vbl()
    while h.vbl() < v0 + a.vbls: time.sleep(0.5)
    h.dump("/tmp/msrclk_b.bin", 0, 0x7000); w1 = peeks(h); v1 = h.vbl()
finally:
    h.close()
A = open("/tmp/msrclk_a.bin", "rb").read(); B = open("/tmp/msrclk_b.bin", "rb").read()
print(f"clock {a.clock}: vbl {v0}->{v1} ({v1 - v0}); frame counter $100e {w0['frame100e']}->{w1['frame100e']}")
for o in range(0x1000, 0x7000, 2):
    x = int.from_bytes(A[o:o + 2], "big"); y = int.from_bytes(B[o:o + 2], "big")
    d = (y - x) & 0xFFFF
    if 1 <= d <= 80 and o not in (0x100e, 0x611a, 0x611b):
        print(f"  ${o:04x}: {x} -> {y}  (+{d})")
