#!/usr/bin/env python3
"""Render work/notes/stages_<name>.txt as a markdown table (callee per stage row, cycles, % of the mean frame period)."""
import re, subprocess, sys
from pathlib import Path
GAME = Path(__file__).resolve().parents[1]
BENCH = GAME.parents[2]
dump = GAME / "work/dumps/ram_race_up.bin"
calls = {}
for a, b in (("7960", "7b7c"), ("ef7a", "efc6")):
    for ln in subprocess.run([sys.executable, str(BENCH / "tools/m68dis.py"), str(dump), a, "--end", b], capture_output=True, text=True).stdout.splitlines():
        m = re.match(r"([0-9a-f]{6}):\s+([0-9a-f]+)\s+(jsr|bsr)\S*\s+\$([0-9a-f]+)", ln)
        if m:
            calls[int(m.group(1), 16) + len(m.group(2)) // 2] = int(m.group(4), 16)
rows = []
for ln in open(GAME / f"work/notes/stages_{sys.argv[1]}.txt"):
    m = re.match(r"([0-9a-f]+) n=\s*(\d+) mean=\s*(\d+) min=\s*(\d+) max=\s*(\d+)", ln)
    if m:
        pc = int(m.group(1), 16); rows.append((pc, int(m.group(3)), int(m.group(4)), int(m.group(5))))
tot = sum(r[1] for r in rows)
print(f"mean frame period (sum of stages) = {tot} cycles = {tot / 160256:.2f} VBL\n")
print("| stage (call returning at) | callee | mean cyc | % frame | min | max |\n|---|---|---:|---:|---:|---:|")
for pc, mean, lo, hi in rows:
    if mean < 1500 and pc not in (0x7b7a,): continue
    c = calls.get(pc)
    name = f"`${c:05x}`" if c else "(loop code)"
    print(f"| ${pc:05x} | {name} | {mean} | {100 * mean / tot:.1f}% | {lo} | {hi} |")
small = sum(r[1] for r in rows if r[1] < 1500 and r[0] != 0x7b7a)
print(f"| (all stages < 1500 cyc) | | {small} | {100 * small / tot:.1f}% | | |")
