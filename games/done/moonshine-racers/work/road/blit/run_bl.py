#!/usr/bin/env python3
"""python3 run_bl.py CLOCK  -> cycles of each bltest.s test (FrameCycles/VBL at the t<n>_s / t<n>_e labels).  One Hatari."""
import sys, re, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path.insert(0, str(GAME / "tools"))
from msr import Moonshine
clock = int(sys.argv[1]) if len(sys.argv) > 1 else 8
lst = (HERE / "bltest.lst").read_text()
labels = {}
for m in re.finditer(r"^00:([0-9A-F]{8}) .*\b(t\d_[se]):", lst, re.M):
    labels[m.group(2)] = int(m.group(1), 16)
order = sorted(labels, key=lambda k: labels[k])
h = Moonshine(snapshot=str(GAME / "work/snapshots/ste1m_race_grid.sav"))
try:
    time.sleep(1.5)
    if clock != 8: h.set_cpuclock(clock)
    for i, lab in enumerate(order):
        nxt = order[i + 1] if i + 1 < len(order) else None
        txt = f"e VBL\ne FrameCycles\n"
        if nxt: txt += f"b pc = ${labels[nxt]:x} :trace :once :file {h.R}/bl_{nxt}.txt\n"
        (h.R / f"bl_{lab}.txt").write_text(txt)
    start = h.R / "bl_start.txt"
    start.write_text(f"loadbin {HERE / 'bltest.bin'} $c0000\nw $7b74 $4e $b9 $00 $0c $00 $00\nb pc = ${labels[order[0]]:x} :trace :once :file {h.R}/bl_{order[0]}.txt\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7a88 :trace :once :file {start}")
    t0 = time.time()
    while time.time() - t0 < 200:
        time.sleep(2)
        out = h.debug("m $c4000 4", 0.5)
        if "4a 4a 4e 4f" in out: break
    log = h._logtext()[n0:]
finally:
    h.close()
vals = re.findall(r"#(\d+) \(dec\)", log)
ev = [(int(vals[i]), int(vals[i + 1])) for i in range(0, len(vals) - 1, 2)]
print("events", len(ev), "expected", len(order))
CYC = 160256
best = None
for c0 in sorted({fc for _, fc in ev}) + [CYC]:
    t = [(v + (1 if fc < c0 else 0)) * CYC + fc for v, fc in ev]
    bad = sum(1 for i in range(1, len(t)) if t[i] < t[i - 1])
    if best is None or bad < best[0]: best = (bad, c0, t)
bad, c0, t = best
print("wrap fit c0", c0, "violations", bad)
base = None
for i in range(0, len(order), 2):
    name = order[i][:2]; d = t[i + 1] - t[i]
    print(f"{name}: {d} cycles")
