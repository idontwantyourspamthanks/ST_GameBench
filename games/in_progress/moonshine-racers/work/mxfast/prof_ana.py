"""Bucket a prof_mx.py output by label window.  python3 prof_ana.py OUT.txt PATCHFILE [lo hi]"""
import sys, re, collections
from mflib import *
f, pf = sys.argv[1], sys.argv[2]
lo = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0xb8000; hi = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0xba000
txt = open(f).read()
ci = txt.index('profile counts'); cy = txt.index('profile cycles')
def tab(t):
    d = {}
    for m in re.finditer(r'^0x([0-9a-f]{6})\s+[\d.]+%\s+(\d+)\s+(.*)$', t, re.M): d[int(m.group(1), 16)] = (int(m.group(2)), m.group(3).strip())
    return d
cnt = tab(txt[ci:cy]); cyc = tab(txt[cy:])
lm = labelmap(pf)
def lab(a):
    best = None
    for x, l in lm:
        if x <= a: best = l
        else: break
    return best
sy = symbols(pf)
groups = cnt.get(sy['saveundo'], (0,))[0]; extras = cnt.get(sy['prerestore'], (0,))[0]; ticks = cnt.get(sy['extras'], (0,))[0]; pre = cnt.get(0xb8300, (0,))[0]
print(f'executions: extras-entry {ticks}, mx_pre {pre}, saveundo (groups) {groups}, prerestore (extra frames) {extras}')
b = collections.Counter(); tot = 0
for a, (c, _) in cyc.items():
    if lo <= a < hi: b[lab(a)] += c; tot += c
print(f'cycles in {lo:x}-{hi:x}: {tot}')
for l, c in sorted(b.items(), key=lambda kv: -kv[1])[:40]:
    print(f'  {str(l):24s} {c:10d}  per group {c/max(groups,1):9.0f}  per extra {c/max(extras,1):9.0f}')
