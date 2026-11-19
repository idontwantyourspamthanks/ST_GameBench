#!/usr/bin/env python3
"""Function-level table of a profile saved by pmprof2.py:  python3 tools/pmtop10.py work/prof2/get_men_8_b2 [--top 10] [--csv]
Ranges are the hand-identified routines (hotpaths.md, hotpaths2.md); everything else is `rest`.  calls = executions of the entry instruction."""
import argparse, re, sys
LINE = re.compile(r"^\$([0-9A-Fa-f]+)\s+(.*?)\s+[\d.]+% \((\d+), (\d+),", re.M)
F = [  # name, lo, hi, entry, role
 ("terrain span fill (orig)", 0xe3e6, 0xe5ab, 0xe3e6, "masked 4-plane span fill of one triangle"),
 ("triangle setup (orig)", 0xef62, 0xf202, 0xef62, "clip tests, sort, 3-7 divu, record for the fill"),
 ("clipper (orig)", 0xf202, 0xf7d0, 0xf202, "polygon clip of partly outside triangles"),
 ("p6_tri setup+fill", 0xd9000, 0xd9800, 0xd9012, "new setup + chunked span fill"),
 ("cell loop", 0xf898, 0xfe00, 0xf898, "per cell: 2 triangles, objects"),
 ("window copy", 0x12ce0, 0x12d08, 0x12ce0, "32000 B picture -> back buffer"),
 ("window copy (p6_cpy)", 0xda000, 0xda100, 0xda000, "blitter copy"),
 ("sprite blit (p4_spr)", 0xbd500, 0xbdc00, 0xbd500, "masked sprite, blitter / pre-shifted cache"),
 ("sprite blit (orig)", 0x12326, 0x126d8, 0x12326, "masked sprite (zoom variants)"),
 ("small sprites (8 px)", 0x11f12, 0x120e9, 0x11f82, "SPRITE8 objects, rol/ror per row"),
 ("object project/sort", 0x11500, 0x11f12, 0x115e0, "per cell object list, screen position"),
 ("object clip front end", 0x12100, 0x12326, 0x12242, "sprite clipping"),
 ("VBL wait", 0x1858, 0x1961, 0x1870, "idle spin until the VBL flag"),
 ("pointer (VBL, p4_ptr)", 0xbd000, 0xbd400, 0xbd000, "mouse pointer skip test"),
 ("pointer (VBL, orig)", 0x1378, 0x14e5, 0x1378, "pointer restore/draw"),
 ("sound (snd_ DMA resampler)", 0xd0000, 0xd5000, 0xd0000, "STE DMA sound producer"),
 ("army/people lists", 0x163ea, 0x16680, 0x163ea, "move person between cell chains"),
 ("men interp (p3b)", 0xb8a80, 0xbb000, 0xb8a80, "predict-ahead men positions"),
 ("tick/timing", 0xb8800, 0xb8a80, 0xb8800, "fixed tick pass logic"),
 ("tooltip (pm_)", 0xcd000, 0xce000, 0xcd000, "tooltip text"),
 ("men sim $14b62", 0x14b62, 0x14bb0, 0x14b62, "people state machine"),
 ("RNG $12c9a", 0x12c9a, 0x12ce0, 0x12c9a, "random numbers"),
 ("group scan/captains", 0x3e06, 0x6600, 0x3e06, "logic"),
]
def load(p):
    rows = {}
    for m in LINE.finditer(open(p).read()):
        rows[int(m.group(1), 16)] = (m.group(2).strip(), int(m.group(3)), int(m.group(4)))
    return rows
def table(base):
    rows = load(base + ".txt")
    tot = sum(r[2] for r in rows.values())
    passes = max(1, rows.get(0x12ce0, ("", 0, 0))[1] + rows.get(0xda000, ("", 0, 0))[1] - (rows.get(0x12ce0, ("", 0, 0))[1] if 0xda000 in rows else 0))
    out = []
    used = 0
    for n, lo, hi, e, role in F:
        c = sum(r[2] for a, r in rows.items() if lo <= a < hi)
        if not c: continue
        calls = rows.get(e, ("", 0, 0))[1]
        out.append((c, n, calls, role)); used += c
    out.sort(reverse=True)
    return out, tot, passes
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    out, tot, passes = table(a.base)
    print(f"{a.base}: {tot} cycles, {passes} rendered passes, {tot/passes:.0f} cycles/pass")
    print("| # | function | share % | cycles/pass | calls/pass | cycles/call | role |\n|---|---|---:|---:|---:|---:|---|")
    for i, (c, n, calls, role) in enumerate(out[:a.top], 1):
        print(f"| {i} | {n} | {100*c/tot:.1f} | {c/passes:.0f} | {calls/passes:.1f} | {c/max(1,calls):.0f} | {role} |")
    rest = tot - sum(c for c, *_ in out)
    print(f"| | rest (HUD, UI, logic, interrupts, ...) | {100*rest/tot:.1f} | {rest/passes:.0f} | | | |")
