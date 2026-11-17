#!/usr/bin/env python3
"""Call-tree / bucket report for the Lotus profile (adapted from tools/msrtree.py; range $70000-$f0000, flip $755f6).
usage: lprof.py DUMP PROF [--root HEX] [--depth N] [--min PCT] [--top N]"""
import argparse, bisect, re, sys
from collections import defaultdict
from pathlib import Path
T = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(T)); sys.path.insert(0, str(T.parents[3] / 'tools'))
import msrprof, msrtree, m68dis
msrprof.LO, msrprof.HI = 0x70000, 0xf0000
msrprof.FLIP_PC = 0x755f6
CPV = 160256
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('dump'); ap.add_argument('prof')
    ap.add_argument('--root', default='70d84'); ap.add_argument('--depth', type=int, default=3)
    ap.add_argument('--min', type=float, default=0.5); ap.add_argument('--top', type=int, default=25)
    ap.add_argument('--frames', type=int, default=0)
    a = ap.parse_args()
    ram = open(a.dump, 'rb').read(); ins = msrtree.parse(a.prof)
    excl, edges, ent, fn = msrtree.build(ram, ins)
    frames = a.frames or ins.get(0x755f6, (0, 0, 0))[1] or 1
    tot = sum(v for v in excl.values())
    print(f'frames={frames} total={tot} = {tot/frames:.0f} cyc/frame ({tot/frames/CPV:.2f} VBL)')
    print('-- exclusive by function bucket --')
    for f, c in sorted(excl.items(), key=lambda kv: -kv[1])[:a.top]:
        print(f'${f:05x} excl {c/frames:9.0f} c/f  {100*c/tot:5.1f}%   entries/f {ent.get(f,0)/frames:6.2f}')
    memo = {}
    def incl(f, stack=()):
        if f in memo: return memo[f]
        if f in stack: return excl[f]
        t = excl[f]
        for c, n in edges[f].items():
            if ent[c]: t += n * incl(c, stack + (f,)) / ent[c]
        memo[f] = t; return t
    root = fn(int(a.root, 16))
    print(f'-- tree root ${root:x}: inclusive {incl(root)/frames:.0f} c/f; (root excl {excl[root]/frames:.0f}) --')
    def show(f, d):
        for c, n in sorted(edges[f].items(), key=lambda kv: -incl(kv[0]) * kv[1] / max(ent[kv[0]], 1)):
            v = n * incl(c) / max(ent[c], 1)
            if v / frames / CPV * 100 < a.min: continue
            print(f"{'  '*d}${c:05x}  incl {v/frames:9.0f} c/f ({100*v/frames/CPV:5.1f}% VBL) excl {excl[c]/frames:8.0f}  calls/f {n/frames:6.2f}")
            if d + 1 < a.depth: show(c, d + 1)
    show(root, 1)
main()
