#!/usr/bin/env python3
"""Track editor milestone 2b gate: LIVE-PREVIEW SPEED and KEY QUEUE (HD build, one boot).
   work/edgate/env3.sh python3 work/edgate/ed3.py --tag T [--build DIR] [--lst LISTING] [--only timing]
One boot: campaign c3.trk -> TRACK EDITOR -> a copy of original track --level (default 4 = TRACK 04, as ed2.py) -> viewer.
  timing  : ms per step = VBL deltas of Hatari's frame counter (`e VBL` in breakpoint command files at the code points of the listing; 20 ms per VBL): a curve bend with `.` in the main view (cursor at segment 0 and at
            segment 150), the curve list (C, DOWN: live preview), the width list, the hill list.
  arrays  : after each class of edit the editor's per-unit arrays (height, left / right width, path points) are compared with a Python expansion of the segment list in RAM (msrtrack.expand_* and the path model of eg.py):
            incremental passes (masks, closed-form path blocks, width early stop) must equal a full expansion.
  burst   : 10 key presses sent back to back (no wait): 10 x `.` (curve +10), 10 x U (undo: back to the start value), 10 x RIGHT (cursor +10 segments), the curve list with 10 x DOWN (selection +10, the preview runs for the
            value the selection ends on), and 'C DOWN DOWN DOWN RETURN' typed without waiting."""
import argparse, re, math
from ed2lib import *

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="ed3"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--lst", default="/tmp/msred3/ovl.lst"); ap.add_argument("--level", type=int, default=3)
ap.add_argument("--only", default="")
a = ap.parse_args()
SYM = {}
LST = open(a.lst).read().splitlines()
for l in LST:
    m = re.match(r"^(\w+)\s+A:([0-9A-F]{8})", l)
    if m: SYM[m.group(1)] = int(m.group(2), 16)
def after_clr_busy():
    """address of the `clr.w vLBusy(a5)` that ends lpreview"""
    for l in LST:
        m = re.match(r"^00:([0-9A-F]{8}) \w+\s+\d+:\s+clr\.w\s+vLBusy\(a5\)", l)
        if m and int(m.group(1), 16) > SYM["lpreview"]: return int(m.group(1), 16)
NEW = "flush_pend" in SYM
e = Ed(a.tag, "ste", 2048, a.build, CAMP / "c3.trk"); r = e.r; h = r.h
VAR.update(lpend=256, lmsg=442, msel=112, lact=220)
EXP = {}
def vbl_arm(pcs):
    h.debug("b all", 0.3)
    f = h.R / "vbl.txt"; f.write_text("e VBL\n")
    for name, pc in pcs.items():
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}"); time.sleep(0.25)
    return len(h._logtext())
def vbl_hits(n0, pcs):
    t = h._logtext()[n0:]; out = []; cur = None
    byaddr = {f"pc = ${pc:x} :trace": n for n, pc in pcs.items()}
    for ln in t.splitlines():
        for k, n in byaddr.items():
            if k in ln: cur = n
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m and cur: out.append((cur, int(m.group(1)))); cur = None
    return out
def seg_goto(k):
    for _ in range(600):
        s = e.vu("seg")
        if s == k: return True
        e.key(0x4d if s < k else 0x4b, 1, 0.1)
    return e.vu("seg") == k
def settle_all(tmo=60):
    """no key waiting, nothing pending, nothing drawn: the editor is idle"""
    t0 = time.time(); ok = 0
    while time.time() - t0 < tmo:
        kq = (e.vu("kqh") == e.vu("kqt")) if NEW else True
        if kq and e.vu("redraw") == 0 and (e.vu("pend") == 0 if NEW else True) and e.vu("lbusy") == 0 and e.vu("lpend") == 0 and e.vu("dirty") == 0x7fff: ok += 1
        else: ok = 0
        if ok >= 3: return True
        time.sleep(0.25)
    return False

# ---- reference expansion of the segment list in RAM
def segs_ram():
    n = e.vu("nseg"); b = e.grab(EV + 0x3000, 12 * n, "seg")
    return [struct.unpack(">HHhhBB", b[12 * i:12 * i + 10]) for i in range(n)]
