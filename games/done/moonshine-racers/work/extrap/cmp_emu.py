import sys
from emu import *
e = Emu('h_start_7a88.bin')
e.run(0x7a88, 0x7b74)
ref = open('h_start_7b74.bin','rb').read()
mine = e.read(0, 0x100000)
d = [i for i in range(0x100000) if ref[i] != mine[i]]
print(len(d), "differing bytes")
# group into runs
runs = []
for a in d:
    if runs and a - runs[-1][1] <= 8: runs[-1][1] = a
    else: runs.append([a, a])
for s, t in runs[:60]: print(f"{s:06x}-{t:06x} ({t-s+1})")
print(len(runs), "runs")
