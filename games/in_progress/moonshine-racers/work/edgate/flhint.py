#!/usr/bin/env python3
"""Floppy build, title screen hint (cp_flhint): cold boot disk A to the title (breakpoint at $7242, the title loop), screenshots at fixed VBL counts after it, then (2 MB) F10 -> campaign menu.
   work/edgate/env5.sh python3 work/edgate/flhint.py --tag T --mem 2048|1024 --disk DISK_A.st [--machine ste] [--f10]"""
import argparse, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="flhint"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--machine", default="ste")
ap.add_argument("--disk", default="/tmp/msred5/fl/disk_a.st"); ap.add_argument("--f10", action="store_true"); ap.add_argument("--vbls", default="150,400,800"); a = ap.parse_args()
logopen(a.tag)
r = Run("fl", a.machine, a.mem, a.tag, disk_a=a.disk, sound=True); h = r.h
try:
    ok = r.boot_title(); log("floppy title reached:", ok, "vbl", h.vbl()); check("title reached", ok)
    v0 = h.vbl(); mk = r.mem(0xb2700, 5); log("marker", mk[:4], "IB+4", hex(mk[4]), "$742e:", r.mem(0x742e, 6).hex())
    for n in [int(x) for x in a.vbls.split(",")]:
        while h.vbl() < v0 + n: time.sleep(0.02)
        r.shot(f"title_{n}")
    if a.f10:
        h.keypress(0x44); time.sleep(5); r.shot("after_f10")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
log(f"RESULT {a.tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
