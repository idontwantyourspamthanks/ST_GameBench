#!/usr/bin/env python3
"""overlap_live.py: compare the grid in RAM at rebuild entry (/tmp/terr/entry.bin) with the grid at exit (/tmp/terr/exit.bin), shifted by the 40-column recentre."""
import struct
def grid(fn):
    d = open(fn, 'rb').read(); g = 0x40040
    return [[(struct.unpack('>h', d[g + 400 * y + 4 * x:g + 400 * y + 4 * x + 2])[0], d[g + 400 * y + 4 * x + 2], d[g + 400 * y + 4 * x + 3]) for x in range(100)] for y in range(100)]
old, new = grid('/tmp/terr/entry.bin'), grid('/tmp/terr/exit.bin')
tot = eqh = eqa = 0
for y in range(100):
    for x in range(40, 100):
        tot += 1; o = old[y][x - 40]; n = new[y][x]
        eqh += o[0] == n[0]; eqa += o == n
print(f'overlap cells {tot}: heights equal {eqh}, height+shade bytes equal {eqa}')
