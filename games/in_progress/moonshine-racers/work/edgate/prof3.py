#!/usr/bin/env python3
"""where does one preview step spend its cycles?  env3.sh python3 prof3.py --tag T [--lst L]: Hatari profiler over one step (bend key in the main view, then DOWN in the width list), buckets = nearest global label of the listing"""
import argparse, re, threading, bisect
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="prof3"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--lst", default="/tmp/msred3/ovl.lst"); ap.add_argument("--seg", type=int, default=150)
a = ap.parse_args()
syms = []
for l in open(a.lst):
    m = re.match(r"^(\w+)\s+A:([0-9A-F]{8})", l)
    if m and not m.group(1).startswith("."): syms.append((int(m.group(2), 16), m.group(1)))
syms.sort(); keys = [s[0] for s in syms]
def bucket(prof):
    d = {}
    for ad, cy in prof:
        i = bisect.bisect_right(keys, ad) - 1
        nm = syms[i][1] if 0 <= i and 0x130000 <= ad < 0x140000 else f"<${ad:x}>"
        if not (0x130000 <= ad < 0x140000): nm = "game/TOS (VBL, music, sync)" if ad < 0x100000 else nm
        d[nm] = d.get(nm, 0) + cy
    tot = sum(d.values())
    return tot, sorted(d.items(), key=lambda x: -x[1])
e = Ed(a.tag, "ste", 2048, a.build, CAMP / "c3.trk"); r = e.r; h = r.h
try:
    e.boot_editor(True)
    e.key(0x50, 3, 0.5); e.send(0x1c); time.sleep(1.0); e.key(0x50, 3, 0.35); e.send(0x1c)
    check("viewer up", e.wait(lambda: e.vu("state") == 1, 60)); time.sleep(1.5); e.idle()
    for _ in range(600):
        s = e.vu("seg")
        if s == a.seg: break
        e.key(0x4d if s < a.seg else 0x4b, 1, 0.1)
    e.idle()
    def run(name, trigger, vbls=90):
        out = {}
        t = threading.Thread(target=lambda: out.__setitem__("p", h.profile(vbls)))
        t.start(); time.sleep(1.2); trigger(); t.join()
        tot, rows = bucket(out["p"])
        log(f"PROFILE {name}: {tot} cycles over ~{vbls} VBL window ({tot / 160256:.1f} VBL of CPU); top buckets:")
        for nm, cy in rows[:22]: log(f"   {cy:9d}  {cy / 160256:5.1f} VBL  {nm}")
    run("main view bend '.'", lambda: e.send(0x34))
    e.idle()
    e.send(0x11); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(1.0); e.settle()
    run("width list DOWN (preview)", lambda: e.send(0x50))
    e.send(0x01)
finally:
    e.close()
