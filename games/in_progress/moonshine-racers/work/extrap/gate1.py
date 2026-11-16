import sys
from gate0 import *
R = [(0x13a2, 0x10), (0x1bb0, 9), (0x1bba, 2), (0x23bc, 12), (0x27c8, 0x26), (0x1308, 4), (0x12f0, 0x18), (0x1316, 0x10), (0x23c4, 2),
     (0x13b0, 0x400), (0x17b0, 0x400), (0x1bbc, 0x800), (0x23c8, 0x400),   # whole rings (validation only)
     (0x2c68, 0x34f0+0x38*6-0x2c68)]
d = gate(sys.argv[1], int(sys.argv[2]), restore=R)
print(len(d), "differing bytes")
for s, t in runs(d):
    print(f"{s:05x}-{t:05x} ({t-s+1}) in {len(set(p for a in range(s,t+1) for p in d.get(a,[])))} passes")
