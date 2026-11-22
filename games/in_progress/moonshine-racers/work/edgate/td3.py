#!/usr/bin/env python3
"""Milestone 3 gate: TEST DRIVE FROM THE CURSOR, HD build, one boot.
 campaign c3.trk -> TRACK EDITOR -> COPY OF TRACK 04 -> a few real edits (bend keys, an inserted segment) -> test drives from the cursor at START / MIDDLE / NEAR THE BAR:
   at every race start: $5ff8 == the cursor unit, the game's curve / width / hill rings and the object slots == a Python expansion of the encoded working copy (ENCBUF read back from RAM), the time bar,
   screenshot; ends: Esc (start), F10 (middle), the BAR (joystick up: finish, tdvbl returns), time-out (standing); after every return: the editor is where it was (cursor, segment / object lists unchanged, keys work,
   V_TD clear, vectors back); then leave (the store keeps the edits), PLAY THIS TRACK of a campaign track and a normal campaign race with the shop click: still normal.
   work/edgate/env5.sh python3 work/edgate/td3.py --tag T [--machine ste|megaste|st] [--quick]"""
import argparse
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="td3"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--machine", default="ste"); ap.add_argument("--level", type=int, default=3)
ap.add_argument("--quick", action="store_true"); ap.add_argument("--nonormal", action="store_true")
a = ap.parse_args()
VAR.update(encl=274, barat=52)
TD = dict(tdhit=2326, tdres=2328, tdlast=2330, tdwhy=2334, encl=274)
VTD = 0xb8e0e
e = Ed(a.tag, a.machine, 2048, a.build, CAMP / "c3.trk"); r = e.r
S16 = lambda b: [struct.unpack(">h", b[i:i + 2])[0] for i in range(0, len(b), 2)]

def vb(off): return r.b(EV + off)
def vw(off): return r.w(EV + off)

def snapshot():
    return dict(pos=e.vl("pos"), seg=e.vu("seg"), segs=e.segs(), objs=e.objs(), nseg=e.vu("nseg"), nobj=e.vu("nobj"), mod=e.vu("mod"))

def goto_pos(target, why=""):
    """cursor to the first segment start >= target: Shift + RIGHT = next 1000 (coarse), then single RIGHT / LEFT steps"""
    e.idle()
    if e.vl("pos") == target: return
    for _ in range(300):
        p = e.vl("pos")
        if p >= target: break
        e.key(0x4d, 1, 0.1)
    e.idle()
    log(f"cursor {why}: unit {e.vl('pos')} seg {e.vu('seg')}")

def td_wait_race(hit0, tmo=90):
    """the test drive has fast-forwarded (td_ff ran once more) and the race stands"""
    t0 = time.time()
    while time.time() - t0 < tmo:
        time.sleep(0.4)
        try:
            if vw(TD["tdhit"]) > hit0 and r.b(0x1024) == 0 and r.w(0x5ff8) >= 0 and r.b(VTD) == 0xff: return True
        except Exception: pass
    return False

def td_wait_back(tmo=120):
    t0 = time.time()
    while time.time() - t0 < tmo:
        time.sleep(0.5)
        try:
            if r.b(VTD) == 0 and e.vu("state") == 1 and e.vu("redraw") == 0 and r.b(0x1028) == 0: return True
        except Exception: pass
    return False

