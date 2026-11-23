#!/usr/bin/env python3
"""Repeated test drives on a plain straight (hill or not) from alternating cursor units; stops at the first Address Error / unexpected Bus Error.
work/edgate/envcrash.sh python3 work/edgate/crash3.py --tag T [--level 0] [--hill 3|none] [--n 20] [--machine ste]"""
import argparse, random, re as _re
import ed2lib
from ed2lib import *
_Run = ed2lib.Run
ed2lib.Run = lambda *a, **k: _Run(*a, extra_args=["--alert-level", "fatal"], **k)
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="crash3"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--machine", default="ste")
ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--hill", default="3"); ap.add_argument("--level", type=int, default=0); ap.add_argument("--n", type=int, default=20); ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--noff", action="store_true")
a = ap.parse_args()
VTD = 0xb8e0e
e = Ed(a.tag, a.machine, a.mem, a.build, None); r = e.r
def bad(): return len([l for l in r.h._logtext().splitlines() if _re.search("Address Error|Bus Error", l) and "8e21" not in l])
rnd = random.Random(a.seed)
try:
    e.boot_editor(False)
    check("viewer up", e.open_track("straight", a.level, ntr=0))
    if a.hill != "none":
        e.send(0x23); e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(0.4); e.list_goto(int(a.hill)); e.send(0x1c); e.wait(lambda: e.vu("lopen") == 0, 40); e.idle()
    nseg = e.vu("nseg"); log("segments", e.segs(), "barat", e.vl("barat"))
    for it in range(a.n):
        k = it % nseg
        e.seg_goto(k); e.idle()
        hit0 = r.w(EV + VAR["tdhit"]); N = e.vl("pos")
        e.send(0x19); t0 = time.time(); up = False
        while time.time() - t0 < 60:
            time.sleep(0.4)
            if bad(): break
            try:
                if r.w(EV + VAR["tdhit"]) > hit0 and r.b(0x1024) == 0 and r.b(VTD) == 0xff: up = True; break
            except Exception: pass
        if bad(): log(f"[{it}] CRASH during start from unit {N}: {bad()} bad lines"); break
        log(f"[{it}] drive from unit {N}: race up={up} $5ff8={r.w(0x5ff8)}")
        drv = rnd.choice([0, 0.5, 1, 2, 3]) 
        e.jpoke(rnd.choice([1, 1, 5, 9])); time.sleep(drv + 1.0); e.jpoke(0)
        if bad(): log(f"[{it}] CRASH while driving ($5ff8={r.w(0x5ff8)}): {bad()} bad lines"); break
        e.send(0x01)
        ok = e.wait(lambda: r.b(VTD) == 0 and e.vu("state") == 1 and e.vu("redraw") == 0 and r.b(0x1028) == 0, 60)
        log(f"[{it}] back={ok} bad={bad()}")
        if not ok: break
        e.idle()
    txt = [l for l in r.h._logtext().splitlines() if _re.search("Bus Error|Address Error", l)]
    for ln in txt[:8]: log("LOG:", ln)
    r.shot("end")
finally:
    e.close()
