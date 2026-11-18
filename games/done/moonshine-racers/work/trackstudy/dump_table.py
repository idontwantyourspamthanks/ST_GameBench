#!/usr/bin/env python3
"""Decoded human-readable segment table of a level (union of all stream breakpoints). usage: dump_table.py LEVEL > out.md"""
import sys, numpy as np
from msrtrack import *
lev = int(sys.argv[1]); t, b = parse(lev); m = minimap(lev); L = int(m['len'])
def bounds(stream):
    s = 0; out = []
    for n, v in stream: out.append((s, s+n, v)); s += n
    return out
S = {k: bounds(t[k]) for k in ('curve', 'left', 'right', 'hill')}
bp = sorted(set(x for k in S for (a, e, v) in S[k] for x in (a, e)) | {0, L})
bp = [x for x in bp if x <= L]
c = curve_arrays(t); hill = ring_arrays(t['hill'], 'hill'); lw = ring_arrays(t['left'], 'slew'); rw = ring_arrays(t['right'], 'slew')
od = np.cumsum([t['obj_first']] + [g for _, _, g in t['objs']][:-1])
def at(k, s):
    for a, e, v in S[k]:
        if a <= s < e: return v
print(f'# Level {lev}: block MS2 sector {t["sector"]:#x} ({t["sector"]*512:#x}), {t["nsect"]} sectors; race length {L} (minimap header word 0); streams: curve {len(t["curve"])} left {len(t["left"])} right {len(t["right"])} hill {len(t["hill"])} objects {len(t["objs"])} (types at block+{t["types_off"]:#x})')
print('| seg | start | len | curve delta | c(start) | c(end) | hill accel | height(start) | left tgt | right tgt | left w | right w | objects |')
print('|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for i in range(len(bp)-1):
    a, e = bp[i], bp[i+1]
    nobj = int(((od >= a) & (od < e)).sum())
    print(f'| {i} | {a} | {e-a} | {at("curve",a)} | {int(c[a])} | {int(c[e-1])} | {at("hill",a)} | {int(hill[a])} | {at("left",a)} | {at("right",a)} | {int(lw[a])} | {int(rw[a])} | {nobj} |')
