#!/usr/bin/env python3
"""Track editor EDITING gate (tile-grid editor, design section 15), HD build.  One boot: campaign (c3.trk, or none) -> TRACK EDITOR -> a copy of an original track / a plain straight -> an edit
script through the UI (keys and joystick: grid cursor, lists with live preview, the object list of a segment, MOVE, menu, Return repeat, undo / redo, refused edits) mirrored by ed2model.py ->
leave (the store is rebuilt) -> block == model, msrtrack.py validate -> re-enter -> PLAY THIS TRACK -> a normal race on it driven to the BAR.  After every group: segment list, object list,
tile words and extent in RAM == the model.
  work/edgate/env8.sh python3 work/edgate/ed2.py --kind stock|straight --machine ste|megaste|st --mem 2048 [--quick] [--tag X]"""
import argparse
from ed2lib import *
import ed2model as em
from PIL import Image, ImageChops

ap = argparse.ArgumentParser()
ap.add_argument("--kind", default="stock"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--quick", action="store_true"); ap.add_argument("--tag"); ap.add_argument("--build", default=os.environ.get("ED_BUILD", "/tmp/msred8/hd")); ap.add_argument("--norace", action="store_true")
ap.add_argument("--level", type=int, default=3)
a = ap.parse_args()
short = f"{ {'ste': 'ste', 'megaste': 'mste', 'st': 'st'}[a.machine] }{a.mem // 1024}m"
tag = a.tag or f"ed2_{a.kind}_{short}"
camp = CAMP / "c3.trk" if a.kind == "stock" else None
e = Ed(tag, a.machine, a.mem, a.build, camp); r = e.r
ms2 = mt.read_ms2()
t0_ = time.time()
msgtext = e.msgtext

def adj(n):
    """exact adjust with LEFT / RIGHT: one key, wait for the value to move and the preview to finish"""
    for _ in range(abs(n)):
        v0 = e.v("lval"); e.send(0x4d if n > 0 else 0x4b); e.wait(lambda: e.v("lval") != v0, 6, 0.15); time.sleep(0.2); e.settle()

class Drv:
    def __init__(s, model):
        s.m = model; s.n = 0; s.log = []
    # ---- navigation
    def goto_seg(s, k):
        assert k <= s.m.seg_last(), f"segment {k} is beyond the race (last {s.m.seg_last()})"
        assert e.seg_goto(k), f"goto_seg {k}: at {e.vu('seg')} focus {e.vu('focus')}"
        assert e.vl("pos") == s.m.segs[k][0], f"cursor unit {e.vl('pos')} != the segment's start {s.m.segs[k][0]}"
    def goto_obj(s, j):
        """the object list of the segment that holds object j, then DOWN to it"""
        k = s.m.seg_of(s.m.objs[j][0]); s.goto_seg(k)
        e.send(0x0f); assert e.wait(lambda: e.vu("focus") == 1, 10), "Tab: the object list did not take the cursor"
        of = e.vu("of"); assert of == s.m.seg_objs(k)[0] and e.vu("ocnt") == len(s.m.seg_objs(k)), f"objects of segment {k}: first {of} count {e.vu('ocnt')} vs model {s.m.seg_objs(k)}"
        e.key(0x50, j - of, 0.06); e.idle()
        assert e.vu("obj") == j, f"goto_obj {j}: at {e.vu('obj')}"
    # ---- lists
    def listpick(s, key, idx, adjust=0, how="key"):
        e.send(key); assert e.wait(lambda: e.vu("lopen") == 1, 25), "list did not open"; time.sleep(0.4)
        if idx is not None: assert e.list_goto(idx), f"list_goto {idx}: at {e.v('lsel')}"
        adj(adjust); e.settle(); time.sleep(0.2)
        val = e.v("lval"); bad = e.vu("lbad")
        if how == "joy": e.fire()
        else: e.send(0x1c)
        if bad:
            time.sleep(1.5); return val, True
        assert e.wait(lambda: e.vu("lopen") == 0, 40), "list did not close"; e.idle()
        return val, False
    def menu(s, idx):
        e.fire(); assert e.wait(lambda: e.vu("state") == 2, 20); time.sleep(0.5)
        for _ in range(40):
            if e.vu("msel") == idx: break
            e.joy(0x02 if e.vu("msel") < idx else 0x01, 0.15); time.sleep(0.15)
        assert e.vu("msel") == idx, f"menu at {e.vu('msel')}"
        r.poke(0x6105, 0x80); time.sleep(0.2); r.poke(0x6105, 0)
        assert e.wait(lambda: e.vu("state") == 1, 40); e.idle()
    # ---- one edit: UI, then the model
    def note(s, what, err=None):
        s.n += 1; s.log.append(what); log(f"[{s.n:3d}] {what}" + (f"  -> refused {err}" if err else ""))
    def curve(s, k, v, how="key"):
        s.goto_seg(k); val, bad = s.listpick(0x2e, v + 9, how=how); assert not bad
        s.note(f"curve seg {k} = {val}"); s.m.set_curve(k, val)
    def hill(s, k, shape, how="key"):
        s.goto_seg(k); val, bad = s.listpick(0x23, shape, how=how)
        err = s.m.hill_shape(k, val); s.note(f"hill seg {k} shape {val}", err)
    def raw(s, k, idx, adjust=0):
        s.goto_seg(k); e.send(0x23); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(0.4); assert e.list_goto(13); e.send(0x1c)
        assert e.wait(lambda: e.vu("lopen") == 1 and e.vu("lact") == 8 and e.vu("lpend") == 0, 40); time.sleep(0.8)        # the exact list opens by itself
        assert e.list_goto(idx)
        adj(adjust); e.settle(); time.sleep(0.2)
        val = e.v("lval"); bad = e.vu("lbad"); e.send(0x1c)
        if bad: time.sleep(1.5); s.note(f"raw accel seg {k} = {val}", "E-HILL/E-RANGE"); return True
        e.wait(lambda: e.vu("lopen") == 0, 40); e.idle()
        err = s.m.set_raw(k, val); s.note(f"raw accel seg {k} = {val}", err); return False
    def length(s, k, idx, adjust=0, how="key"):
        s.goto_seg(k); val, bad = s.listpick(0x26, idx, adjust, how)
        err = s.m.set_len(k, val); s.note(f"length seg {k} = {val}", err)
    def width(s, k, side, idx, adjust=0):
        s.goto_seg(k); val, bad = s.listpick(0x11 if side == "L" else 0x12, idx, adjust)
        err = (s.m.set_wl if side == "L" else s.m.set_wr)(k, val); s.note(f"width {side} seg {k} = {val}", err)
    def repeat(s, k, what, fn):
        """Return = the last pick again at the cursor"""
        s.goto_seg(k); e.send(0x1c); e.idle(); err = fn(); s.note(f"Return = repeat {what} at seg {k}", err)
    def copy(s, k):
        s.goto_seg(k); e.send(0x17); e.idle(); err = s.m.seg_copy(k); s.note(f"insert copy of seg {k}", err)
        if not err: check_cursor(f"after the copy the cursor is on the copy ({k + 1})", k + 1)
    def delete(s, k):
        s.goto_seg(k); e.send(0x53); e.idle(); err = s.m.seg_del(k); s.note(f"delete seg {k}", err)
    def merge(s, k):
        s.goto_seg(k); e.send(0x32); e.idle(); err = s.m.seg_merge(k); s.note(f"merge seg {k} with the next", err)
    def split(s, k):
        s.goto_seg(k); L = s.m.segs[k][1]; e.send(0x1f); e.idle(); err = s.m.seg_split(k); s.note(f"split seg {k} (length {L}) in half", err)
        if not err: check_cursor(f"after the split the cursor stays on the first half ({k})", k)
    def objtype(s, j, idx):
        s.goto_obj(j); val, bad = s.listpick(0x14, idx); err = s.m.obj_type(j, val); s.note(f"object {j} type {val}", err)
    def objside(s, j, idx, adjust=0):
        s.goto_obj(j); val, bad = s.listpick(0x1f, idx, adjust); err = s.m.obj_side(j, val); s.note(f"object {j} side {val}", err)
    def objadd_grid(s, k):
        """O with the grid cursor on segment k: the first free unit from its middle"""
        s.goto_seg(k); e.send(0x18); e.idle(); err = s.m.obj_add(k); j = e.vu("obj")
        s.note(f"O = add an object to seg {k}: unit {s.m.objs[j][0] if not err else '-'}", err)
        if not err: check(f"the new object ({j}) is selected in the list of segment {k}", e.vu("focus") == 1 and e.vu("seg") == k and j in s.m.seg_objs(k) and s.m.objs[j][1] != s.m.bar_t, f"focus {e.vu('focus')} seg {e.vu('seg')} obj {j}")
        return j
    def objadd_list(s, j):
        """I with object j selected in the list: the first free unit behind it"""
        k = s.m.seg_of(s.m.objs[j][0]); s.goto_obj(j); e.send(0x17); e.idle(); err = s.m.obj_add(k, after=j); j2 = e.vu("obj")
        s.note(f"I = add an object behind object {j} (seg {k}): unit {s.m.objs[j2][0] if not err else '-'}", err)
        return j2
    def objdel(s, j):
        s.goto_obj(j); e.send(0x53); e.idle(); err = s.m.obj_del(j); s.note(f"delete object {j}", err)
    def objmove(s, j, steps):
        """M, then LEFT / RIGHT (10 units; with the joystick's fire held 1 unit) and UP / DOWN (the previous / next segment), Return = keep"""
        s.goto_obj(j); at0 = s.m.objs[j][0]; e.send(0x32); assert e.wait(lambda: e.vu("mode") == 1, 20); time.sleep(0.3)
        for st in steps:
            if st[0] == "lr" and st[2] == 10: e.send(0x4d if st[1] > 0 else 0x4b)
            elif st[0] == "lr":
                e.jpoke(0x80); time.sleep(0.15); e.jpoke(0x80 | (8 if st[1] > 0 else 4)); time.sleep(0.06); e.jpoke(0x80); time.sleep(0.15); e.jpoke(0); time.sleep(0.2)
            else: e.send(0x50 if st[1] > 0 else 0x48)
            time.sleep(0.15); e.idle()
        e.send(0x1c); assert e.wait(lambda: e.vu("mode") == 0, 20); e.idle()
        j2 = s.m.obj_move(j, steps); s.note(f"move object {j} (unit {at0}) by {steps}: unit {s.m.objs[j2][0]}, now object {j2} of seg {s.m.seg_of(s.m.objs[j2][0])}")
        check(f"after the move the cursor follows the object (object {j2}, its segment)", e.vu("obj") == j2 and e.vu("seg") == s.m.seg_of(s.m.objs[j2][0]) and e.vu("focus") == 1, f"obj {e.vu('obj')} seg {e.vu('seg')} focus {e.vu('focus')}")
        return j2
    def barhere(s, k):
        s.goto_seg(k); s.menu(10); err = s.m.bar_here(k); s.note(f"PUT THE BAR HERE (menu) at seg {k}: unit {s.m.bar_at()}", err)
    def undo(s):
        e.send(0x16); e.idle(); err = s.m.undo(); s.note("undo", err)
    def redo(s):
        if e.vu("focus"): e.send(0x0f); e.idle()
        s.menu(12); err = s.m.redo(); s.note("redo (menu)", err)
    def verify(s, name):
        e.idle(); sg, ob, tl = e.segs(), e.objs(), e.tiles()
        msg = [s_[:6] for s_ in s.m.segs] == [x[:6] for x in sg] and [[o[0], o[1], o[2]] for o in ob] == [o[:3] for o in s.m.objs] and [o[3] for o in ob] == [1 if o_[1] == s.m.bar_t else 0 for o_ in s.m.objs]
        d = ""
        if not msg:
            bad = [i for i, (x, y) in enumerate(zip(sg, s.m.segs)) if list(x[:6]) != list(y[:6])][:3]
            bo = [i for i, (x, y) in enumerate(zip(ob, s.m.objs)) if list(x[:3]) != list(y[:3])][:3]
            d = f"nseg {len(sg)} vs {len(s.m.segs)}; first diffs {[(i, sg[i], s.m.segs[i]) for i in bad]}; nobj {len(ob)} vs {len(s.m.objs)}; first object diffs {[(i, ob[i], s.m.objs[i]) for i in bo]}"
        check(f"{name}: segment and object lists in RAM == the model ({len(sg)} segments, {len(ob)} objects, after {s.n} edits)", msg, d)
        mt_ = s.m.tiles(); tok = tl == mt_ and e.vl("end") == s.m.end()
        check(f"{name}: tile words in RAM == the model's ({sum(1 for w in mt_ if not w & 0x8000)} tiles), extent {s.m.end()}", tok,
              "" if tok else f"end {e.vl('end')} vs {s.m.end()}; first diffs {[(i, hex(x), hex(y)) for i, (x, y) in enumerate(zip(tl, mt_)) if x != y][:4]}")
        return msg and tok

def check_cursor(name, k):
    check(name, e.vu("seg") == k and e.vu("focus") == 0, f"seg {e.vu('seg')} focus {e.vu('focus')}")

def norm(segs):
    out = []
    for x in segs:
        if out and out[-1][2:6] == x[2:6]: out[-1][1] += x[1]
        else: out.append(list(x))
    return out

def run_script(D, kind):
    M = D.m
    # ---- 5 splits (S = in half)
    for k in (0, 1, 3, 5, 7): D.split(k)
    D.verify("after 5 splits")
    # ---- 6 curves (lists with live preview; one accepted with the joystick), then Return = the same value again on another segment
    for k, v, how in ((6, 8, "key"), (5, -6, "key"), (4, 10, "joy"), (3, -9, "key"), (2, 4, "key"), (1, -3, "key")):
        D.curve(k, v, how)
    v = M.segs[1][2]; D.repeat(8, f"curve {v}", lambda: M.set_curve(8, v))
    D.verify("after 7 curve edits")
    # ---- hills (highest segment first: the pieces a shape makes shift only the segments behind it): RISE MEDIUM / CREST SMALL / DIP BIG / DROP SMALL shapes, a raw accel + Return
    for k, sh in ((7, 4), (5, 12), (3, 7), (1, 2)):
        D.hill(k, sh, "joy" if sh == 4 else "key")
    D.raw(0, 5, 3)                                                  # -100 + 3 exact steps = -97
    v = e.v("lval"); D.repeat(2, f"raw accel {v}", lambda: M.set_raw(2, v))
    D.verify("after 6 hill edits")
    # ---- lengths (presets, an exact +3, one long segment for the E-HILL test below), highest first
    ks = [k for k in range(len(M.segs) - 1) if M.segs[k][1] >= 20 and M.segs[k][3] == 0][:12]
    sel = [ks[i] for i in (8, 6, 4, 3, 1)]
    for n, k in enumerate(sel):
        D.length(k, (5, 6, 4, 14, 3)[n], adjust=3 if n == 0 else 0, how="joy" if n == 2 else "key")
    D.verify("after 5 length edits")
    # ---- widths: left / right presets and exact values
    for n, (k, side, idx, adj_) in enumerate(((1, "L", 8, 0), (2, "R", 2, 0), (3, "L", 12, 2), (4, "R", 10, -1), (5, "L", 1, 0))):
        D.width(k, side, idx, adj_)
    D.verify("after 5 width edits")
    # ---- structure: 5 copies, 5 deletes, 5 merges (highest first)
    for k in (9, 7, 5, 3, 1): D.copy(k)
    for k in (10, 8, 6, 4, 2): D.delete(k)
    for k in (9, 7, 5, 3, 1): D.merge(k)
    D.verify("after copies, deletes, merges")
    # ---- objects: 3 added from the grid (O: a segment without objects, one with objects twice), 2 from the object list (I: behind the selected object)
    wo = [k for k in range(12, 70) if not M.seg_objs(k)]; wi = [k for k in range(12, 70) if len(M.seg_objs(k)) >= 2]
    D.objadd_grid(wo[0]); D.objadd_grid(wi[0]); D.objadd_grid(wi[0])
    D.objadd_list(M.seg_objs(wi[1])[0]); D.objadd_list(M.seg_objs(wi[2])[-1])
    D.verify("after 5 objects added")
    pos_of = lambda at_: [o[0] for o in M.objs].index(at_)
    cur = [M.objs[j][0] for k in (wi[3], wi[4], wi[5]) for j in M.seg_objs(k)[:2] if M.objs[j][1] != M.bar_t][:5]
    for at_, idx in zip(cur, (3, 7, 0, 12, 20)): D.objtype(pos_of(at_), idx)
    for at_, idx, adj_ in zip(cur, (0, 2, 8, 5, 4), (0, 0, 0, 3, 0)): D.objside(pos_of(at_), idx, adj_)
    # ---- moves: 10-unit steps, exact steps (fire + direction), into the next / previous segment and back
    plans = ([("lr", 1, 10)] * 3, [("lr", -1, 10)] * 2, [("lr", 1, 1)] * 3 + [("lr", 1, 10)], [("seg", 1), ("lr", -1, 10)], [("seg", 1), ("seg", 1), ("seg", -1), ("lr", -1, 1)])
    ids = [M.objs[pos_of(at_)] for at_ in cur]                      # the objects themselves (their units change)
    for ob, steps in zip(ids, plans): D.objmove(next(i for i, o in enumerate(M.objs) if o is ob), steps)
    D.verify("after types, sides, moves")
    for ob in ids: D.objdel(next(i for i, o in enumerate(M.objs) if o is ob))
    D.verify("after 5 objects deleted")
    # ---- the BAR is put into five segments (never deleted, never doubled); the last one is the segment it came from
    k0 = M.seg_of(M.bar_at())
    for k in (60, 3, 100, 30): D.barhere(k)
    D.barhere(min(k0, M.seg_last()))                                  # the BAR's old segment may now lie beyond the (shrunken) extent: it came from past the race length
    D.verify("after 5 BAR moves")
    # ---- undo x3, redo x2
    for _ in range(3): D.undo()
    for _ in range(2): D.redo()
    D.verify("after 3 undos and 2 redos")
    # ---- the raw accels and cut-up hill shapes leave a slope that never returns (the height would sit at the clamp for the whole race): FLAT once, then Return = repeat on every other segment with an accel
    ks = [k for k, s_ in enumerate(M.segs) if s_[3] != 0 and k < 24]
    if ks:
        D.hill(ks[0], 0)
        for k in ks[1:]: D.repeat(k, "FLAT", lambda k=k: M.hill_shape(k, 0))
    D.verify("after flattening the hills")

def run_quick(D, kind):
    """one quick cell: a few edits of every family, through keys and the joystick"""
    M = D.m
    D.split(0); D.split(1 if kind == "stock" else 0)   # a plain straight: 20024 of 32768 units are the race, a split of segment 1 would start beyond it
    D.curve(2, 8); D.curve(1, -6, "joy")
    D.hill(2, 2)
    D.width(1, "L", 8); D.length(1, 5)
    D.copy(1); D.delete(2); D.merge(1)
    j = D.objadd_grid(1); D.objtype(j, 3); D.objside(j, 2)
    j = D.objmove(j, [("lr", 1, 10), ("lr", -1, 1), ("seg", -1)])
    D.objadd_list(j)
    D.barhere(min(3, M.seg_last()))
    D.undo(); D.redo()
    D.verify("after the quick script")

def invalid_edits(D):
    M = D.m; nobj0, nseg0 = e.vu("nobj"), e.vu("nseg"); h0 = e.vl("hcur")
    # (1) the BAR cannot be deleted (B = its segment, the object list, DOWN to it, Delete)
    bi = [i for i, o in enumerate(M.objs) if o[1] == M.bar_t][0]
    e.send(0x30); e.idle(); check_cursor("B: the cursor is on the segment that holds the BAR", M.seg_of(M.bar_at()))
    D.goto_obj(bi)
    log("BAR object", bi, "cursor object", e.vu("obj"), "nbar", e.vu("nbar"))
    e.send(0x53); time.sleep(1.0); e.idle(); m1 = msgtext(); r.shot("inv_bar_delete")
    check("BAR delete refused: 'THE BAR CANNOT BE DELETED (E-BAR)', nothing changed", "E-BAR" in m1 and e.vu("nobj") == nobj0 and e.vl("hcur") == h0 and e.vu("nbar") == 1, f"message '{m1}' nobj {e.vu('nobj')}/{nobj0}")
    # (1b) Tab on a segment without objects: a message, the grid keeps the cursor
    k = next(k_ for k_ in range(M.seg_last()) if not M.seg_objs(k_)); D.goto_seg(k); e.send(0x0f); time.sleep(0.8); e.idle(); m1 = msgtext()
    check("Tab on a segment without objects: 'NO OBJECTS HERE: O ADDS ONE', the grid keeps the cursor", "NO OBJECTS" in m1 and e.vu("focus") == 0, f"message '{m1}' focus {e.vu('focus')}")
    # (2) a width out of range: list W, 85, RIGHT = 86 -> refused, the list stays open, LEFT = 85 is accepted again, Esc = nothing changes
    D.goto_seg(1); e.send(0x11); assert e.wait(lambda: e.vu("lopen") == 1, 20); time.sleep(0.8); e.list_goto(15)
    e.send(0x4d); time.sleep(1.0); e.settle(); time.sleep(0.5); b1, v1 = e.vu("lbad"), e.v("lval"); m2 = msgtext(); r.shot("inv_width_86")
    e.send(0x1c); time.sleep(1.5); still = e.vu("lopen")
    check("width 86 refused: 'OUTSIDE THE ORIGINAL RANGE (E-RANGE)', the list refuses to close", b1 == 1 and v1 == 86 and "E-RANGE" in m2 and still == 1, f"lbad {b1} lval {v1} lopen {still} message '{m2}'")
    e.send(0x4b); time.sleep(1.0); e.settle(); time.sleep(0.5)
    check("width back to 85: accepted again (lbad 0)", e.vu("lbad") == 0 and e.v("lval") == 85)
    e.send(0x01); assert e.wait(lambda: e.vu("lopen") == 0, 30); e.idle()
    check("Esc: nothing changed (history entry and lists as before)", e.vl("hcur") == h0 and e.vu("nseg") == nseg0 and D.verify("after the refused edits"))
    # (3) hill overflow: raw accel 4000 on the long segment
    k = [i for i, s_ in enumerate(M.segs[:-1]) if s_[1] >= 1500][0]
    D.goto_seg(k); e.send(0x23); assert e.wait(lambda: e.vu("lopen") == 1, 20); time.sleep(0.8); e.list_goto(13); e.send(0x1c)
    assert e.wait(lambda: e.vu("lopen") == 1 and e.vu("lact") == 8, 40); time.sleep(1.5); e.list_goto(13)
    e.settle(); time.sleep(0.5); b3, v3 = e.vu("lbad"), e.v("lval"); m3 = msgtext(); r.shot("inv_hill_overflow")
    check("raw accel 4000 on a 2000-unit segment refused: 'HILL TOO STEEP: OVERFLOW (E-HILL)'", b3 == 1 and v3 == 4000 and "E-HILL" in m3, f"lbad {b3} lval {v3} message '{m3}' (segment {k}, length {M.segs[k][1]})")
    e.send(0x01); assert e.wait(lambda: e.vu("lopen") == 0, 30); e.idle()
    check("Esc: nothing changed", e.vl("hcur") == h0 and D.verify("after the hill overflow test"))
    # (4) the check page: no blocking error
    e.send(0x25); assert e.wait(lambda: e.vu("state") == 3, 20); time.sleep(1.0); r.shot("check_page"); n_, ne = e.vu("chkn"), e.vu("chke")
    e.send(0x39); assert e.wait(lambda: e.vu("state") == 1, 20); e.idle()
    check("K: the check page lists no blocking error", ne == 0, f"messages {n_}, blocking {ne}")

try:
    r.ff(False) if hasattr(r, "ff") else None
    e.boot_editor(load_camp=(a.kind == "stock"))
    r.shot("1_tracklist")
    t, _ = mt.decode_stock(ms2, a.level)
    if a.kind == "stock": M = em.Model(t); old_count = 3
    else: M = em.Model(t, straight=True); old_count = 0
    check("viewer up", e.open_track(a.kind, a.level, ntr=old_count))
    D = Drv(M)
    check("start: lists in RAM == the model", D.verify("start"))
    r.shot("2_start")
    (run_quick if a.quick else run_script)(D, a.kind)
    r.shot("3_after_script")
    if not a.quick: invalid_edits(D)
    # ---- leave: the track is kept in the campaign file in memory
    nseg_e, nobj_e = e.vu("nseg"), e.vu("nobj")
    e.send(0x01); check("Esc = back to the track list", e.wait(lambda: e.vu("state") == 0, 60)); time.sleep(2.0); r.shot("4_tracklist_after")
    st = e.store(); Path(f"{os.environ.get('ED_TMP', '/tmp/msred8')}/{tag}.trk").write_bytes(st)
    ents = mt.parse_campaign(st)
    check(f"campaign in memory: {old_count + 1} tracks, V_COUNT / V_LOADED", len(ents) == old_count + 1 and r.w(V["count"]) == old_count + 1 and r.b(V["loaded"]) != 0, f"{len(ents)} entries, V_COUNT {r.w(V['count'])}")
    blk = bytes(ents[-1]["block"]); ln_last = len(blk)
    exp = M.block()
    check(f"the kept block ({len(blk)} B) == what the Python model of the edit script predicts (mt.encode_track of the model)", blk == exp, f"{len(blk)} vs {len(exp)} B, first diff {next((i for i, (x, y) in enumerate(zip(blk, exp)) if x != y), None)}")
    import subprocess
    p = subprocess.run([sys.executable, str(HERE.parents[1] / "tools" / "msrtrack.py"), "validate", f"{os.environ.get('ED_TMP', '/tmp/msred8')}/{tag}.trk"], capture_output=True, text=True)
    log(p.stdout.strip()); check("msrtrack.py validate of the campaign file dumped from RAM: exit 0, no errors", p.returncode == 0 and "ERROR" not in p.stdout, p.stdout[-300:])
    if a.kind == "stock":
        orig = mt.parse_campaign((CAMP / "c3.trk").read_bytes())
        co = (CAMP / "c3.trk").read_bytes()
        same = all(bytes(ents[i]["block"]) == bytes(orig[i]["block"]) for i in range(3))
        check("the three campaign tracks before the new one are byte for byte unchanged", same)
    # ---- re-enter: the edits are there
    sel = old_count
    e.key(0x50, sel, 0.4); e.send(0x1c); time.sleep(1.2)                 # the kept track -> EDIT / PLAY / DELETE / BACK
    r.shot("5_trackmenu"); e.send(0x1c)                                  # EDIT THIS TRACK
    check("re-entered: viewer up", e.wait(lambda: e.vu("state") == 1, 60)); time.sleep(1.5); e.idle()
    sg, ob = e.segs(), e.objs(); ns = norm(M.segs)
    check(f"re-entered: the segment list ({len(sg)}) == the model's merged list, objects ({len(ob)}) == the model's", [x[:6] for x in sg] == [list(x[:6]) for x in ns] and [x[:3] for x in ob] == [o[:3] for o in M.objs],
          f"{len(sg)} vs {len(ns)}, {len(ob)} vs {len(M.objs)}")
    r.shot("6_reentered")
    e.send(0x01); assert e.wait(lambda: e.vu("state") == 0, 60); time.sleep(1.5)
    # ---- PLAY THIS TRACK: a normal race on it
    if not a.norace:
        e.key(0x50, sel, 0.4); e.send(0x1c); time.sleep(1.2); e.key(0x50, 1, 0.4); r.shot("7_trackmenu_play"); e.send(0x1c)        # PLAY THIS TRACK
        # (the earlier version logged for 8 s before it looked for the race: the race of the right track came and went in that time, then the harness's SPACE presses started a new game from the title = track 0)
        vp = e.vu("play"); log(f"vPlay {vp} V_START {r.w(0xb8e06)} CPV+4 {r.w(0xb8e04)} $102c {r.w(0x102c):#x}")
        log(f"after PLAY: V_START {r.w(0xb8e06)} (the menu consumes it at once) vPlay {vp}")
        res = []; ok = False
        w0 = None                                                         # NO key presses (SPACE at the title / start screens starts a new game = track 0); race criterion $23c0 != 0 and $1024 == 0 ($100e can stay <= 30 on a short-lived edited road)
        for _ in range(240):
            time.sleep(0.5)
            if r.l(0x23c0) != 0 and r.b(0x1024) == 0: w0 = (r.w(0x57890), r.w(0x102c), r.l(0x23c0), r.w(V["pos"])); break
        if w0 is not None:
            res.append(w0); r.st("race 0 start"); r.shot("race_start")
            ring = r.mem(0x1bbc, 64); got = [struct.unpack(">h", ring[2 * i:2 * i + 2])[0] for i in range(32)]
            ok = r.drive_to_finish(tmo=300); r.st(f"race 0 over (finished={ok})"); r.shot("race_over")
        base_addr = 0x110000 + ents[-1]["offset"]
        check("race on the edited track: the stream pointer is inside its block in the campaign store, driven to the BAR (drive_to_finish saw $1024 = $ff; the state is read before the end-of-race screens move on), campaign position = the edited track", len(res) == 1 and base_addr <= res[0][2] < base_addr + ln_last + 64 and ok and res[0][3] == sel,
              f"{res} finished {ok} block ${base_addr:x}..${base_addr + ln_last:x} $1024 {r.b(0x1024):#x}")
    log(f"Bus/Address error lines in the Hatari log: {r.errlines()}")
except Exception as ex:
    import traceback; log("EXCEPTION", traceback.format_exc()); FAILS.append("exception")
finally:
    try: log(f"wall {time.time() - t0_:.0f} s")
    except Exception: pass
    e.close()
log(f"RESULT {tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
