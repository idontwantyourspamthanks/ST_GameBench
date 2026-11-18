#!/usr/bin/env python3
"""ramdiff.py A.bin B.bin [--ignore lo-hi ...]: print differing ranges (merged, gap<=16) with classification of ignored areas."""
import sys
a = open(sys.argv[1], 'rb').read(); b = open(sys.argv[2], 'rb').read()
n = min(len(a), len(b))
ign = []
for x in sys.argv[3:]:
    lo, hi = x.split('-'); ign.append((int(lo, 16), int(hi, 16)))
def ig(i):
    return any(lo <= i < hi for lo, hi in ign)
d = [i for i in range(n) if a[i] != b[i]]
print(f'{sys.argv[1]} vs {sys.argv[2]}: {n} bytes compared, {len(d)} differ')
d2 = [i for i in d if not ig(i)]
print(f'  after excluding {len(d) - len(d2)} bytes inside the ignored ranges: {len(d2)} differ')
runs = []
for i in d2:
    if runs and i - runs[-1][1] <= 16: runs[-1][1] = i; runs[-1][2] += 1
    else: runs.append([i, i, 1])
for lo, hi, c in runs[:60]:
    print(f'  ${lo:06x}..${hi:06x} ({c} bytes differ)  A {a[lo:lo+8].hex()}  B {b[lo:lo+8].hex()}')
print(f'  {len(runs)} ranges')
