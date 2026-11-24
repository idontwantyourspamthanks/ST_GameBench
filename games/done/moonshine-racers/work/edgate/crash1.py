#!/usr/bin/env python3
"""Repro of the user's crash: PLAIN STRAIGHT -> H -> RISE BIG -> P (test drive).  work/edgate/envcrash.sh python3 work/edgate/crash1.py --tag T [--mem 2048] [--hill 3|none] [--camp]"""
import argparse
import ed2lib
from ed2lib import *
_Run = ed2lib.Run
ed2lib.Run = lambda *a, **k: _Run(*a, extra_args=["--alert-level", "fatal"], **k)
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="crash1"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--machine", default="ste")
ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--hill", default="3"); ap.add_argument("--camp", action="store_true"); ap.add_argument("--wait", type=int, default=40); ap.add_argument("--level", type=int, default=3); ap.add_argument("--drive", type=float, default=0); ap.add_argument("--seg", type=int, default=0); ap.add_argument("--obj", action="store_true"); ap.add_argument("--rand", type=int, default=0); ap.add_argument("--from1m", action="store_true"); ap.add_argument("--dump", action="store_true"); ap.add_argument("--pdelay", type=float, default=-1); ap.add_argument("--step", type=float, default=1.0)
a = ap.parse_args()
e = Ed(a.tag, a.machine, 1024 if a.from1m else a.mem, a.build, CAMP / "c3.trk" if a.camp else None); r = e.r
try:
    if a.from1m:
        ok = r.boot_title(); log("1 MB title:", ok, "$42e", hex(r.l(0x42e))); r.h.cmd(f"hatari-option --memsize {a.mem}"); time.sleep(6); log("after the switch: $42e", hex(r.l(0x42e)))
    e.boot_editor(a.camp)
    check("viewer up", e.open_track("straight", a.level, ntr=3 if a.camp else 0))
    log("segments", e.segs()[:4], "nobj", e.vu("nobj"), "barat", e.vl("barat"))
    r.shot("1_straight")
    if a.hill != "none":
        e.send(0x23); check("H list open", e.wait(lambda: e.vu("lopen") == 1, 25)); time.sleep(0.4)
        check("list_goto", e.list_goto(int(a.hill))); e.send(0x1c)
        if a.pdelay >= 0: time.sleep(a.pdelay)
        else: e.wait(lambda: e.vu("lopen") == 0, 40); e.idle()
        if a.pdelay < 0: log("segments after hill", e.segs()[:4]); r.shot("2_hill")
    if a.seg:
        check("seg_goto", e.seg_goto(a.seg))
    if a.obj:
        e.send(0x0f); check("object list", e.wait(lambda: e.vu("focus") == 1, 10)); e.idle()
        log("object", e.objs()[e.vu("obj")])
    if a.pdelay < 0: log("cursor unit", e.vl("pos"), "seg", e.vu("seg"))
    e.send(0x19); t0 = time.time(); r.shot("3_after_P_0")
    import re as _re0
    def bad():
        return len([l for l in r.h._logtext().splitlines() if _re0.search("Address Error|Bus Error", l) and "8e21" not in l])
    base = 0; seen = None
    while time.time() - t0 < a.wait:
        time.sleep(1.0)
        n = bad()
        if n > base and seen is None:
            seen = time.time() - t0; log(f"ERROR LINES appeared after {seen:.1f} s: {n}")
            break
    if a.dump:
        time.sleep(4); b = e.grab(0, 0x40000, "ramlow"); import shutil; shutil.copy(ED_TMP / f"{a.tag[:12]}_ramlow.bin", "/tmp/msrcrash/ram_race.bin"); log("dumped $0..$40000", len(b), "$5ff8", r.w(0x5ff8), "$10ce", hex(r.l(0x10ce)), "$10d8", hex(r.l(0x10d8)), "$10d2", r.w(0x10d2))
    if a.drive and seen is None:
        time.sleep(3); log("race up: $5ff8", r.w(0x5ff8), "$1024", hex(r.b(0x1024)), "ptr", hex(r.l(0x23c0)))
        e.jpoke(0x01); r.ff(True); t1 = time.time()
        import random; rnd = random.Random(a.rand)
        while time.time() - t1 < a.drive:
            if a.rand:
                for _ in range(4):
                    e.jpoke(rnd.choice([1, 1, 1, 5, 9, 2, 0x81, 0x85, 0x89, 4, 8])); time.sleep(0.25)
            else: time.sleep(a.step)
            if r.b(0x1028) == 0: log("race ended: $5ff8", r.w(0x5ff8), hex(r.b(0x1024))); break
            log(f"  driving: $5ff8={r.w(0x5ff8)} $1024={r.b(0x1024):#x} $1026={r.b(0x1026)} $1226={r.b(0x1226)} $10ce={r.l(0x10ce):#x} $10d8={r.l(0x10d8):#x} $1030={r.w(0x1030):#x} $130c={r.w(0x130c)} errlines={r.errlines()} bad={bad()}")
            if bad() > base: break
        r.ff(False); e.jpoke(0)
    log("errlines", r.errlines(), "race flag", hex(r.b(0x1028)), "$5ff8", r.w(0x5ff8), "$1024", hex(r.b(0x1024)))
    r.shot("4_after_P")
    txt = r.h._logtext(); import re as _re
    for ln in [l for l in txt.splitlines() if _re.search("Bus Error|Address Error", l)][:6]: log("LOG:", ln)
finally:
    e.close()
log("RESULT", a.tag, "FAILED" if FAILS else "ok", FAILS)
