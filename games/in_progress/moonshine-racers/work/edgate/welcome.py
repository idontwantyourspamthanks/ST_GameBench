#!/usr/bin/env python3
"""The WELCOME PARTNERS / PRESS A KEY screen (cp_welcome + cp_title e3).  env7.sh python3 welcome.py --tag T [--mem 2048|1024] [--machine ste] [--build DIR] [--full]
 cold boot, fast-forward until the screen's line was drawn (V_WELC, CPV+13), screenshot: `F10 = CAMPAIGNS` at >= 2 MB, `2 MB: CAMPAIGNS + TRACK EDITOR` at 1 MB (gate byte IB+4 = 0; F10 is an
 ordinary key there); with --full (>= 2 MB): F10 -> menu (screenshot) -> Esc = back to the screen (screenshot) -> F10 -> LOAD CAMPAIGN FROM HARD DISK -> play list: track 2 -> a race on it."""
import argparse
from pathlib import Path
import os, sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="welcome"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--machine", default="ste"); ap.add_argument("--build", default=os.environ.get("ED_BUILD"))
ap.add_argument("--vbl", type=int, default=4300); ap.add_argument("--nof10", action="store_true"); ap.add_argument("--full", action="store_true"); a = ap.parse_args()
logopen(a.tag)
camp = CAMP / "c3.trk"
r = Run("hd", a.machine, a.mem, a.tag, build=a.build, camp_hd=camp, sound=True); h = r.h
try:
    n0 = len(h._logtext())
    r.ff(True); t0 = time.time(); hit = False
    while time.time() - t0 < 600 and not r.b(0xb8e0d): time.sleep(0.3)      # V_WELC = 0xff: the line was drawn = the real screen is up
    hit = bool(r.b(0xb8e0d))
    r.ff(False); check("the welcome screen reached (V_WELC set)", hit, f"vbl {h.vbl()}")
    time.sleep(0.5); r.shot("1_welcome")
    scr = r.l(0x1004); row = b"".join(r.mem(scr + 160 * y, 160) for y in range(184, 192)); gate = r.b(0xb2704)
    log("V_WELC (CPV+13) =", hex(r.b(0xb8e0d)), "gate byte IB+4 =", hex(gate), f"screen ${scr:x}: text row 23 has {sum(1 for x in row if x)} non-zero bytes")
    check("text row 23 of the screen holds the line", any(row))
    if a.mem < 2048:
        check("1 MB: the gate is closed (IB+4 = 0): the line is `2 MB: CAMPAIGNS + TRACK EDITOR` (see the screenshot)", gate == 0)
        h.keypress(0x44); time.sleep(4.0); r.shot("2_after_f10"); a0 = r.b(V["act"]); log("after F10: V_ACT", hex(a0), "V_LOADED", hex(r.b(V["loaded"])), "V_WELC", hex(r.b(0xb8e0d)))
        check("1 MB: F10 is an ordinary key (the screen is left, no campaign menu: V_WELC cleared, nothing loaded)", r.b(0xb8e0d) == 0 and a0 == 0 and r.b(V["loaded"]) == 0)
    if a.full:
        h.keypress(0x44); time.sleep(5.0); r.shot("2_menu")
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
