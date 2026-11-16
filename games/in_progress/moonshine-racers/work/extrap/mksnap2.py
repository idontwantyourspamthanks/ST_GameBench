"""python3 mksnap2.py SRC.sav OUT.sav VBLS : restore stock snapshot, run VBLS more (8 MHz), save a new snapshot"""
import sys; sys.path.insert(0, '../timing')
from tlib import *
src, out, nv = sys.argv[1], sys.argv[2], int(sys.argv[3])
h = open_snap(src, 8)
try:
    v = h.vbl(); start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v + nv} :trace :once")
    h._wait_removed(start, 600)
    h.savemem(str(Path(out).resolve())); time.sleep(2)
    print("saved", out, "at VBL", h.vbl(), "pass", h.debug("m $100e 2")[-80:])
finally:
    h.close()
