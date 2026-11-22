#!/usr/bin/env python3
"""Floppy build, site $7c04 + gate: boot disk A, fast-forward to the title, read marker / IB+4 / the bytes at $7c04 / V_WELC.  env4.sh python3 sitefl.py --mem 1024|2048"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "campgate"))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--machine", default="ste"); ap.add_argument("--disk", default="/tmp/msred4/fl/disk_a.st"); a = ap.parse_args()
tag = f"sitefl_{a.mem}"; logopen(tag)
r = Run("fl", a.machine, a.mem, tag, disk_a=a.disk, sound=True)
try:
    ok = r.boot_title(); log("floppy title reached:", ok, "vbl", r.vbl()); check("title reached", ok)
    mk = r.mem(0xb2700, 5); log("marker", mk[:4], "IB+4", hex(mk[4]), "site $7c04:", r.mem(0x7c04, 6).hex(), "V_WELC", hex(r.b(0xb8e0d)))
    r.shot("title")
    r.h.keypress(0x44); time.sleep(5); r.shot("after_f10")
    if a.mem >= 2048: log("F10 at the floppy title -> campaign menu: see shot after_f10")
    log(f"Bus/Address error lines: {r.errlines()}")
finally:
    r.close()
log(f"RESULT {tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
