#!/usr/bin/env python3
"""PLAY gate: HD build + campaign file, F10 menu, LOADED CAMPAIGN -> play list -> track N, observe the race. 
   env3.sh python3 play1.py --build DIR --camp FILE --track N [--machine ste]"""
import argparse, sys, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--build"); ap.add_argument("--camp"); ap.add_argument("--track", type=int, default=2); ap.add_argument("--tag", default="play1")
a = ap.parse_args()
logopen(a.tag)
r = Run("hd", "ste", 2048, a.tag, build=a.build, camp_hd=Path(a.camp), sound=True)
try:
    ok = r.boot_title(); log("title", ok); r.menu_open(); time.sleep(1)
    r.downs(1); r.key(0x1c); t0 = time.time()
    while time.time() - t0 < 60 and not r.b(V["loaded"]): time.sleep(0.5)
    time.sleep(2.5); log("loaded", r.b(V["loaded"]), "count", r.w(V["count"]))
    r.shot("afterload")                          # a successful load opens the play list directly
    r.downs(a.track - 1); r.shot("playlist"); r.key(0x1c)
    n0 = time.time()
    for i in range(40):
        time.sleep(1.0)
        r.st(f"t+{i+1}s")
        r.shot(f"s{i+1:02d}") if i % 2 == 1 else None
        if r.race_up(): break
finally:
    r.close()
