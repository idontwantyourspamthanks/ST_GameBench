#!/usr/bin/env python3
"""Per-region changed-byte statistics between consecutive presented frames captured by msrframes.py.
    python3 tools/msrdiff.py work/frames/grid"""
import re, sys
from pathlib import Path
d = Path(sys.argv[1])
log = (d / "log.txt").read_text()
bufs = [int(a + b, 16) for a, b in re.findall(r"00001008:\s+00 ([0-9a-f]{2}) ([0-9a-f]{2}) 00", log)]
n = len(list(d.glob("f*_70.bin")))
F = []
for k in range(n):
    which = "70" if bufs[k] == 0x70 << 8 | 0 or bufs[k] == 0x7000 else "78"
    which = "70" if bufs[k] == 0x0700 else "78"
    F.append((d / f"f{k:02d}_{which}.bin").read_bytes()[:32000])
print("finished buffer at each flip:", ["70" if b == 0x0700 else "78" for b in bufs[:n]])
bands = [("rows 0-64 (sky/clouds/HUD top)", 0, 65), ("rows 65-119 (mountain strip)", 65, 120), ("rows 120-199 (road)", 120, 200)]
for gap in (1, 2):
    print(f"\nfinished frame k vs k+{gap}: mean changed bytes per band (of {{}} bytes)")
    for name, lo, hi in bands:
        tot = 0; cnt = 0
        for k in range(n - gap):
            a, b = F[k][lo * 160:hi * 160], F[k + gap][lo * 160:hi * 160]
            tot += sum(1 for x, y in zip(a, b) if x != y); cnt += 1
        print(f"  {name:34s} {tot / cnt:8.0f} of {(hi - lo) * 160}")
# per-8-row-band for gap 1 and 2 summary
for gap in (1, 2):
    print(f"\nrows 8-row bands, gap {gap}, mean changed bytes:")
    line = []
    for r in range(0, 200, 8):
        tot = 0
        for k in range(n - gap):
            a, b = F[k][r * 160:(r + 8) * 160], F[k + gap][r * 160:(r + 8) * 160]
            tot += sum(1 for x, y in zip(a, b) if x != y)
        line.append(f"{r}:{tot / (n - gap):.0f}")
    print("  " + "  ".join(line))
