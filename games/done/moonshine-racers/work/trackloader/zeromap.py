#!/usr/bin/env python3
"""zeromap.py DUMP.bin [min_kb=4]  -> zero runs (512-byte granularity, like the study's msrdump) and the non-zero islands between them."""
import sys
d = open(sys.argv[1], 'rb').read(); mk = int(sys.argv[2]) if len(sys.argv) > 2 else 4
G = 512; n = len(d) // G
z = [not any(d[i*G:(i+1)*G]) for i in range(n)]
runs = []; i = 0
while i < n:
    if z[i]:
        j = i
        while j < n and z[j]: j += 1
        if (j - i) * G >= mk * 1024: runs.append((i*G, j*G))
        i = j
    else: i += 1
print(f"dump {len(d)//1024} KB; zero runs >= {mk} KB (512-byte granularity):")
for a, b in runs: print(f"  ${a:06x}-${b-1:06x}  {(b-a)//1024:5d} KB")
prev = 0; print("non-zero islands (between those runs):")
for a, b in runs + [(len(d), len(d))]:
    if a > prev: print(f"  ${prev:06x}-${a-1:06x}  {(a-prev)//1024:5d} KB")
    prev = b
