#!/usr/bin/env python3
"""Markdown tables from work/prof/<scn>_<clk>mhz.txt (+ _stages.json) and work/dumps/<scn>.bin.
    python3 pmreport.py map_idle 8"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pmprof import Prof
import pm
G = pm.GAME
scn, clk = sys.argv[1], sys.argv[2]
dump = G / "work/dumps" / f"{scn}.bin"
if not dump.exists():
    dump = G / "work/dumps" / "map_idle.bin"
p = Prof(G / f"work/prof/{scn}_{clk}mhz.txt", dump)
passes = p.rows.get(0x13040, ("", 0, 0))[1]
vbls = p.frames
print(f"## {scn} @ {clk} MHz: VBL-handler runs {vbls}, loop passes {passes}, total {p.total} cycles ({p.total/max(1,passes):.0f}/pass)")
# clusters of executed addresses (gap <= 64 bytes) = hot blocks
cl = []; cur = None
for a in p.addrs:
    if cur and a - cur[1] <= 64:
        cur[1] = a; cur[2] += p.rows[a][2]
    else:
        cur = [a, a, p.rows[a][2]]; cl.append(cur)
cl.sort(key=lambda c: -c[2])
print("| block | cycles/pass | % | entry count/pass | cycles/entry | first instruction |")
print("|---|---:|---:|---:|---:|---|")
for a, b, c in cl[:15]:
    n = p.rows[a][1]
    print(f"| ${a:06x}-${b:06x} | {c/max(1,passes):.0f} | {100*c/p.total:.1f} | {n/max(1,passes):.1f} | {c/max(1,n):.0f} | {p.rows[a][0]} |")
rows = [(a,) + p.rows[a] for a in p.addrs if re.match(r"(mulu|muls|divu|divs)", p.rows[a][0])]
tot = sum(r[3] for r in rows)
print(f"\nmul/div: {tot/p.total*100:.2f} % of cycles; per pass:")
agg = {}
for a, ins, n, c in rows:
    agg.setdefault(p.func_of(a), []).append((a, ins, n))
for f, lst in sorted(agg.items(), key=lambda kv: -sum(x[2] for x in kv[1])):
    print(f"- fn ${f:06x}: " + ", ".join(f"${a:06x} `{ins}` x{n/max(1,passes):.1f}" for a, ins, n in sorted(lst, key=lambda x: -x[2])[:8]))
sj = G / f"work/prof/{scn}_{clk}mhz_stages.json"
if sj.exists():
    r = json.loads(sj.read_text())["trace"]
    from collections import defaultdict
    its = []; curi = []
    for pc, cy, v in r:
        if pc == 0x13040 and curi:
            its.append(curi); curi = []
        curi.append((pc, cy))
    its.append(curi)
    its = [i for i in its if len(i) == len(pm.LOOP_SITES)]
    print(f"\nstages over {len(its)} complete passes (e CycleCounter at call sites):")
    acc = defaultdict(int)
    for it in its:
        for (p0, c0), (p1, c1) in zip(it, it[1:]):
            acc[p0] += (c1 - c0) % 2**32
    tot_ = sum(acc.values())
    for k, v in acc.items():
        print(f"- {pm.LOOP_NAMES.get(k,hex(k))}: {v/len(its):.0f} cycles/pass ({100*v/tot_:.1f} %)")
    print(f"- total {tot_/len(its):.0f} cycles/pass")
