"""Profile the mx blob by PC in Hatari.  python3 prof_mx.py SET SNAP MHZ VBLS XTEST OUT   (SET X|M ; XTEST n = forced extras per tick, 0 = natural)"""
import sys, re, json
from hlib import *
sset, snap, mhz, vbls, xt, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
pre = live_build(sset)
h = open_snap(snap, mhz)
try:
    apply_prefix(h, pre, pokes=[(0xB8F21, bytes([xt]))] if xt else [])
    time.sleep(1)
    start = h._arm_vbl(vbls + 25, f" :file {h.R / 'prof_end.txt'}") if False else None
    end = h.R / "prof_end.txt"; end.write_text("m $b8f38 12\nm $100e 2\ne VBL\nprofile counts 30000\nprofile cycles 30000\n")
    m0 = h.debug("m $b8f38 12\nm $100e 2" if False else "m $b8f38 12", 0.8)
    st = h._arm_vbl(vbls + 25, f" :file {end}")
    time.sleep(0.3)
    h.cmd("hatari-debug profile on")
    o = h._wait_removed(st, timeout=1500)
    open(out, 'w').write(m0 + "\n=====\n" + o)
    print(len(o), 'bytes of profile output ->', out)
finally:
    h.close()
