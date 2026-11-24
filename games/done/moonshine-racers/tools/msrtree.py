#!/usr/bin/env python3
"""Inclusive-cycle call tree from a Hatari `profile save` file (uses the jsr/bsr execution counts in the profile itself).

    python3 tools/msrtree.py work/dumps/ram_race_up.bin work/prof/race_up_100.txt [--root 7960] [--depth 3] [--min 0.5]

Function = jsr/bsr/jmp-abs target buckets (msrprof.targets).  Inclusive per call = incl(F)/entries(F); entries = sum of
executed jsr/bsr counts into F (approximation when F is also entered by jmp or fall-through)."""
import argparse, bisect, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import msrprof

L = re.compile(r"^\$([0-9a-f]+)\s+(.*?)\s+[\d.]+% \((\d+), (\d+), \d+, \d+\)\s*$", re.I)
CALL = re.compile(r"^(jsr|bsr\S*)\s+\$([0-9a-f]+)")

def parse(path):
    ins = {}
    for ln in open(path):
        m = L.match(ln)
        if m:
            ins[int(m.group(1), 16)] = (m.group(2), int(m.group(3)), int(m.group(4)))
    return ins

def build(ram, ins):
    tg = msrprof.targets(ram)
    fn = lambda a: tg[bisect.bisect_right(tg, a) - 1] if a >= tg[0] else a
    excl = defaultdict(int); edges = defaultdict(lambda: defaultdict(int)); ent = defaultdict(int)
    for a, (txt, n, cyc) in ins.items():
        f = fn(a); excl[f] += cyc
        m = CALL.match(txt)
        if m:
            t = int(m.group(2), 16); edges[f][t] += n; ent[t] += n
    return excl, edges, ent, fn

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dump"); ap.add_argument("prof")
    ap.add_argument("--root", default="7960"); ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--min", type=float, default=0.5, help="hide below this %% of a frame")
    ap.add_argument("--frames", type=int, default=0)
    a = ap.parse_args()
    ram = open(a.dump, "rb").read(); ins = parse(a.prof)
    excl, edges, ent, fn = build(ram, ins)
    frames = a.frames or ins.get(msrprof.FLIP_PC, (0, 0, 0))[1] or 1
    memo = {}
    def incl(f, stack=()):
        if f in memo: return memo[f]
        if f in stack: return excl[f]
        t = excl[f]
        for c, n in edges[f].items():
            if ent[c]: t += n * incl(c, stack + (f,)) / ent[c]
        memo[f] = t; return t
    root = fn(int(a.root, 16))
    tot = incl(root)
    print(f"root ${root:x}: inclusive {tot / frames:.0f} cyc/frame ({tot / frames / msrprof.CYC_PER_VBL:.2f} VBL); frames={frames}")
    def show(f, d, calls):
        for c, n in sorted(edges[f].items(), key=lambda kv: -incl(kv[0]) * kv[1] / max(ent[kv[0]], 1)):
            v = n * incl(c) / max(ent[c], 1)
            if v / frames / msrprof.CYC_PER_VBL * 100 < a.min: continue
            print(f"{'  ' * d}${c:05x}  incl {v / frames:9.0f} c/f ({100 * v / frames / msrprof.CYC_PER_VBL:5.1f}% VBL) excl {excl[c] / frames:8.0f}  calls/f {n / frames:6.2f}")
            if d + 1 < a.depth: show(c, d + 1, n)
    print(f"  (root excl {excl[root] / frames:.0f})")
    show(root, 1, 1)
if __name__ == "__main__":
    main()
