"""python3 mksnap.py SNAP OUT.sav : restore a stock snapshot, apply the mt_* live patch, save a patched snapshot (for tools/msrbench.py)."""
import sys; sys.path.insert(0, '../timing'); sys.path.insert(0, '.')
from mtlive import *
snap, out = sys.argv[1], sys.argv[2]
h = open_snap(snap, 8)
try:
    apply_mt(h); time.sleep(2)
    h.debug("m $d128 6", 0.5); h.savemem(str(Path(out).resolve()))
    print("saved", out)
finally:
    h.close()