def rings_check(label, N, blk_len, expect_bar):
    """game rings + objects vs the Python expansion of ENCBUF"""
    blk = e.grab(0x1b0000, blk_len, "enc")
    t, used = mt.parse_block(blk)
    cur = expand = mt.expand_curve(t["curve"], 33000); lw = mt.expand_width(t["left"], 33000); rw = mt.expand_width(t["right"], 33000); hl, ovf = mt.expand_hill(t["hill"], 33000)
    cr = S16(e.grab(0x1bbc, 2048, "cring")); head_c = r.w(0x1bba)
    lring = e.grab(0x13b0, 1024, "lring"); rring = e.grab(0x17b0, 1024, "rring"); head_w = r.w(0x13ae)
    hring = e.grab(0x23c8, 1024, "hring"); head_h = r.w(0x23c6)
    log(f"[{label}] N={N} heads: curve $1bba={head_c} width $13ae={head_w} hill $23c6={head_h}  $5ff8={r.w(0x5ff8)}")
    def cmp(name, ring, exp, head):
        best = None
        for sh in range(-3, 4):
            bad = 0
            for i in range(1024):
                u = N + i + sh
                ev = exp[u] if 0 <= u < len(exp) else None
                if ev is None: continue
                if (ring[(head + i) & 1023] if True else None) != ev: bad += 1
            if best is None or bad < best[1]: best = (sh, bad)
        z = sum(1 for i in range(1024) if 0 <= N + i < len(exp) and ring[(head + i) & 1023] != exp[N + i])
        log(f"[{label}] {name} ring: mismatches at shift 0 = {z}; best shift {best[0]} ({best[1]} mismatches); first entries {[ring[(head + i) & 1023] for i in range(6)]} expected {exp[N:N + 6]}")
        return z
    ch = [cr[i] for i in range(1024)]                       # head in bytes -> entries
    z1 = cmp("curve", ch, cur, head_c // 2)
    z2 = cmp("left", list(lring), lw, head_w)
    z3 = cmp("right", list(rring), rw, head_w)
    z4 = cmp("hill", list(hring), hl, head_h)
    check(f"[{label}] rings == expansion of the working copy at unit {N} (curve / left / right / hill mismatches {z1} {z2} {z3} {z4})", z1 + z2 + z3 + z4 == 0)
    # objects
    sl = e.grab(0x2d80, 32 * 56, "slots"); got = []
    for k in range(32):
        s = sl[k * 56:(k + 1) * 56]
        if s[4] & 1: got.append((struct.unpack(">h", s[0x20:0x22])[0], struct.unpack(">h", s[0x1c:0x1e])[0], struct.unpack(">H", s[6:8])[0]))
    exp = sorted((o["at"] - N, o["lateral"]) for o in t["objects"] if N <= o["at"] <= N + 1023)
    gs = sorted((g[0], g[1]) for g in got)
    log(f"[{label}] object slots active {len(got)}, expected {len(exp)} (window {N}..{N + 1023}); first got {gs[:4]} exp {exp[:4]}")
    check(f"[{label}] object slots == the objects of the working copy in the window [{N}, {N + 1023}] (distance relative to the camera, lateral)", gs == exp, f"{len(gs)} vs {len(exp)}")
    # time bar
    ce, rate = r.l(0x10ce), r.w(0x10d2)
    bar = None
    for o in t["objects"]: pass
    if expect_bar is not None:
        R = max(0, expect_bar - 500 - N); P = (R // 10) * 2 + 100; exp0 = max(0, 0xff0000 - P * rate)
        log(f"[{label}] time bar: $10ce={ce:#x} rate $10d2={rate}; R={R} P={P} expected start {exp0:#x} (the bar has run on since: tolerance 600 passes)")
        check(f"[{label}] time bar start == $ff0000 - (2 x R/10 + 100) x rate (clamped at 0)", exp0 <= ce <= exp0 + 600 * rate, f"{ce:#x} vs {exp0:#x}")
    return t

def after_return(label, snap0, shot=True):
    e.idle(); time.sleep(0.5)
    if shot: r.shot(f"{label}_back")
    s = snapshot()
    check(f"[{label}] back in the editor at the same cursor (unit {snap0['pos']} seg {snap0['seg']})", s["pos"] == snap0["pos"] and s["seg"] == snap0["seg"], f"{s['pos']} {s['seg']}")
    check(f"[{label}] working copy intact: {s['nseg']} segments / {s['nobj']} objects identical to before, vMod unchanged", s["segs"] == snap0["segs"] and s["objs"] == snap0["objs"] and s["mod"] == snap0["mod"])
    check(f"[{label}] V_TD cleared, $1028 race flag clear, $102c as before", r.b(VTD) == 0 and r.b(0x1028) == 0 and r.w(0x102c) == snap0["102c"], f"$102c {r.w(0x102c):#x} vs {snap0['102c']:#x}")
    ik = r.l(0x118); vb_ = r.l(0x70)
    log(f"[{label}] vectors: $118 {ik:#x} $70 {vb_:#x} (editor hook inside $130000-$13ffff: {0x130000 <= ik < 0x140000}; VBL = the game's $d11e: {vb_ == 0xd11e})")
    check(f"[{label}] IKBD vector = the editor's kbhook again, VBL vector = the game's handler", 0x130000 <= ik < 0x140000 and vb_ == 0xd11e)
    p0 = e.vl("pos"); e.key(0x4d, 1, 0.3); e.idle(); p1 = e.vl("pos")
    check(f"[{label}] keys work after the return (RIGHT: cursor {p0} -> {p1})", p1 != p0)
    e.key(0x4b, 1, 0.3); e.idle()
    check(f"[{label}] LEFT puts the cursor back on {p0}", e.vl("pos") == p0, f"{e.vl('pos')}")
    return s

def one_drive(label, N_target, how, bar_expect, drive=0.0, hold=6.0, endkey=None):
    goto_pos(N_target, label)
    snap0 = snapshot(); snap0["102c"] = r.w(0x102c)
    N = snap0["pos"]; log(f"[{label}] TEST DRIVE from unit {N} (segment {snap0['seg']})")
    r.shot(f"{label}_cursor")
    hit0 = vw(TD["tdhit"]); t0 = time.time()
    e.send(0x19)
    ok = td_wait_race(hit0); check(f"[{label}] race starts (td_ff ran, race standing, V_TD set)", ok, f"in {time.time() - t0:.0f} s")
    r.st(f"{label} race up")
    check(f"[{label}] $5ff8 == the cursor unit {N} (distance counter)", r.w(0x5ff8) == N, f"{r.w(0x5ff8)}")
    check(f"[{label}] stream pointer inside ENCBUF ($1b0000..), campaign position / $102c = base level 3", 0x1b0000 <= r.l(0x23c0) < 0x1c0000 and r.w(0x102c) == 3, f"{r.l(0x23c0):#x} {r.w(0x102c):#x}")
    t = rings_check(label, N, e.vl("encl"), bar_expect)
    r.shot(f"{label}_race_standing")
    if drive:
        e.jpoke(0x01); time.sleep(drive); r.shot(f"{label}_race_driving"); log(f"[{label}] after {drive} s UP: $5ff8={r.w(0x5ff8)} $1024={r.b(0x1024):#x} $10ce={r.l(0x10ce):#x}"); e.jpoke(0)
        check(f"[{label}] the car drove on from the cursor ($5ff8 > {N})", r.w(0x5ff8) > N, f"{r.w(0x5ff8)}")
    if how == "esc": e.send(0x01)
    elif how == "f10": e.send(0x44)
    elif how == "bar": e.jpoke(0x01)
    elif how == "timeout": pass
    t0 = time.time(); back = td_wait_back(150)
    if how == "bar": e.jpoke(0)
    why = vb(TD["tdwhy"]); res = vb(TD["tdres"]); last = vw(TD["tdlast"])
    log(f"[{label}] returned after {time.time() - t0:.1f} s: why={why} ($1024 at return {res:#x}) $5ff8 at return {last}")
    check(f"[{label}] returned to the editor ({how})", back)
    if how == "bar": check(f"[{label}] the BAR ended it (tdvbl: why = 1)", why == 1)
    if how == "timeout": check(f"[{label}] the time-out ended it (tdvbl: why = 2)", why == 2)
    if how in ("esc", "f10"): check(f"[{label}] {how} ended it (neither BAR nor time-out)", why == 0)
    return after_return(label, snap0)

try:
    e.boot_editor(True)
    e.key(0x50, 3, 0.5); e.send(0x1c); time.sleep(1.0); e.key(0x50, a.level, 0.35); e.send(0x1c)
    check("viewer up", e.wait(lambda: e.vu("state") == 1, 60)); time.sleep(1.5); e.idle()
    # ---- real edits through the UI: bend keys (`.` = one step more to the right, `,` = to the left) at two segments, an inserted copy
    def seg_to(k):
        for _ in range(400):
            s = e.vu("seg")
            if s == k: return
            e.key(0x4d if s < k else 0x4b, 1, 0.1)
    for k, key, n in ((20, 0x34, 3), (60, 0x33, 4), (120, 0x34, 2)):
        seg_to(k); e.idle()
        for _ in range(n): e.send(key); time.sleep(0.25)
        e.idle()
    seg_to(100); e.idle(); e.send(0x17); e.idle()                                    # I = insert a copy behind
    e.send(0x47); e.idle()
    s0 = snapshot(); log(f"edited copy: {s0['nseg']} segments, {s0['nobj']} objects, vMod {s0['mod']}")
    check("the working copy is edited (vMod != 0)", s0["mod"] != 0)
    barat = e.vl("barat"); log("BAR at unit", barat)
    r.shot("1_edited")
    # ---- START
    one_drive("A_start", 0, "esc", barat, drive=5.0)
    # ---- MIDDLE
    one_drive("B_middle", 9000, "f10", barat, drive=3.0)
    if not a.quick:
        # ---- NEAR THE BAR: the finish
        one_drive("C_nearbar", barat - 1500, "bar", barat)
        # ---- time-out: standing still near the BAR
        one_drive("D_timeout", barat - 700, "timeout", barat)
    # ---- leave: the store keeps the edited track; the editor's normal PLAY and a normal campaign race with the shop
    e.send(0x01); check("Esc = back to the track list", e.wait(lambda: e.vu("state") == 0, 60)); time.sleep(2.0); r.shot("9_tracklist")
    if not a.nonormal:
        # normal PLAY THIS TRACK of the first campaign track (full race from unit 0 through the campaign), driven to the BAR, then the shop (real EXIT click) and the next race (position 1)
        e.send(0x1c); time.sleep(1.2); e.key(0x50, 1, 0.4); e.send(0x1c)
        got = None
        for _ in range(240):
            time.sleep(0.5)
            if r.l(0x23c0) != 0 and r.b(0x1024) == 0 and r.b(VTD) == 0: got = r.st("normal PLAY race up"); break
        check("normal PLAY THIS TRACK still works: a race stands, V_TD = 0, stream pointer in the campaign store, $5ff8 starts at 0, campaign position 0", got is not None and 0x110000 <= r.l(0x23c0) < 0x130000 and r.w(0x5ff8) < 50 and r.w(V["pos"]) == 0, f"$5ff8 {r.w(0x5ff8)} ptr {r.l(0x23c0):#x} pos {r.w(V['pos'])}")
        r.shot("10_normal_play")
        ok = r.drive_to_finish(tmo=300); r.st(f"normal race over (finished={ok})")
        check("the normal race is driven to the BAR (the full end sequence, not cut: $1024 = $ff)", ok)
        res = r.wait_race(tmo=300, press=True, shop=True)
        r.st("race after the shop"); r.shot("11_race_after_shop")
        check("shop EXIT click -> the next campaign race starts (position 1, V_TD = 0, $5ff8 starts at 0)", res is not None and r.w(V["pos"]) == 1 and r.b(VTD) == 0 and r.w(0x5ff8) < 50, f"{res} $5ff8 {r.w(0x5ff8)}")
    log(f"Bus/Address error lines in the Hatari log: {r.errlines()}")
except Exception:
    import traceback; log("EXCEPTION", traceback.format_exc()); FAILS.append("exception")
finally:
    e.close()
log(f"RESULT {a.tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
