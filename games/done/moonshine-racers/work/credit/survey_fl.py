"""Floppy cold boot survey (disk A only), screenshot every DT s with no keys. python3 survey_fl.py DISK_A OUTDIR LIMIT_VBL"""
import sys, time, os
sys.path.insert(0, 'tools')
from msrfloppy import mk
a, out, limit = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(out, exist_ok=True)
h = mk(a, machine=os.environ.get("MACHINE","ste"), mem=int(os.environ.get("MEM","1024")), tos=os.environ.get("TOS") or None)
try:
    n = 0
    while True:
        time.sleep(float(os.environ.get("DT", "0.5")))
        v = h.vbl()
        h.shot(f"{out}/{n:03d}_vbl{v}.png"); print(n, v, flush=True); n += 1
        if v > limit: break
finally:
    h.close()
