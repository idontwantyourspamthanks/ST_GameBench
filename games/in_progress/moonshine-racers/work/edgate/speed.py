#!/usr/bin/env python3
"""Tile-grid editor SPEED and KEY QUEUE gate (HD build, one boot: campaign c3.trk -> TRACK EDITOR -> a copy of original track --level).
   env7.sh python3 speed.py [--tag T] [--machine ste] [--level 3]
 timing: breakpoints at the code points (addresses from a listing of the source, ed2lib.symbols) print Hatari's VBL and CycleCounter: ms = CPU cycles between the routine that handles the
         key (seg_move / apply_try / lpreview) and the end of the redraw (the entry of draw_keys = the last call of draw_view; lpreview: its last instruction), at 8,021,248 cycles per second
         (the key itself waits for the editor's poll, once per frame = up to 20 ms more).  Cases: one segment (RIGHT), into the next grid row, one row (DOWN), a row move that scrolls the
         grid (all 128 tiles drawn), a bend key, a list preview.
 burst : keys typed back to back (no wait): 10 x RIGHT (cursor +10), 6 x `.` then 6 x `,` (12 applied steps, the curve back where it was), 10 x U (10 undos), 10 x DOWN in the curve list
         (selection +10), `C DOWN DOWN DOWN RETURN` typed ahead (the curve three items on)."""
import argparse
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="speed"); ap.add_argument("--build", default=os.environ.get("ED_BUILD", "/tmp/msred7/hd")); ap.add_argument("--level", type=int, default=3)
ap.add_argument("--machine", default="ste")
a = ap.parse_args()
SYM = symbols()
LST = (ED_TMP / "ovl.lst").read_text().splitlines()
def lp_end():
    """address of the `clr.w vLBusy(a5)` that ends lpreview"""
    for l in LST:
        m = re.match(r"^00:([0-9A-F]{8}) \w+\s+\d+:\s+clr\.w\s+vLBusy\(a5\)", l)
        if m and int(m.group(1), 16) > SYM["lpreview"]: return int(m.group(1), 16)
e = Ed(a.tag, a.machine, 2048, a.build, CAMP / "c3.trk"); r = e.r; h = r.h
HZ = 8021248

def arm(pcs):
    h.debug("b all", 0.3)
    f = h.R / "vc.txt"; f.write_text("e VBL\ne CycleCounter\n")
    for name, pc in pcs.items():
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}"); time.sleep(0.25)
    return len(h._logtext())
def hits(n0, pcs):
    """-> [(name, vbl, cycles)] in order"""
    out = []; cur = None; vals = []
    byaddr = {f"pc = ${pc:x} :trace": n for n, pc in pcs.items()}
    for ln in h._logtext()[n0:].splitlines():
        for k, n in byaddr.items():
            if k in ln and "matched" not in ln and "Removed" not in ln: cur = n; vals = []
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m and cur:
            vals.append(int(m.group(1)))
            if len(vals) == 2: out.append((cur, vals[0], vals[1])); cur = None
    return out
def measure(label, pcs, first, last, act, n=1):
    """ms from the first hit of `first` to the last hit of `last` after act()"""
    e.idle(); n0 = arm(pcs); act(); time.sleep(0.6); e.idle(); time.sleep(0.3)
    hs = hits(n0, pcs); h.debug("b all", 0.3)
    a_ = [x for x in hs if x[0] == first]; b_ = [x for x in hs if x[0] == last]
    if not a_ or not b_:
        check(f"timing {label}: code points hit", False, f"{hs}"); return None
    cyc = (b_[-1][2] - a_[0][2]) & 0xffffffff; ms = cyc * 1000 / HZ; vb = b_[-1][1] - a_[0][1]
    cnt = {k: sum(1 for x in hs if x[0] == k) for k in pcs}
    log(f"TIMING {label}: {ms:.1f} ms ({cyc} cycles, {vb} VBL boundaries crossed) from {first} to {last}; hits {cnt}")
    return ms

