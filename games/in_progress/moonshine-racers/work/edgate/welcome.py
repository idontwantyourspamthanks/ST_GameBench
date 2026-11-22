#!/usr/bin/env python3
"""F10 on the WELCOME PARTNERS / PRESS A KEY screen (cp_welcome + cp_title e3).  env3.sh python3 welcome.py --tag T [--mem 2048|1024] [--machine ste] [--build DIR] [--full]
 cold boot, fast-forward to the screen (one-shot breakpoint at its key-wait loop $7c02), screenshot (hint line F10 = CAMPAIGNS at >= 2 MB, the stock screen at 1 MB); with --full (>= 2 MB):
 F10 -> menu (screenshot) -> Esc = back to the screen (screenshot) -> F10 -> LOAD CAMPAIGN FROM HARD DISK -> play list: track 2 -> the game continues (title) -> SPACE -> a race on the chosen track."""
import argparse
from pathlib import Path
import os, sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="welcome"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--machine", default="ste"); ap.add_argument("--build", default=os.environ.get("ED_BUILD"))
ap.add_argument("--full", action="store_true"); a = ap.parse_args()
logopen(a.tag)
camp = CAMP / "c3.trk"
r = Run("hd", a.machine, a.mem, a.tag, build=a.build, camp_hd=camp, sound=True); h = r.h
try:
    n0 = len(h._logtext())
    h.cmd("hatari-debug b pc = $7c02 :trace :once"); time.sleep(0.5)
    r.ff(True); t0 = time.time()
    while time.time() - t0 < 600 and "pc = $7c02" not in h._logtext()[n0:]: time.sleep(0.4)
    hit = "pc = $7c02" in h._logtext()[n0:]
    r.ff(False); check("the welcome screen's key wait (pc $7c02) reached", hit, f"vbl {h.vbl()}")
    time.sleep(4.0); r.shot("1_welcome")
    if a.mem >= 2048:
        log("V_WELC (CPV+13) =", hex(r.b(0xb8e0d)), " (0xff = the hint line was drawn)")
    if a.full:
        h.keypress(0x44); time.sleep(3.0); r.shot("2_menu")
        h.keypress(0x01) if False else h.cmd("hatari-event keypress 0x01"); time.sleep(3.5); r.shot("3_back_on_welcome"); log("V_WELC after back =", hex(r.b(0xb8e0d)))
        h.keypress(0x44); time.sleep(3.0)
        r.downs(1); h.keypress(0x1c)            # LOAD CAMPAIGN FROM HARD DISK
        t0 = time.time()
        while time.time() - t0 < 60 and not r.b(V["loaded"]): time.sleep(0.5)
        time.sleep(2.5); log("loaded", r.b(V["loaded"]), "count", r.w(V["count"])); r.shot("4_playlist")
        r.downs(1); h.keypress(0x1c)            # track 2 of the campaign -> start
        time.sleep(3.0); log("after the menu: V_ACT", hex(r.b(V["act"])), "V_START", r.w(V["start"])); r.shot("5_after_menu")
        res = r.wait_race(tmo=200)
        r.st("race start"); r.shot("6_race")
        check("F10 menu on the welcome screen -> play from track 2 -> the race is campaign track 2 (pos 1)", res is not None and r.w(V["pos"]) == 1, f"{res} pos {r.w(V['pos'])}")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
log(f"RESULT {a.tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
