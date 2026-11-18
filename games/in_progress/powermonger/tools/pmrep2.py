#!/usr/bin/env python3
"""Cluster report of a Hatari profile saved by pmprof2.py: python3 tools/pmrep2.py work/prof2/get_men_8_p [--top 25] [--gap 64]
Blocks = runs of executed addresses with gaps <= --gap bytes; per block: share, entries per rendered pass, cycles per entry."""
import re, sys, argparse
LINE = re.compile(r"^\$([0-9A-Fa-f]+)\s+(.*?)\s+[\d.]+% \((\d+), (\d+),", re.M)

def load(path):
    rows = {}
    for m in LINE.finditer(open(path).read()):
        rows[int(m.group(1), 16)] = (m.group(2).strip(), int(m.group(3)), int(m.group(4)))
    return rows

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("--top", type=int, default=25); ap.add_argument("--gap", type=int, default=64)
    a = ap.parse_args()
    rows = load(a.base + ".txt")
    addrs = sorted(rows)
    total = sum(r[2] for r in rows.values())
    passes = rows.get(0x12ce0, ("", 0, 0))[1] or 1
    vbl = rows.get(0x1282, ("", 0, 0))[1]
    print(f"{a.base}: total {total} cycles, VBL handler runs {vbl}, rendered passes ($12ce0 entries) {passes}, {total/passes:.0f} cycles/pass")
    cl = []; cur = None
    for ad in addrs:
        if cur and ad - cur[1] <= a.gap:
            cur[1] = ad; cur[2] += rows[ad][2]; cur[3] = max(cur[3], rows[ad][1])
        else:
            cur = [ad, ad, rows[ad][2], rows[ad][1], ad]; cl.append(cur)
    cl.sort(key=lambda c: -c[2])
    print("| block | share % | cycles/pass | entries/pass | cycles/entry | first insn |")
    for c in cl[:a.top]:
        n = rows[c[0]][1]
        print(f"| ${c[0]:06x}-${c[1]:06x} | {100*c[2]/total:5.1f} | {c[2]/passes:9.0f} | {n/passes:7.1f} | {c[2]/max(1,n):8.0f} | {rows[c[0]][0]} |")
main()
