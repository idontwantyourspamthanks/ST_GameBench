"""What do the post stages (18888 18c86 18f0e at $7b52..$7b74) write?  python3 post_trace.py DUMP KIND NPASS"""
import sys, collections
from mflib import *
dump, kind, npass = DUMPS.get(sys.argv[1], sys.argv[1]), sys.argv[2], int(sys.argv[3])
e = Emu(dump)   # stock game
scr = collections.Counter(); other = collections.Counter(); slot = collections.Counter(); anyscr = 0
for p in range(npass):
    v = schedule(p, kind); e.setb(0x6105, v)
    e.run(0x7a88, 0x7b52)
    e.trace(True); e.run(0x7b52, 0x7b74)
    for a in e.wr:
        if 0x70000 <= a < 0x77d00 or 0x78000 <= a < 0x7fd00: scr['screen'] += 1
        elif 0x77d00 <= a < 0x78000: scr['stack'] += 1
        elif 0x2c68 <= a < 0x36e8: slot[(a - 0x2c68) // 56] += 1
        else: other[a >> 4 << 4] += 1
    e.trace(False)
    e.call(0xd1ca); e.run(0x7b7a, 0x7a88)
print(sys.argv[1:], 'screen writes by post stages:', dict(scr))
print('slots written (idx: count):', dict(sorted(slot.items())))
print('other write blocks:', sorted((hex(a), c) for a, c in other.items())[:40])
