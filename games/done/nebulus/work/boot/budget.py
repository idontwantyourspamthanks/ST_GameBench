#!/usr/bin/env python3
"""Inclusive per-frame cost tree from a Hatari `profile save` file of the Nebulus tower (call edges from executed jsr/bsr counts).
usage: budget.py PROF [--frames N | --flip HEX] [--root HEX] [--depth D] [--min CYC]
Self cost of a function = cycles of its addresses up to the next call target; inclusive cost distributes a callee's inclusive cost
over its callers in proportion to the executed call counts (exact for single-caller functions; shared helpers are split pro rata)."""
import re, sys, bisect, argparse, collections
ap = argparse.ArgumentParser(); ap.add_argument('prof'); ap.add_argument('--flip', default='3868e'); ap.add_argument('--root', default='3dcf4')
ap.add_argument('--depth', type=int, default=3); ap.add_argument('--min', type=int, default=1500); ap.add_argument('--names', default=None)
a = ap.parse_args()
prof = {}; call = {}
rx = re.compile(r'^\$([0-9a-f]+)\s+(\S+)\s*(.*?)\s+[\d.]+% \((\d+), (\d+),')
for ln in open(a.prof):
    m = rx.match(ln)
    if not m: continue
    ad = int(m.group(1), 16); mn, op = m.group(2), m.group(3)
    prof[ad] = (int(m.group(4)), int(m.group(5)))
    mm = re.match(r'(jsr|bsr)', mn)
    if mm:
        t = re.match(r'\$([0-9a-f]+)', op)
        call[ad] = int(t.group(1), 16) if t else None
frames = prof.get(int(a.flip, 16), (0, 0))[0]
targets = sorted({t for t in call.values() if t})
root = int(a.root, 16)
targets = sorted(set(targets) | {root, 0x3dfe0, 0x3822c})
def func_of(ad):
    i = bisect.bisect_right(targets, ad) - 1
    return targets[i] if i >= 0 else None
selfc = collections.Counter(); edges = collections.defaultdict(lambda: collections.Counter()); callcnt = collections.Counter(); indirect = collections.Counter()
for ad, (n, c) in prof.items():
    f = func_of(ad); selfc[f] += c
    if ad in call:
        t = call[ad]
        if t: edges[f][t] += n; callcnt[t] += n
        else: indirect[f] += c
memo = {}
def incl(f, stack=()):
    if f in memo: return memo[f]
    if f in stack: return 0
    tot = selfc[f]
    for g, n in edges[f].items():
        if callcnt[g]: tot += incl(g, stack + (f,)) * n / callcnt[g]
    memo[f] = tot; return tot
names = {}
if a.names:
    for ln in open(a.names):
        p = ln.split(None, 1)
        if len(p) == 2: names[int(p[0], 16)] = p[1].strip()
def show(f, depth, mult=1.0, ind=0):
    ic = incl(f) * mult
    print(f"{'  '*ind}{f:06x} {names.get(f,''):<22} incl {ic/frames:9.0f}/frame  self {selfc[f]*mult/frames:8.0f}  calls/frame {callcnt[f]/frames*mult:6.1f}")
    if depth == 0: return
    for g, n in sorted(edges[f].items(), key=lambda kv: -incl(kv[0]) * kv[1] / max(callcnt[kv[0]], 1)):
        sh = n / callcnt[g] if callcnt[g] else 0
        if incl(g) * sh / frames >= a.min: show(g, depth - 1, mult * sh, ind + 1)
tot = sum(c for n, c in prof.values())
print(f"frames(flip {a.flip}) = {frames}; profiled cycles {tot} = {tot/160256:.1f} VBL; per frame {tot/frames:.0f} cycles = {tot/frames/160256:.2f} VBL")
idle = sum(c for ad, (n, c) in prof.items() if 0x3822c <= ad < 0x3827c)
print(f"frame pacer 3822c spin {idle/frames:.0f}/frame = {100*idle/tot:.1f}% ; busy {(tot-idle)/frames:.0f}/frame = {(tot-idle)/frames/160256:.2f} VBL")
show(root, a.depth)
