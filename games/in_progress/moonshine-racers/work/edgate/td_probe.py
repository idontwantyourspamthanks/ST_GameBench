#!/usr/bin/env python3
"""exploration: boot to the editor, copy TRACK 04 (stock), go to a position, press P, watch the race"""
import argparse
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="td_probe"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--machine", default="ste"); ap.add_argument("--level", type=int, default=3)
ap.add_argument("--target", type=int, default=3000); ap.add_argument("--secs", type=int, default=20)
a = ap.parse_args()
e = Ed(a.tag, a.machine, 2048, a.build, CAMP / "c3.trk"); r = e.r
try:
    e.boot_editor(True)
    e.key(0x50, 3, 0.5); e.send(0x1c); time.sleep(1.0); e.key(0x50, a.level, 0.35); e.send(0x1c)
    check("viewer up", e.wait(lambda: e.vu("state") == 1, 60)); time.sleep(1.5); e.idle()
    r.shot("1_viewer")
    for _ in range(600):
        if e.vl("pos") >= a.target: break
        e.key(0x4d, 1, 0.12)
    log("cursor at", e.vl("pos"), "seg", e.vu("seg"))
    e.idle(); r.shot("2_cursor")
    n0 = len(r.h._logtext())
    e.send(0x19)
    t0 = time.time()
    for i in range(a.secs * 2):
        time.sleep(0.5)
        try:
            log(f"[{time.time()-t0:5.1f}] $5ff8={r.w(0x5ff8)} $1024={r.b(0x1024):#x} $1226={r.b(0x1226)} $102c={r.w(0x102c):#x} $23c0={r.l(0x23c0):#x} $10ce={r.l(0x10ce):#x} $10d2={r.w(0x10d2)} state={e.vu('state')} hit={r.w(0x140000+2326)}")
        except Exception as ex: log("ERR", ex)
        if i in (6, 12, 20): r.shot(f"3_race_{i}")
    log("Bus/Address error lines:", r.errlines())
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    e.close()
