#!/usr/bin/env python3
"""Floppy build: does the WELCOME PARTNERS / PRESS A KEY screen occur, and does the hint / F10 work?  env4.sh python3 welcomefl.py --tag T --mem 2048|1024 [--machine ste]
 cold boot of disk A (no keys), fast-forward, poll V_WELC ($b8e0d), screenshot every 20 s of wall time; at the screen: shot, F10, shot."""
import argparse, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="wfl"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--machine", default="ste")
ap.add_argument("--disk", default="/tmp/msred4/fl/disk_a.st"); ap.add_argument("--secs", type=int, default=240); a = ap.parse_args()
logopen(a.tag)
r = Run("fl", a.machine, a.mem, a.tag, disk_a=a.disk, sound=True); h = r.h
try:
    r.ff(True); t0 = time.time(); k = 0; seen = False
    while time.time() - t0 < a.secs:
        time.sleep(1.0)
        if a.mem >= 2048 and r.b(0xb8e0d): seen = True; break
        if int(time.time() - t0) // 20 > k: k += 1; log("t", int(time.time() - t0), "vbl", h.vbl(), "V_WELC", hex(r.b(0xb8e0d))); r.shot(f"t{k:02d}")
    r.ff(False); log("welcome hint drawn (V_WELC):", seen, "vbl", h.vbl())
    time.sleep(0.5); r.shot("1_welcome")
    if seen:
        h.keypress(0x44); time.sleep(5.0); r.shot("2_menu")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
