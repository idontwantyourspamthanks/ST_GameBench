#!/usr/bin/env python3
"""Test drive on an object-zoo track (mkzoo.py): campaign of one track in the editor, P from segment SEG, drive with fast-forward, watch for Address / Bus Errors.
work/edgate/envcrash.sh python3 work/edgate/crash5.py --tag T --zoo zoo1 [--seg 0] [--drive 40] [--play]   (--play: PLAY THIS TRACK, a normal race, instead of the editor's test drive)"""
import argparse, re as _re
import ed2lib
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="crash5"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--machine", default="ste")
ap.add_argument("--zoo", default="zoo1"); ap.add_argument("--seg", type=int, default=0); ap.add_argument("--drive", type=float, default=40); ap.add_argument("--play", action="store_true")
a = ap.parse_args()
e = Ed(a.tag, a.machine, 2048, a.build, Path(__file__).resolve().parent / f"{a.zoo}.trk"); r = e.r
def bad():
    out = []
    for l in r.h._logtext().splitlines():
        if "Address Error" in l: out.append(l)
        elif "Bus Error" in l:
            m = _re.search(r"at address \$([0-9a-f]+)", l)
            if not m or (int(m.group(1), 16) & 0xffffff) < 0xff8000: out.append(l)
    return out
try:
    e.boot_editor(True, ntr=1)
    check("viewer up", e.open_track("camp", 0, ntr=1))
    log("segments", len(e.segs()), "objects", e.vu("nobj"), "barat", e.vl("barat"))
    if a.seg: check("seg_goto", e.seg_goto(a.seg))
    log("cursor unit", e.vl("pos"))
    hit0 = r.w(EV + VAR["tdhit"]); e.send(0x19); t0 = time.time()
    while time.time() - t0 < 60 and not bad():
        time.sleep(0.5)
        try:
            if r.w(EV + VAR["tdhit"]) > hit0 and r.b(0x1024) == 0 and r.b(0xb8e0e) == 0xff and r.w(0x5ff8) == e.vl("pos"): break
        except Exception: pass
    log("race up: $5ff8", r.w(0x5ff8), "bad", len(bad()))
    if not bad():
        e.jpoke(1); r.ff(True); t1 = time.time()
        while time.time() - t1 < a.drive:
            time.sleep(2.0)
            log(f"  driving: $5ff8={r.w(0x5ff8)} $1024={r.b(0x1024):#x} $1026={r.b(0x1026)} bad={len(bad())}")
            if bad() or r.b(0x1028) == 0: break
        r.ff(False); e.jpoke(0)
    for l in bad()[:6]: log("BAD:", l)
    log("race flag", hex(r.b(0x1028)), "$5ff8", r.w(0x5ff8)); r.shot("end")
finally:
    e.close()
log("RESULT", a.tag, "CRASH" if bad() else "no error")