try:
    e.boot_editor(True)
    check("viewer up", e.open_track("stock", a.level))
    P = {"seg_move": SYM["seg_move"], "draw_view": SYM["draw_view"], "draw_keys": SYM["draw_keys"], "tile_draw": SYM["tile_draw"], "tiles_calc": SYM["tiles_calc"], "apply_try": SYM["apply_try"]}
    res = {}
    e.seg_goto(2)
    res["step"] = measure("one segment (RIGHT, same row)", P, "seg_move", "draw_keys", lambda: e.send(0x4d))
    e.seg_goto(15)
    res["step_row_edge"] = measure("one segment into the next grid row (RIGHT 16 -> 17: the row labels change)", P, "seg_move", "draw_keys", lambda: e.send(0x4d))
    e.seg_goto(20)
    res["row"] = measure("one row (DOWN, no scroll)", P, "seg_move", "draw_keys", lambda: e.send(0x50))
    e.seg_goto(100); f0 = e.vu("first")
    res["row_scroll"] = measure("one row that scrolls the grid (DOWN on row 7 of 8)", P, "seg_move", "draw_keys", lambda: e.send(0x50))
    check("the grid scrolled by one row", e.vu("first") == f0 + 16, f"first {f0} -> {e.vu('first')}")
    e.seg_goto(150)
    res["bend"] = measure("bend key `.` at segment 151 (apply, history, tile words of 313 segments, redraw)", P, "apply_try", "draw_keys", lambda: e.send(0x34))
    e.send(0x33); e.idle()
    P2 = {"lpreview": SYM["lpreview"], "lp_end": lp_end(), "tile_draw": SYM["tile_draw"]}
    e.send(0x2e); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(0.6); e.settle()
    n0 = arm(P2); e.send(0x50); time.sleep(0.8); e.settle(); hs = hits(n0, P2); h.debug("b all", 0.3)
    a_ = [x for x in hs if x[0] == "lpreview"]; b_ = [x for x in hs if x[0] == "lp_end"]
    if a_ and b_:
        res["list"] = ((b_[-1][2] - a_[0][2]) & 0xffffffff) * 1000 / HZ
        log(f"TIMING curve list, DOWN (live preview: apply, tile words, grid, panel): {res['list']:.1f} ms; tiles drawn {sum(1 for x in hs if x[0] == 'tile_draw')}")
    e.send(0x01); e.wait(lambda: e.vu("lopen") == 0, 30); e.idle()
    ok = all(res.get(k) is not None for k in ("step", "step_row_edge", "row", "row_scroll", "bend", "list"))
    check("timing: every case measured", ok, f"{res}")
    if ok:
        log("RESULT ms: " + ", ".join(f"{k} {v:.0f}" for k, v in res.items()))
        check("a cursor step and a row move finish within 3 frames (60 ms), a scrolling row move and a bend within 0.4 s", res["step"] <= 60 and res["row"] <= 60 and res["row_scroll"] <= 400 and res["bend"] <= 400, f"{res}")
    # ---- bursts (typed back to back)
    e.seg_goto(40); s0 = e.vu("seg"); n0 = arm({"draw_view": SYM["draw_view"]})
    e.key(0x4d, 10, 0.02); time.sleep(1.0); e.idle(); nd = len(hits(n0, {"draw_view": SYM["draw_view"]})); h.debug("b all", 0.3)
    check(f"burst: 10 x RIGHT typed back to back = the cursor 10 segments on ({s0} -> {e.vu('seg')}); redraws {nd}", e.vu("seg") == s0 + 10)
    k = next(i for i, s in enumerate(e.segs()) if 60 <= i < 200 and -3 <= s[2] <= 3); e.seg_goto(k); c0 = e.segs()[k][2]; hc0 = e.vl("hcur")
    PB = {"apply_try": SYM["apply_try"], "tiles_calc": SYM["tiles_calc"], "draw_view": SYM["draw_view"]}
    n0 = arm(PB); e.key(0x34, 6, 0.02); e.key(0x33, 6, 0.02); time.sleep(1.5); e.idle(); hs = hits(n0, PB); h.debug("b all", 0.3)
    cnt = {k_: sum(1 for x in hs if x[0] == k_) for k_ in PB}
    check(f"burst: 6 x `.` + 6 x `,` at segment {k}: 12 applied steps (apply_try {cnt['apply_try']}), the curve back at {c0}, recomputes {cnt['tiles_calc']}, redraws {cnt['draw_view']}", cnt["apply_try"] == 12 and e.segs()[k][2] == c0 and cnt["tiles_calc"] < 12)
    e.key(0x16, 10, 0.02); time.sleep(1.5); e.idle()
    check("burst: 10 x U typed back to back = 10 undos (the curve is where it was after the first two `.`)", e.segs()[k][2] == c0 + 2, f"{e.segs()[k][2]} vs {c0 + 2}")
    e.key(0x16, 2, 0.02); time.sleep(0.8); e.idle()
    check("two more undos: the curve and the history entry of before the burst", e.segs()[k][2] == c0 and e.vl("hcur") == hc0, f"{e.segs()[k][2]} hcur {e.vl('hcur'):#x} vs {hc0:#x}")
    e.seg_goto(k); e.send(0x2e); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(0.6); e.settle(); l0 = e.v("lsel")
    n0 = arm({"lpreview": SYM["lpreview"]}); e.key(0x50, 10, 0.02); time.sleep(1.5); e.settle(); npv = len(hits(n0, {"lpreview": SYM["lpreview"]})); h.debug("b all", 0.3)
    cnt_ = e.vu("lcnt") + 1
    check(f"burst: 10 x DOWN in the curve list = the selection 10 items on ({l0} -> {e.v('lsel')}); previews {npv}", e.v("lsel") == (l0 + 10) % cnt_ and npv < 10)
    e.send(0x01); e.wait(lambda: e.vu("lopen") == 0, 30); e.idle()
    check("Esc: the curve is unchanged", e.segs()[k][2] == c0)
    for sc in (0x2e, 0x50, 0x50, 0x50, 0x1c): e.send(sc); time.sleep(0.02)
    time.sleep(2.0); e.wait(lambda: e.vu("lopen") == 0, 30); e.idle()
    check(f"typed ahead `C DOWN DOWN DOWN RETURN`: the curve of segment {k} is three items on ({c0} -> {e.segs()[k][2]})", e.segs()[k][2] == c0 + 3)
    log(f"Bus/Address error lines in the Hatari log: {r.errlines()}")
except Exception:
    import traceback; log("EXCEPTION", traceback.format_exc()); FAILS.append("exception")
finally:
    e.close()
log(f"RESULT {a.tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
