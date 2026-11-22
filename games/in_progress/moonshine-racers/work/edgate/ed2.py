#!/usr/bin/env python3
"""Track editor milestone 2 (EDITING) gate, HD build.  One boot: campaign (c3.trk, or none) -> TRACK EDITOR -> a copy of an original track / a plain straight -> an edit script through the UI (keys and
joystick: lists with live preview, menu, Return repeat, undo / redo, refused edits) mirrored by ed2model.py -> leave (the store is rebuilt) -> block == model, msrtrack.py validate -> re-enter ->
PLAY THIS TRACK -> a normal race on it driven to the BAR.
  work/edgate/env2.sh python3 work/edgate/ed2.py --kind stock|straight --machine ste|megaste|st --mem 2048 [--quick] [--tag X]"""
import argparse
from ed2lib import *
import ed2model as em
from PIL import Image, ImageChops

ap = argparse.ArgumentParser()
ap.add_argument("--kind", default="stock"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--quick", action="store_true"); ap.add_argument("--tag"); ap.add_argument("--build", default=os.environ.get("ED_BUILD", "/tmp/msred2/hd")); ap.add_argument("--norace", action="store_true")
ap.add_argument("--level", type=int, default=3)
a = ap.parse_args()
short = f"{ {'ste': 'ste', 'megaste': 'mste', 'st': 'st'}[a.machine] }{a.mem // 1024}m"
tag = a.tag or f"ed2_{a.kind}_{short}"
camp = CAMP / "c3.trk" if a.kind == "stock" else None
e = Ed(tag, a.machine, a.mem, a.build, camp); r = e.r
ms2 = mt.read_ms2()
t0_ = time.time()
VAR.update(lpend=256, lmsg=442, msel=112, lact=220)

def msgtext():
    p = e.vl("lmsg")
    if not 0x130000 <= p < 0x140000: return ""
    b = r.mem(p, 48); return b.split(b"\0")[0].decode("latin1")

def adj(n):
    """exact adjust with LEFT / RIGHT: one key, wait for the value to move and the preview to finish"""
    for _ in range(abs(n)):
        v0 = e.v("lval"); e.send(0x4d if n > 0 else 0x4b); e.wait(lambda: e.v("lval") != v0, 6, 0.15); time.sleep(0.2); e.settle()

class Drv:
    def __init__(s, model):
        s.m = model; s.n = 0; s.log = []
    # ---- navigation
    def goto_seg(s, k):
        for _ in range(120):
            sg, p = e.vu("seg"), e.vl("pos")
            st = s.m.segs[sg][0] if sg < len(s.m.segs) else 0
            if sg == k and p == s.m.segs[k][0]: return
            if sg < k: e.key(0x4d, 1, 0.4)
            else: e.key(0x4b, 1, 0.4)
        raise RuntimeError(f"goto_seg {k}: at {e.vu('seg')}")
    def road(s):
        if e.vu("focus") != 0: e.key(0x0f, 1, 0.5)
    def objrow(s):
        if e.vu("focus") != 1: e.key(0x0f, 1, 0.5)
    def goto_obj(s, j):
        s.objrow()
        for _ in range(200):
            o = e.vu("obj")
            if o == j: return
            e.key(0x4d if o < j else 0x4b, 1, 0.35)
        raise RuntimeError(f"goto_obj {j}")
    def joyfine(s, d):
        """FIRE held, then LEFT / RIGHT: one strip pixel (the way a joystick player does it)"""
        e.jpoke(0x80); time.sleep(0.15); e.jpoke(0x80 | (8 if d > 0 else 4)); time.sleep(0.06); e.jpoke(0x80); time.sleep(0.15); e.jpoke(0); time.sleep(0.4)
    # ---- lists
    def listpick(s, key, idx, adjust=0, how="key"):
        e.send(key); assert e.wait(lambda: e.vu("lopen") == 1, 25), "list did not open"; time.sleep(0.8)
        if idx is not None: assert e.list_goto(idx), f"list_goto {idx}: at {e.v('lsel')}"
        adj(adjust); e.settle(); time.sleep(0.4)
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
    def curve(s, k, v, how="key", key=0x2e):
        s.road(); s.goto_seg(k); val, bad = s.listpick(0x2e, v + 9, how=how); assert not bad
        s.note(f"curve seg {k} = {val}"); s.m.set_curve(k, val)
    def hill(s, k, shape, how="key"):
        s.road(); s.goto_seg(k); val, bad = s.listpick(0x23, shape, how=how)
        err = s.m.hill_shape(k, val); s.note(f"hill seg {k} shape {val}", err)
    def raw(s, k, idx, adjust=0):
        s.road(); s.goto_seg(k); e.send(0x23); assert e.wait(lambda: e.vu("lopen") == 1, 25); time.sleep(0.8); assert e.list_goto(13); e.send(0x1c)
        assert e.wait(lambda: e.vu("lopen") == 1 and e.vu("lact") == 8 and e.vu("lpend") == 0, 40); time.sleep(1.5)        # the exact list opens by itself
        assert e.list_goto(idx)
        adj(adjust); e.settle(); time.sleep(0.4)
        val = e.v("lval"); bad = e.vu("lbad"); e.send(0x1c)
        if bad: time.sleep(1.5); s.note(f"raw accel seg {k} = {val}", "E-HILL/E-RANGE"); return True
        e.wait(lambda: e.vu("lopen") == 0, 40); e.idle()
        err = s.m.set_raw(k, val); s.note(f"raw accel seg {k} = {val}", err); return False
    def length(s, k, idx, adjust=0, how="key"):
        s.road(); s.goto_seg(k); val, bad = s.listpick(0x26, idx, adjust, how)
        err = s.m.set_len(k, val); s.note(f"length seg {k} = {val}", err)
    def width(s, k, side, idx, adjust=0):
        s.road(); s.goto_seg(k); val, bad = s.listpick(0x11 if side == "L" else 0x12, idx, adjust)
        err = (s.m.set_wl if side == "L" else s.m.set_wr)(k, val); s.note(f"width {side} seg {k} = {val}", err)
    def repeat_at(s, k, act):
        """Return = the last pick again at the cursor"""
        s.road(); s.goto_seg(k); e.send(0x1c); e.idle()
        s.note(f"repeat (Return) at seg {k}: {act}")
    def copy(s, k):
        s.road(); s.goto_seg(k); e.send(0x17); e.idle(); err = s.m.seg_copy(k); s.note(f"insert copy of seg {k}", err)
    def delete(s, k):
        s.road(); s.goto_seg(k); e.send(0x53); e.idle(); err = s.m.seg_del(k); s.note(f"delete seg {k}", err)
    def merge(s, k):
        s.road(); s.goto_seg(k); e.send(0x32); e.idle(); err = s.m.seg_merge(k); s.note(f"merge seg {k} with the next", err)
    def split(s, k, steps):
        s.road(); s.goto_seg(k)
        for _ in range(steps): s.joyfine(1)
        pos = e.vl("pos"); e.send(0x1f); e.idle(); err = s.m.seg_split(k, pos); s.note(f"split seg {k} at {pos}", err)
    def objtype(s, j, idx):
        s.goto_obj(j); val, bad = s.listpick(0x14, idx); err = s.m.obj_type(j, val); s.note(f"object {j} type {val}", err)
    def objside(s, j, idx, adjust=0):
        s.goto_obj(j); val, bad = s.listpick(0x1f, idx, adjust); err = s.m.obj_side(j, val); s.note(f"object {j} side {val}", err)
    def objadd(s, j, steps=1):
        """cursor on object j, fine-move (joystick) to a free unit, I = add"""
        s.goto_obj(j)
        for _ in range(steps): s.joyfine(-1)
        pos = e.vl("pos"); free = {o[0] for o in s.m.objs}
        while pos in free: s.joyfine(-1); pos = e.vl("pos")
        e.send(0x17); e.idle(); err = s.m.obj_add(pos); s.note(f"add object at {pos}", err)
        return e.vu("obj")
    def objdel(s, j):
        s.goto_obj(j); e.send(0x53); e.idle(); err = s.m.obj_del(j); s.note(f"delete object {j}", err)
    def objmove(s, j, n):
        s.goto_obj(j); e.send(0x32); assert e.wait(lambda: e.vu("mode") == 1, 20); time.sleep(0.5)
        for _ in range(abs(n)): e.send(0x4d if n > 0 else 0x4b); time.sleep(0.4)
        e.send(0x1c); assert e.wait(lambda: e.vu("mode") == 0, 20); e.idle(); err = s.m.obj_move(j, 10 * n); s.note(f"move object {j} by {10 * n}", err)
    def barhere(s, k):
        s.road(); s.goto_seg(k); pos = e.vl("pos"); s.menu(9); err = s.m.bar_here(pos); s.note(f"BAR here (seg {k}, unit {pos}) via the menu", err)
    def undo(s):
        e.send(0x16); e.idle(); err = s.m.undo(); s.note("undo", err)
    def redo(s):
        s.road(); s.menu(11); err = s.m.redo(); s.note("redo (menu)", err)
    def verify(s, name):
        sg, ob = e.segs(), e.objs()
        msg = [s_[:6] for s_ in s.m.segs] == [x[:6] for x in sg] and [[o[0], o[1], o[2]] for o in ob] == [o[:3] for o in s.m.objs] and [o[3] for o in ob] == [1 if o_[1] == s.m.bar_t else 0 for o_ in s.m.objs]
        d = ""
        if not msg:
            bad = [i for i, (x, y) in enumerate(zip(sg, s.m.segs)) if list(x[:6]) != list(y[:6])][:3]
            d = f"nseg {len(sg)} vs {len(s.m.segs)}; first diffs {[(i, sg[i], s.m.segs[i]) for i in bad]}; nobj {len(ob)} vs {len(s.m.objs)}"
        check(f"{name}: segment and object lists in RAM == the model ({len(sg)} segments, {len(ob)} objects, after {s.n} edits)", msg, d)
        return msg


def norm(segs):
    out = []
    for x in segs:
        if out and out[-1][2:6] == x[2:6]: out[-1][1] += x[1]
        else: out.append(list(x))
    return out

def run_script(D, kind):
    M = D.m
    # ---- 5 splits (joystick fine moves: FIRE held, then RIGHT = one strip pixel = 128 units)
    for k, st in ([(0, 1), (1, 1), (3, 1), (5, 1), (7, 1)] if kind == "stock" else [(k_, 5) for k_ in range(8)]):
        D.split(k, st)
    D.verify("after 5 splits")
    # ---- 6 curves (lists with live preview; one accepted with the joystick), then Return = the same value again on another segment
    for k, v, how in ((6, 8, "key"), (5, -6, "key"), (4, 10, "joy"), (3, -9, "key"), (2, 4, "key"), (1, -3, "key")):
        D.curve(k, v, how)
    D.last = ("curve", M.segs[1][2]); D.road(); D.goto_seg(8); e.send(0x1c); e.idle(); err = M.set_curve(8, D.last[1]); D.note(f"Return = repeat curve {D.last[1]} at seg 8", err)
    D.verify("after 7 curve edits")
    # ---- hills (highest segment first: the pieces a shape makes shift only the segments behind it): RISE MEDIUM / CREST SMALL / DIP BIG / DROP SMALL shapes, a raw accel + Return
    for k, sh in ((7, 4), (5, 12), (3, 7), (1, 2)):
        D.hill(k, sh, "joy" if sh == 4 else "key")
    D.raw(0, 5, 3)                                                  # -100 + 3 exact steps = -97
    D.last = ("raw", e.v("lval")); D.road(); D.goto_seg(2); e.send(0x1c); e.idle(); err = M.set_raw(2, D.last[1]); D.note(f"Return = repeat raw accel {D.last[1]} at seg 2", err)
    D.verify("after 6 hill edits")
    # ---- lengths (presets, an exact +3, one long segment for the E-HILL test below), highest first
    ks = [k for k in range(len(M.segs) - 1) if M.segs[k][1] >= 20 and M.segs[k][3] == 0][:12]
    sel = [ks[i] for i in (8, 6, 4, 3, 1)] if len(ks) >= 9 else ks[:5]
    for n, k in enumerate(sel):
        D.length(k, (5, 6, 4, 14, 3)[n], adjust=3 if n == 0 else 0, how="joy" if n == 2 else "key")
    long_k = sel[3]
    D.verify("after 5 length edits")
    # ---- widths: left / right presets and exact values
    for n, (k, side, idx, adj) in enumerate(((1, "L", 8, 0), (2, "R", 2, 0), (3, "L", 12, 2), (4, "R", 10, -1), (5, "L", 1, 0))):
        D.width(k, side, idx, adj)
    D.verify("after 5 width edits")
    # ---- structure: 5 copies, 5 deletes, 5 merges (highest first)
    for k in (9, 7, 5, 3, 1): D.copy(k)
    for k in (10, 8, 6, 4, 2): D.delete(k)
    for k in (9, 7, 5, 3, 1): D.merge(k)
    D.verify("after copies, deletes, merges")
    # ---- objects: add 5 (fine move left of an object, I), types (list of the base level's own types), sides, moves, deletes
    pos_of = lambda at_: [o[0] for o in M.objs].index(at_)
    if len(M.objs) > 12: plan = [(M.objs[j][0], 1) for j in (9, 8, 7, 6, 5)]
    else: plan = [([o[0] for o in M.objs if o[1] == M.bar_t][0], k) for k in (1, 2, 3, 4, 5)]       # a straight has only the BAR: objects are added left of it
    for at, steps in plan: D.objadd(pos_of(at), steps)
    D.verify("after 5 objects added")
    cur = [o[0] for o in M.objs if o[1] != M.bar_t][:5]
    for at_, idx in zip(cur, (3, 7, 0, 12, 20)): D.objtype(pos_of(at_), idx)
    for at_, idx, adj in zip(cur, (0, 2, 8, 5, 4), (0, 0, 0, 3, 0)): D.objside(pos_of(at_), idx, adj)
    D.last = ("side", e.v("lval"))
    for at_, n in zip(cur, (3, -2, 5, 2, -4)): D.objmove(pos_of(at_), n)
    D.verify("after types, sides, moves")
    for at_ in [o[0] for o in M.objs if o[1] != M.bar_t][:5]: D.objdel(pos_of(at_))
    D.verify("after 5 objects deleted")
    # ---- the BAR is moved five times (never deleted, never doubled)
    used = {o[0] for o in M.objs if o[1] != M.bar_t}
    free = [k for k in range(2, len(M.segs) - 1) if M.segs[k][0] not in used]
    for i in (1, 0, 3, 2, 5):
        D.barhere(free[i % len(free)])
    D.verify("after 5 BAR moves")
    # ---- undo x3, redo x2
    for _ in range(3): D.undo()
    for _ in range(2): D.redo()
    D.verify("after 3 undos and 2 redos")
    # ---- the raw accels and cut-up hill shapes leave a slope that never returns (the height would sit at the clamp for the whole race): FLAT once, then Return = repeat on every other segment with an accel
    ks = [k for k, s_ in enumerate(M.segs) if s_[3] != 0 and k < 24]
    if ks:
        D.hill(ks[0], 0)
        for k in ks[1:]:
            D.road(); D.goto_seg(k); e.send(0x1c); e.idle(); err = M.hill_shape(k, 0); D.note(f"Return = repeat FLAT at seg {k}", err)
    D.verify("after flattening the hills")

def run_quick(D, kind):
    """one quick cell: a few edits of every family, through keys and the joystick"""
    M = D.m; st = 1 if kind == "stock" else 5
    D.split(0, st); D.split(1, st)
    D.curve(2, 8); D.curve(1, -6, "joy")
    D.hill(2, 2)
    D.width(1, "L", 8); D.length(1, 5)
    D.copy(1); D.delete(2); D.merge(1)
    at = M.objs[9][0] if len(M.objs) > 12 else [o[0] for o in M.objs if o[1] == M.bar_t][0]; j = D.objadd([o[0] for o in M.objs].index(at), 1)
    D.objtype(j, 3); D.objside(j, 2)
    used = {o[0] for o in M.objs if o[1] != M.bar_t}
    cand = [k for k in range(1, len(M.segs)) if M.segs[k][0] not in used]
    if cand: D.barhere(cand[min(1, len(cand) - 1)])
    D.undo(); D.redo()
    D.verify("after the quick script")

def invalid_edits(D):
    M = D.m; nobj0, nseg0 = e.vu("nobj"), e.vu("nseg"); h0 = e.vl("hcur")
    # (1) the BAR cannot be deleted
    D.road(); e.send(0x30); e.idle(); D.objrow(); time.sleep(0.5)
    bi = [o[1] for o in M.objs].index(M.bar_t) if False else [i for i, o in enumerate(M.objs) if o[1] == M.bar_t][0]
    log("BAR object", bi, "cursor object", e.vu("obj"), "nbar", e.vu("nbar"))
    e.send(0x53); time.sleep(1.5); m1 = msgtext(); r.shot("inv_bar_delete")
    check("BAR delete refused: 'THE BAR CANNOT BE DELETED (E-BAR)', nothing changed", "E-BAR" in m1 and e.vu("nobj") == nobj0 and e.vl("hcur") == h0 and e.vu("nbar") == 1, f"message '{m1}' nobj {e.vu('nobj')}/{nobj0}")
    # (2) a width out of range: list W, 85, RIGHT = 86 -> refused, the list stays open, LEFT = 85 is accepted again, Esc = nothing changes
    D.road(); D.goto_seg(1); e.send(0x11); assert e.wait(lambda: e.vu("lopen") == 1, 20); time.sleep(0.8); e.list_goto(15)
    e.send(0x4d); time.sleep(1.0); e.settle(); time.sleep(0.5); b1, v1 = e.vu("lbad"), e.v("lval"); m2 = msgtext(); r.shot("inv_width_86")
    e.send(0x1c); time.sleep(1.5); still = e.vu("lopen")
    check("width 86 refused: 'OUTSIDE THE ORIGINAL RANGE (E-RANGE)', the list refuses to close", b1 == 1 and v1 == 86 and "E-RANGE" in m2 and still == 1, f"lbad {b1} lval {v1} lopen {still} message '{m2}'")
    e.send(0x4b); time.sleep(1.0); e.settle(); time.sleep(0.5)
    check("width back to 85: accepted again (lbad 0)", e.vu("lbad") == 0 and e.v("lval") == 85)
    e.send(0x01); assert e.wait(lambda: e.vu("lopen") == 0, 30); e.idle()
    check("Esc: nothing changed (history entry and lists as before)", e.vl("hcur") == h0 and e.vu("nseg") == nseg0 and D.verify("after the refused edits"))
    # (3) hill overflow: raw accel 4000 on the long segment
    k = [i for i, s_ in enumerate(M.segs[:-1]) if s_[1] >= 1500][0]
    D.road(); D.goto_seg(k); e.send(0x23); assert e.wait(lambda: e.vu("lopen") == 1, 20); time.sleep(0.8); e.list_goto(13); e.send(0x1c)
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
    if a.kind == "stock":
        e.key(0x50, 3, 0.5); e.send(0x1c); time.sleep(1.0); e.key(0x50, a.level, 0.35)
        t, _ = mt.decode_stock(ms2, a.level); M = em.Model(t); old_count = 3
    else:
        e.key(0x50, 1, 0.5); e.send(0x1c); time.sleep(1.0); e.key(0x50, a.level, 0.35)
        t, _ = mt.decode_stock(ms2, a.level); M = em.Model(t, straight=True); old_count = 0
    e.send(0x1c)
    check("viewer up", e.wait(lambda: e.vu("state") == 1, 60)); time.sleep(1.5); e.idle()
    D = Drv(M)
    check("start: lists in RAM == the model", D.verify("start"))
    r.shot("2_start")
    (run_quick if a.quick else run_script)(D, a.kind)
    r.shot("3_after_script")
    if not a.quick: invalid_edits(D)
    # ---- leave: the track is kept in the campaign file in memory
    nseg_e, nobj_e = e.vu("nseg"), e.vu("nobj")
    e.send(0x01); check("Esc = back to the track list", e.wait(lambda: e.vu("state") == 0, 60)); time.sleep(2.0); r.shot("4_tracklist_after")
    st = e.store(); Path(f"{os.environ.get('ED_TMP', '/tmp/msred2')}/{tag}.trk").write_bytes(st)
    ents = mt.parse_campaign(st)
    check(f"campaign in memory: {old_count + 1} tracks, V_COUNT / V_LOADED", len(ents) == old_count + 1 and r.w(V["count"]) == old_count + 1 and r.b(V["loaded"]) != 0, f"{len(ents)} entries, V_COUNT {r.w(V['count'])}")
    blk = bytes(ents[-1]["block"]); ln_last = len(blk)
    exp = M.block()
    check(f"the kept block ({len(blk)} B) == what the Python model of the edit script predicts (mt.encode_track of the model)", blk == exp, f"{len(blk)} vs {len(exp)} B, first diff {next((i for i, (x, y) in enumerate(zip(blk, exp)) if x != y), None)}")
    import subprocess
    p = subprocess.run([sys.executable, str(HERE.parents[1] / "tools" / "msrtrack.py"), "validate", f"{os.environ.get('ED_TMP', '/tmp/msred2')}/{tag}.trk"], capture_output=True, text=True)
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
