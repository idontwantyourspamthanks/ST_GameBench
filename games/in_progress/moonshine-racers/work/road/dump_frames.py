#!/usr/bin/env python3
"""Dump the road stage inputs/outputs for N consecutive race passes of a snapshot (rd_ study, question 1).
    python3 work/road/dump_frames.py SNAP OUTDIR [--passes 40] [--drive]
Chain of one-shot breakpoints per pass: $100b4 (geometry entry: inputs), $17c42 (draw entry: records), $7b10 (after draw: both screen buffers)."""
import argparse, sys, time, re
from pathlib import Path
GAME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(GAME / "tools"))
from msr import Moonshine
ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("out")
ap.add_argument("--passes", type=int, default=40); ap.add_argument("--drive", action="store_true"); ap.add_argument("--wait", type=float, default=0)
a = ap.parse_args()
out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
for f in out.glob("*.bin"): f.unlink()
snap = a.snap if "/" in a.snap else str(GAME / f"work/snapshots/ste1m_{a.snap}.sav")
STAGES = [
  (0x100b4, "a", [("lo", 0x1000, 0x400), ("tb", 0x2300, 0x500), ("g", 0x4500, 0xe00), ("t68", 0x68000, 0x400), ("sin", 0x1400, 0xf00), ("v", 0x5ff0, 0x20)]),
  (0x17c42, "b", [("lo", 0x1000, 0x400), ("g", 0x4500, 0xe00), ("tab", 0x4ff8, 0xc00), ("cs", 0x10200, 0x400)]),
  (0x7b10, "c", [("s70", 0x70000, 0x7d00), ("s78", 0x78000, 0x7d00)]),
  (0xd1ca, "d", [("s70", 0x70000, 0x7d00), ("s78", 0x78000, 0x7d00), ("pal", 0x3c00, 0x200)]),
]
h = Moonshine(snapshot=snap)
try:
    time.sleep(3)
    if a.drive: h.drive(True)
    seq = []
    for p in range(a.passes):
        for pc, tag, regs in STAGES: seq.append((p, pc, tag, regs))
    for i, (p, pc, tag, regs) in enumerate(seq):
        lines = [f"savebin {out}/p{p:03d}_{tag}_{n}.bin ${ad:x} ${ln:x}" for n, ad, ln in regs]
        if i + 1 < len(seq):
            q = seq[i + 1]; lines.append(f"b pc = ${q[1]:x} :trace :once :file {h.R}/rd_{i + 1}.txt")
        (h.R / f"rd_{i}.txt").write_text("\n".join(lines) + "\n")
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${seq[0][1]:x} :trace :once :file {h.R}/rd_0.txt")
    t0 = time.time()
    last = f"p{a.passes-1:03d}_d_pal.bin"
    while not (out / last).exists() and time.time() - t0 < 600: time.sleep(1)
    time.sleep(1)
    print("done", len(list(out.glob('*.bin'))), "files in", round(time.time() - t0), "s")
finally:
    h.close()
