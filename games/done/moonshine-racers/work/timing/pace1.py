import sys; sys.path.insert(0,'.')
from tlib import *
snap, mhz, nfr = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
h = open_snap(snap, mhz)
try:
    pcs = [0x7a88, 0x7b0a, 0xd1ca, 0xd1f6]
    log = chain(h, pcs, ["m $611a 2", "m $1004 8", "m $ff8200 4"], nfr*6/50*1.1+3)
finally:
    h.close()
open(f"pace_{snap}_{mhz}.raw","w").write(log)
print(log[:3000])
