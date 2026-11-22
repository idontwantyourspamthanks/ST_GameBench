#!/usr/bin/env python3
"""Live-preview speed gate: ms per step (VBL deltas of Hatari's own frame counter, `e VBL` in breakpoint command files at the code points; 20 ms per VBL) and key bursts.
   env3.sh python3 speed.py --tag T [--burst] ; addresses come from /tmp/msred4/ovl.lst (symbols of the overlay assembled by symlst.py)"""
import argparse, re
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="speed"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--level", type=int, default=3)
ap.add_argument("--lst", default="/tmp/msred4/ovl.lst"); ap.add_argument("--pcs", default="")
a = ap.parse_args()
SYM = {}
for l in open(a.lst):
    m = re.match(r"^(\w+)\s+A:([0-9A-F]{8})", l)
    if m: SYM[m.group(1)] = int(m.group(2), 16)
e = Ed(a.tag, "ste", 2048, a.build, CAMP / "c3.trk"); r = e.r; h = r.h
def arm(pcs):
    h.debug("b all", 0.3)
    f = h.R / "vbl.txt"; f.write_text("e VBL\n")
    for name, pc in pcs.items():
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}"); time.sleep(0.25)
    return len(h._logtext())
def hits(n0, pcs):
    """-> [(name, vbl)] in order"""
    t = h._logtext()[n0:]; out = []; cur = None
    byaddr = {f"pc = ${pc:x} :trace": n for n, pc in pcs.items()}
    for ln in t.splitlines():
        for k, n in byaddr.items():
            if k in ln: cur = n
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m and cur: out.append((cur, int(m.group(1)))); cur = None
    return out
def wait_hits(n0, pcs, want, tmo=30):
    t0 = time.time()
    while time.time() - t0 < tmo:
        hs = hits(n0, pcs)
        if len(hs) >= want: return hs
        time.sleep(0.4)
    return hits(n0, pcs)
def goto_seg(k):
    for _ in range(400):
        s = e.vu("seg")
        if s == k: return
        e.key(0x4d if s < k else 0x4b, 1, 0.12)
    raise RuntimeError("goto_seg")
try:
    e.boot_editor(True)
    e.key(0x50, 3, 0.5); e.send(0x1c); time.sleep(1.0); e.key(0x50, a.level, 0.35); e.send(0x1c)
    check("viewer up", e.wait(lambda: e.vu("state") == 1, 60)); time.sleep(1.5); e.idle()
    P1 = {"apply_try": SYM["apply_try"], "full_draw": SYM["full_draw"], "full_draw_end": SYM["show"], "expand": SYM["expand_from"], "draw_all": SYM["draw_all"], "draw_hi": SYM["draw_hi"]}
    # main view, bend keys: apply_try (start) ... show (end of the redraw)
    for k in (0, 150):
        e.send(0x47); e.idle(); goto_seg(k); e.idle()
        for key, nm in ((0x34, "."), (0x33, ",")):
            n0 = arm(P1); e.send(key); e.idle()
            hs = wait_hits(n0, P1, 4, 10); log(f"main view seg {k} key '{nm}': {hs}")
            d = {}
            for n, v in hs: d.setdefault(n, v)
            if "apply_try" in d and "full_draw" in d: log(f"  RESULT seg {k} '{nm}': apply_try -> full_draw {d['full_draw'] - d['apply_try']} VBL, expand -> draw_all {d.get('draw_all', 0) - d.get('expand', 0)} VBL")
    # list preview: C opens the curve list, DOWN moves the selection
    P2 = {"lpreview": SYM["lpreview"], "lp_end": SYM["lpreview"] + 0x3e, "expand": SYM["expand_from"], "draw_all": SYM["draw_all"]}
    e.send(0x47); e.idle(); goto_seg(150); e.idle()
    e.send(0x2e); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(1.5); e.settle()
    n0 = arm(P2)
    for i in range(3):
        e.send(0x50); time.sleep(2.5); e.settle()
    hs = hits(n0, P2); log(f"list preview (3 DOWN): {hs}")
    e.send(0x01); e.wait(lambda: e.vu("lopen") == 0, 30)
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    e.close()