def path_fixed(curve, n):
    q = [round(32767 * math.sin(i * math.pi / 2048)) for i in range(1025)]
    sin = [0] * 5120
    for i in range(5120):
        j = i & 4095; neg = j >= 2048; j -= 2048 if neg else 0
        v = q[j] if j <= 1024 else q[2048 - j]
        sin[i] = -v if neg else v
    ax = ay = 0; pts = [(0, 0)]
    for k in range(n // 8):
        m = sum(curve[8 * k:8 * k + 8]) >> 3
        ixx = ((m * 17801) >> 14) & 4095
        ax += sin[ixx] << 3; ay -= sin[ixx + 1024] << 3
        pts.append((ax >> 17, ay >> 17))
    return pts
def verify_arrays(label):
    segs = segs_ram(); end = e.vl("end")
    cs = [[s[1], s[2]] for s in segs]; hs = [[s[1], s[3]] for s in segs]; ls = [[s[1], s[4]] for s in segs]; rs = [[s[1], s[5]] for s in segs]
    eh, _ = mt.expand_hill(hs, end); el = mt.expand_width(ls, end); er = mt.expand_width(rs, end); ec = mt.expand_curve(cs, end)
    gh, gl, gr = e.grab(EV + 0x10000, end, "h"), e.grab(EV + 0x18000, end, "wl"), e.grab(EV + 0x20000, end, "wr")
    pb = e.grab(EV + 0x28000, 4 * (end // 8 + 1), "pts")
    gp = [struct.unpack(">hh", pb[4 * i:4 * i + 4]) for i in range(end // 8 + 1)]
    ep = path_fixed(ec, end)
    dh, dl, dr, dp = (sum(x != y for x, y in zip(gh, eh)), sum(x != y for x, y in zip(gl, el)), sum(x != y for x, y in zip(gr, er)), sum(x != y for x, y in zip(gp, ep)))
    check(f"arrays == full reference expansion after {label} ({len(segs)} segments, extent {end})", dh == dl == dr == dp == 0 and list(gh) == eh, f"differing: height {dh} left {dl} right {dr} path {dp}")
def curve_of(k):
    return segs_ram()[k][2]

try:
    e.boot_editor(True)
    e.key(0x50, 3, 0.5); e.send(0x1c); time.sleep(1.0); e.key(0x50, a.level, 0.35); e.send(0x1c)
    check("viewer up", e.wait(lambda: e.vu("state") == 1, 60)); time.sleep(1.5); settle_all()
    if "timing" not in a.only: verify_arrays("loading TRACK %02d" % (a.level + 1))
    P1 = {"apply_try": SYM["apply_try"], "expand": SYM["expand_from"], "full_draw": SYM["full_draw"], "show": SYM["show"]}
    if NEW: P1["flush_pend"] = SYM["flush_pend"]
    # ---- timing: main view, bend keys
    log("TIMING (VBL = 20 ms; step = key accepted (apply_try) ... picture handed to the shifter (show))")
    res = {}
    for k in (0, 150):
        e.send(0x47); settle_all(); seg_goto(k); settle_all()
        for key, nm in ((0x34, "."), (0x33, ",")):
            n0 = vbl_arm(P1); e.send(key); settle_all(); time.sleep(0.5)
            hs = vbl_hits(n0, P1); d = {}
            for n, v in hs: d.setdefault(n, v)
            if "apply_try" in d and "show" in d:
                tot = d["show"] - d["apply_try"]; exp = d["full_draw"] - d["expand"] if "expand" in d else -1; dr = d["show"] - d["full_draw"]
                log(f"  bend '{nm}' at segment {k}: step {tot} VBL = {tot * 20} ms (recompute {exp} VBL, draw {dr} VBL)   raw {hs}")
                res[(k, nm)] = (tot, exp, dr)
            else: log(f"  bend '{nm}' at segment {k}: hits {hs}")
    EXP["bend"] = res
    # list preview: one DOWN in the curve list, width list, hill list at segment 150
    P2 = {"lpreview": SYM["lpreview"], "lp_end": after_clr_busy(), "expand": SYM["expand_from"], "full_draw": SYM["full_draw"]}
    seg_goto(150); settle_all()
    for key, nm, act in ((0x2e, "curve", 1), (0x11, "width L", 4), (0x23, "hill", 2)):
        e.send(key); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(1.0); e.settle()
        e.settle(); n0 = vbl_arm(P2); e.send(0x50); time.sleep(0.4); e.settle(); time.sleep(0.8)
        hs = vbl_hits(n0, P2); d = {}
        for n, v in hs: d.setdefault(n, v)
        if "lpreview" in d and "lp_end" in d: log(f"  {nm} list, DOWN: preview {d['lp_end'] - d['lpreview']} VBL = {(d['lp_end'] - d['lpreview']) * 20} ms (recompute {d['full_draw'] - d['expand']} VBL, draw {d['lp_end'] - d['full_draw']} VBL)   raw {hs}")
        else: log(f"  {nm} list: hits {hs}")
        e.send(0x01); e.wait(lambda: e.vu("lopen") == 0, 30); settle_all()
    h.debug("b all", 0.3)
    if "timing" in a.only: raise SystemExit
    # ---- arrays after each class of edit (keys, one at a time)
    seg_goto(60); settle_all()
    e.send(0x34); settle_all(); verify_arrays("a curve bend at segment 60 (path pass only)")
    e.send(0x16); settle_all(); verify_arrays("its undo")
    seg_goto(20); settle_all()
    e.send(0x11); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(1.0); e.settle(); e.list_goto(11); e.send(0x1c); e.wait(lambda: e.vu("lopen") == 0, 40); settle_all()
    verify_arrays("a left width pick at segment 20 (width pass, early stop)")
    seg_goto(40); settle_all()
    e.send(0x23); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(1.0); e.settle(); e.list_goto(3); e.send(0x1c); e.wait(lambda: e.vu("lopen") == 0, 40); settle_all()
    verify_arrays("a hill shape at segment 40 (all passes)")
    seg_goto(80); settle_all()
    e.send(0x26); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(1.0); e.settle(); e.list_goto(4); e.send(0x1c); e.wait(lambda: e.vu("lopen") == 0, 40); settle_all()
    verify_arrays("a length pick at segment 80")
    e.send(0x17); settle_all(); verify_arrays("an inserted segment copy")
    e.send(0x16); settle_all(); e.send(0x16); settle_all(); verify_arrays("two undos")
    # ---- bursts
    log("BURSTS (every key sent back to back, no wait between)")
    seg_goto(150); settle_all()
    c0 = curve_of(150); key, n_exp = (0x34, c0 + 10) if c0 <= 0 else (0x33, c0 - 10)
    P3 = {"apply_try": SYM["apply_try"]}
    if NEW: P3["flush_pend"] = SYM["flush_pend"]; P3["xp_path"] = SYM["xp_path"]
    else: P3["expand"] = SYM["expand_from"]
    n0 = vbl_arm(P3)
    for _ in range(10): h.cmd(f"hatari-event keypress 0x{key:02x}"); time.sleep(0.01)
    settle_all(); time.sleep(0.5)
    hs = vbl_hits(n0, P3); cnt = {}
    for n, v in hs: cnt[n] = cnt.get(n, 0) + 1
    c1 = curve_of(150)
    check(f"burst of 10 bends ('{'.' if key == 0x34 else ','}'): curve of segment 150 {c0} -> {n_exp}", c1 == n_exp, f"got {c1}; hits {cnt}")
    log(f"  breakpoint hits: {cnt}  (apply_try = steps applied; the recompute runs {'once' if NEW else 'per step'})   VBL of the hits {hs[:3]} ... {hs[-2:]}")
    check("10 steps applied (apply_try hits == 10)", cnt.get("apply_try", 0) == 10, f"{cnt.get('apply_try', 0)}")
    verify_arrays("the burst of 10 bends")
    h.debug("b all", 0.3)
    for _ in range(10): h.cmd("hatari-event keypress 0x16"); time.sleep(0.01)
    settle_all(); time.sleep(0.3)
    c2 = curve_of(150)
    check(f"burst of 10 undos (U): curve back to {c0}", c2 == c0, f"got {c2}")
    verify_arrays("the burst of 10 undos")
    s0 = e.vu("seg")
    for _ in range(10): h.cmd("hatari-event keypress 0x4d"); time.sleep(0.01)
    settle_all(); time.sleep(0.3)
    s1 = e.vu("seg")
    check(f"burst of 10 RIGHT: cursor segment {s0} -> {s0 + 10}", s1 == s0 + 10, f"got {s1}")
    # the curve list with a burst of DOWN
    e.send(0x2e); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(1.0); e.settle()
    sel0, cnt_items = e.v("lsel"), e.vu("lcnt") + 1
    P4 = {"lpreview": SYM["lpreview"]}
    n0 = vbl_arm(P4)
    for _ in range(10): h.cmd("hatari-event keypress 0x50"); time.sleep(0.01)
    time.sleep(0.5); e.settle(); time.sleep(1.0)
    hs = vbl_hits(n0, P4)
    sel1 = e.v("lsel")
    check(f"burst of 10 DOWN in the curve list: selection {sel0} -> {(sel0 + 10) % cnt_items} (of {cnt_items} items), the preview ran for the value it ended on", sel1 == (sel0 + 10) % cnt_items and len(hs) >= 1, f"got {sel1}; lpreview hits {len(hs)}: {hs}")
    log(f"  list burst: previews run {len(hs)}x for 10 selection moves")
    e.send(0x01); e.wait(lambda: e.vu("lopen") == 0, 30); settle_all()
    verify_arrays("the cancelled curve list")
    # typed ahead: C DOWN DOWN DOWN RETURN
    c3 = curve_of(e.vu("seg")); sg = e.vu("seg")
    for sc in (0x2e, 0x50, 0x50, 0x50, 0x1c): h.cmd(f"hatari-event keypress 0x{sc:02x}"); time.sleep(0.01)
    time.sleep(1.0); settle_all(); time.sleep(1.0); settle_all()
    c4 = curve_of(sg)
    check(f"typed ahead 'C DOWN DOWN DOWN RETURN' at segment {sg}: curve {c3} -> {c3 + 3}", c4 == c3 + 3 and e.vu("lopen") == 0, f"got {c4}, list open {e.vu('lopen')}")
    verify_arrays("the typed-ahead list pick")
except SystemExit:
    pass
except Exception:
    import traceback; log("EXC", traceback.format_exc()); FAILS.append("exception")
finally:
    e.close()
log(f"RESULT {a.tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
