#!/usr/bin/env python3
"""Track editor milestone 1 (the VIEWER) gates, HD build, cold boot (MSREditor).
   work/edgate/env.sh python3 work/edgate/eg.py --machine ste|megaste|st --mem 2048 [--build DIR] [--stock 0,7,14] [--quick] [--tag X]
One boot: title, F10, LOAD CAMPAIGN FROM HARD DISK (c3.trk), TRACK EDITOR (the overlay is read from FILES\\MSEDIT.OVL), then per track (campaign track 1, the stock tracks, a plain straight):
  * the model in RAM (segment list, object list, per-unit height / width arrays, path points) against tools/msrtrack.py (parse + expand_* + the render's path arithmetic);
  * a screenshot (logs/shots/<tag>_<track>.png) for cmpmap.py (map vs `msrtrack.py render`);
  * the cursor walk: RIGHT until the last segment (every key is a real IKBD scancode), the objects row, zoom, HOME / B;
then ESC back to the campaign menu (video base and palette restored), the loaded campaign is started, race 1 is driven to the BAR, the shop is left with the real EXIT click and race 2 runs."""
import argparse, json, math, sys, time, struct, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ.setdefault("CG_LOGS", str(HERE / "logs"))
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
import msrtrack as mt

ap = argparse.ArgumentParser()
ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--build", default="/tmp/msred/hd")
ap.add_argument("--stock", default="0,7,14"); ap.add_argument("--quick", action="store_true"); ap.add_argument("--tag"); ap.add_argument("--norace", action="store_true")
a = ap.parse_args()
short = f"{ {'ste': 'ste', 'megaste': 'mste', 'st': 'st', 'megast': 'mst'}[a.machine] }{a.mem // 1024}m"
tag = a.tag or f"view_{short}"
logopen(tag)
EV = 0x140000
SEGT, OBJT, HARR, WLARR, WRARR, PTS = EV + 0x3000, EV + 0x9000, EV + 0x10000, EV + 0x18000, EV + 0x20000, EV + 0x28000
TMP = Path("/tmp/msred"); TMP.mkdir(exist_ok=True)
camp = CAMP / "c3.trk"
ms2 = mt.read_ms2()

r = Run("hd", a.machine, a.mem, tag, build=a.build, camp_hd=camp, sound=True)
log(f"== {tag}: HD {MACH[a.machine]} {a.mem // 1024} MB, build {a.build}, sound on, campaign {camp.name}")


def ev():
    b = r.mem(EV, 146)
    return dict(nseg=W(b, 34), nobj=W(b, 36), total=L(b, 38), end=L(b, 42), rl=W(b, 46), base=W(b, 48), bart=W(b, 50), barat=struct.unpack(">i", b[52:56])[0], ntypes=W(b, 56), nbar=W(b, 58),
                seg=W(b, 60), pos=L(b, 62), obj=W(b, 66), focus=W(b, 68), zoom=W(b, 70), vstart=L(b, 72), state=W(b, 96), src=W(b, 98), srcix=W(b, 100), msel=W(b, 112), S=W(b, 80))


def grab(addr, n, name):
    p = TMP / f"{tag[:10]}_{name}.bin"
    if p.exists(): p.unlink()
    r.h.debug(f"savebin {p} ${addr:x} {n}", 0.6)
    for _ in range(40):
        if p.exists() and p.stat().st_size == n: break
        time.sleep(0.1)
    return p.read_bytes()


def union(t):
    """the editor's segment list from the four ring streams (msedit.s `parse`)"""
    st = [list(map(list, t[k])) for k in ("curve", "left", "right", "hill")]
    ix = [0, 0, 0, 0]; rem = [s[0][0] for s in st]; pos = 0; out = []
    while pos < 32768 and len(out) < 2048:
        n = min(min(rem), 32768 - pos)
        out.append((pos, n, st[0][ix[0]][1], st[3][ix[3]][1], st[1][ix[1]][1] & 0xff, st[2][ix[2]][1] & 0xff))
        pos += n; done = False
        for i in range(4):
            rem[i] -= n
            if rem[i] == 0:
                ix[i] += 1
                if ix[i] >= len(st[i]): done = True
                else: rem[i] = st[i][ix[i]][0]
        if done: break
    return out, pos


def path_fixed(curve, n):
    """msedit.s `expand`: mean curve value of 8 units, 4096-step sine table, accumulators world * 2^15, points world / 4"""
    sin = [round(32767 * math.sin(2 * math.pi * i / 4096)) for i in range(5120)]
    q = [round(32767 * math.sin(i * math.pi / 2048)) for i in range(1025)]
    for i in range(5120):                                  # the table as sin_init builds it from the quarter wave
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


def check_model(name, t, straight=False):
    """RAM model vs msrtrack.py for track dict t"""
    v = ev()
    base = t["base_level"]; rl = mt.LEVELS[base][mt.LEV_LEN]
    bar_types = {n + 1 for n, e in enumerate(t["types"]) if e[2] == mt.BAR_SPRITE}
    bars = [o["at"] for o in t["objects"] if o["type"] in bar_types]
    if straight:
        w = union(t)[0][0]
        segs, total = [(0, 32768, 0, 0, w[4], w[5])], 32768
        objs = [o for o in t["objects"] if o["type"] in bar_types][:1]
        cs, ls, rs, hs = [[32768, 0]], [[32768, w[4]]], [[32768, w[5]]], [[32768, 0]]
    else:
        segs, total = union(t); objs = t["objects"]
        cs, ls, rs, hs = t["curve"], t["left"], t["right"], t["hill"]
    end = min(total, max(rl + 1024, (bars[0] + 512) if bars else 0)) & ~7
    log(f"[{name}] editor: nseg={v['nseg']} nobj={v['nobj']} total={v['total']} end={v['end']} rl={v['rl']} base={v['base']} bartype={v['bart']} bar_at={v['barat']} nbar={v['nbar']} ntypes={v['ntypes']} scale={v['S']}")
    log(f"[{name}] msrtrack: nseg={len(segs)} nobj={len(objs)} total={total} end={end} rl={rl} base={base} bartype={sorted(bar_types)} bar_at={bars} ntypes={len(t['types'])}")
    ok = check(f"{name}: counts, extent, base, BAR", (v["nseg"], v["nobj"], v["total"], v["end"], v["rl"], v["base"], v["ntypes"], v["nbar"]) == (len(segs), len(objs), total, end, rl, base, len(t["types"]), len(bars[:1]) if straight else len(bars))
               and (not bars or v["barat"] == bars[0]) and v["bart"] in bar_types)
    sb = grab(SEGT, 12 * max(v["nseg"], 1), "seg")
    got = [struct.unpack(">HHhhBB", sb[12 * i:12 * i + 10]) for i in range(v["nseg"])]
    exp = [(s[0], s[1] & 0xffff, s[2], s[3], s[4], s[5]) for s in segs]
    bad = [i for i, (g, e) in enumerate(zip(got, exp)) if g != e]
    check(f"{name}: segment list == union of the four streams ({len(exp)} segments)", got == exp, f"first diff {bad[:1]} {got[bad[0]] if bad else ''} {exp[bad[0]] if bad else ''}")
    ob = grab(OBJT, 8 * max(v["nobj"], 1), "obj")
    gobj = [struct.unpack(">HHhH", ob[8 * i:8 * i + 8]) for i in range(v["nobj"])]
    eobj = [(o["at"], o["type"], o["lateral"], 1 if o["type"] in bar_types else 0) for o in objs]
    check(f"{name}: object list ({len(eobj)} objects, BAR flagged)", gobj == eobj)
    n = end
    eh, _ = mt.expand_hill(hs, n); el = mt.expand_width(ls, n); er = mt.expand_width(rs, n); ec = mt.expand_curve(cs, n)
    gh, gl, gr = grab(HARR, n, "h"), grab(WLARR, n, "wl"), grab(WRARR, n, "wr")
    check(f"{name}: height / left / right arrays == msrtrack expand_* over {n} units", list(gh) == eh and list(gl) == el and list(gr) == er,
          f"h {sum(x != y for x, y in zip(gh, eh))} wl {sum(x != y for x, y in zip(gl, el))} wr {sum(x != y for x, y in zip(gr, er))} differing")
    pb = grab(PTS, 4 * (n // 8 + 1), "pts")
    gp = [struct.unpack(">hh", pb[4 * i:4 * i + 4]) for i in range(n // 8 + 1)]
    ep = path_fixed(ec, n)
    check(f"{name}: path points == the fixed-point model ({len(ep)} points)", gp == ep, f"{sum(x != y for x, y in zip(gp, ep))} differing")
    # the float path of msrtrack.py render_png (x += sin(c/600), y += cos(c/600) per unit) against the editor's points, in map pixels at zoom 0
    x = y = 0.0; dev = 0.0
    for i in range(n):
        th = ec[i] / 600.0; x += math.sin(th); y += math.cos(th)
        if (i + 1) % 8 == 0:
            px, py = gp[(i + 1) // 8]
            dev = max(dev, math.hypot(px * 4 - x, -py * 4 - y))
    pxdev = dev / 4 * v["S"] / 65536
    check(f"{name}: path vs msrtrack.py render arithmetic", pxdev < 1.0, f"max deviation {dev:.1f} units = {pxdev:.2f} map pixels (scale {v['S'] / 65536 / 4:.5f} px/unit)")
    return v, exp, eobj


def send(sc):
    """one key as an ST scancode.  `hatari-event keypress N` takes a ONE-character argument as an ASCII character (control.c Control_InsertKey: `keypress 1` types the key '1', not Esc),
    so the scancode is always sent as 0xNN"""
    r.h.cmd(f"hatari-event keypress 0x{sc:02x}")


def goto_item(n):
    """campaign menu: move the bar to item n (M_SEL = $100406)"""
    for _ in range(10):
        s = r.w(0x100406)
        if s == n: return True
        send(0x50 if s < n else 0x48); time.sleep(0.6)
    return r.w(0x100406) == n


def key(sc, n=1, dt=0.13):
    for _ in range(n): send(sc); time.sleep(dt)


def wait_state(s, tmo=20):
    t0 = time.time()
    while time.time() - t0 < tmo:
        if ev()["state"] == s: return True
        time.sleep(0.3)
    return False


def walk(name, segs, objs, end, full):
    """RIGHT segment by segment to the last one that starts inside the extent; the status follows; then LEFT, objects row, zoom, HOME / B"""
    last = max(i for i, s in enumerate(segs) if s[0] < end)
    v = ev(); check(f"{name}: cursor starts at segment 1, unit 0, road row, zoom 1", (v["seg"], v["pos"], v["focus"], v["zoom"]) == (0, 0, 0, 0))
    lost = 0; i = 0; trace = []
    target = last if full else min(last, 25)
    while i < target:
        nstep = min(20, target - i); key(0x4d, nstep); time.sleep(0.25)
        v = ev()
        if v["seg"] != i + nstep: lost += 1; log(f"[{name}] walk: after {i + nstep} RIGHTs seg={v['seg']} pos={v['pos']}")
        i = v["seg"]; trace.append((v["seg"], v["pos"]))
        if v["pos"] != segs[v["seg"]][0]: check(f"{name}: cursor on a segment start", False, f"seg {v['seg']} pos {v['pos']} start {segs[v['seg']][0]}"); break
        if lost > 5: break
    log(f"[{name}] walk samples (seg, unit) every 20 keys: {trace[:4]} ... {trace[-3:]}")
    check(f"{name}: RIGHT walked {'the whole track' if full else 'the first segments'}: segment {target + 1} of {len(segs)} reached, unit = its start", ev()["seg"] == target and ev()["pos"] == segs[target][0], f"batches with a wrong count: {lost}")
    if full:
        key(0x4d, 3); v = ev(); check(f"{name}: RIGHT at the last segment stays", v["seg"] == last)
        r.shot(f"{name}_end")
    key(0x4b, 2); time.sleep(0.3); v = ev(); check(f"{name}: LEFT twice", v["seg"] == target - 2 and v["pos"] == segs[target - 2][0], f"seg {v['seg']}")
    key(0x47); time.sleep(0.4); v = ev(); check(f"{name}: CLR/HOME = unit 0", v["pos"] == 0 and v["seg"] == 0)
    key(0x30); time.sleep(0.4); v = ev(); bars = [o[0] for o in objs if o[3]]
    check(f"{name}: B = the BAR", bars and v["pos"] == min(bars[0], end - 1), f"pos {v['pos']} bar {bars[:1]}")
    key(0x4e, 3, 0.5); time.sleep(0.5); v = ev(); check(f"{name}: + three times = zoom 4, strips centred on the cursor", v["zoom"] == 3 and v["vstart"] <= v["pos"] < v["vstart"] + 256 * 16, f"zoom {v['zoom']} vstart {v['vstart']}")
    r.shot(f"{name}_zoom4")
    key(0x47); time.sleep(0.5)
    key(0x50); time.sleep(0.4); v = ev(); check(f"{name}: DOWN = objects row, first object", v["focus"] == 1 and v["obj"] == 0 and v["pos"] == min(objs[0][0], end - 1), f"{v['focus']} {v['obj']} {v['pos']}")
    if len(objs) > 4:
        key(0x4d, 4); time.sleep(0.4); v = ev(); check(f"{name}: RIGHT x4 in the objects row = object 5", v["obj"] == 4 and v["pos"] == objs[4][0], f"obj {v['obj']} pos {v['pos']}")
    r.shot(f"{name}_objects")
    key(0x48); time.sleep(0.3); key(0x4a, 3, 0.5); time.sleep(0.4); v = ev(); check(f"{name}: UP = road row, - three times = zoom 1", v["focus"] == 0 and v["zoom"] == 0)


def view_checks(name, t, full, straight=False):
    check(f"{name}: viewer is up", wait_state(1))
    time.sleep(1.2)
    r.shot(name)
    v, segs, objs = check_model(name, t, straight)
    walk(name, segs, objs, v["end"], full)
    key(0x01); check(f"{name}: ESC = back to the track list", wait_state(0)); time.sleep(0.6)


try:
    ok = r.boot_title()
    log(f"title reached: {ok} vbl {r.vbl()}"); check("title reached", ok)
    mk = probe_boot(r)
    r.menu_open(); time.sleep(1); r.shot("0_menu")
    base0 = r.mem(0xff8201, 3); pal0 = r.mem(0xff8240, 32)
    log(f"campaign menu: video base {base0[0]:02x}{base0[2]:02x}00 palette {pal0.hex()}")
    # load the campaign from the HD copy (item 1), leave its track list through the "< BACK" row (as campgate.py does)
    check("main menu: item 1 (LOAD CAMPAIGN FROM HARD DISK)", goto_item(1))
    send(0x1c); t0 = time.time()
    while time.time() - t0 < 60 and not r.b(V["loaded"]): time.sleep(0.5)
    check("campaign c3.trk loaded from FILES", r.b(V["loaded"]) != 0 and r.w(V["count"]) == 3)
    time.sleep(2.5); check("play list: < BACK row", goto_item(3)); send(0x1c); time.sleep(2.0)
    # TRACK EDITOR = item 4 (ORIGINAL GAME, HARD DISK, DRIVE A, LOADED CAMPAIGN, TRACK EDITOR, BACK)
    goto_item(4)
    r.shot("1_menu_editor_item"); err0 = r.errlines(); log(f"Bus/Address error lines before the editor is opened: {err0}")
    check("TRACK EDITOR item selected, overlay not loaded yet", r.w(0x100406) == 4 and r.b(0xb8e0c) == 0 and r.l(0x130000) == 0, f"sel {r.w(0x100406)} V_EDOK {r.b(0xb8e0c):#x} $130000 {r.l(0x130000):#x}")
    v0 = r.vbl(); send(0x1c); t0 = time.time()
    while time.time() - t0 < 30 and r.b(0xb8e0c) == 0: time.sleep(0.2)
    ovl = (Path(a.build) / "FILES" / "MSEDIT.OVL").read_bytes()
    time.sleep(1.0)
    got = grab(0x130000, len(ovl), "ovl")
    check("MSEDIT.OVL read to $130000 and accepted (V_EDOK), RAM == the file", r.b(0xb8e0c) == 0xff and got == ovl, f"{len(ovl)} B, {r.vbl() - v0} VBL after RETURN (includes the wait)")
    vb = r.mem(0xff8201, 3)
    check("editor screen: video base $170000", (vb[0], vb[2]) == (0x17, 0x00), f"{vb[0]:02x}{vb[2]:02x}00")
    r.shot("2_tracklist")
    # ---- campaign track 1
    ents = mt.parse_campaign(camp.read_bytes())
    t, _ = mt.entry_track(ents[0])
    check("track list: 3 campaign tracks + 3 items, selection 0", ev()["msel"] == 0 and W(r.mem(EV + 110, 2)) == 6)
    send(0x1c)
    view_checks("camp1", t, full=True)
    # ---- stock tracks: item 3 (COPY OF AN ORIGINAL TRACK >), then the track
    for n, lev in enumerate(int(x) for x in a.stock.split(",") if x != ""):
        key(0x50, 3, 0.4); send(0x1c); time.sleep(1.0)
        if n == 0: r.shot("3_stocklist")
        key(0x50, lev, 0.3); time.sleep(0.3)
        check(f"stock list: TRACK {lev + 1:02d} selected", ev()["msel"] == lev)
        v0 = r.vbl(); send(0x1c)
        t, _ = mt.decode_stock(ms2, lev)
        ok = wait_state(1); log(f"[stock{lev}] loaded and expanded in {r.vbl() - v0} VBL (includes polling)")
        view_checks(f"stock{lev}", t, full=(not a.quick) or n == 0)
    # ---- plain straight on the scenery of track 4 (level 3)
    key(0x50, 4, 0.4); send(0x1c); time.sleep(1.0); key(0x50, 3, 0.3); send(0x1c)
    t, _ = mt.decode_stock(ms2, 3)
    check("straight: viewer is up", wait_state(1)); time.sleep(1.2); r.shot("straight")
    v, segs, objs = check_model("straight", t, straight=True)
    key(0x62); time.sleep(1.0); check("HELP page", ev()["state"] == 3); r.shot("help"); key(0x39); time.sleep(0.8)
    r.poke(0x6105, 0x80); time.sleep(0.4); r.poke(0x6105, 0x00); time.sleep(1.0)          # fire tapped = the menu
    check("FIRE = viewer menu", ev()["state"] == 2); r.shot("vmenu")
    key(0x50, 7, 0.3); send(0x1c); check("menu item LEAVE THIS TRACK = back to the track list", wait_state(0)); time.sleep(0.5)
    # ---- back to the campaign menu, the game intact
    key(0x01); time.sleep(2.0)
    base1 = r.mem(0xff8201, 3); pal1 = r.mem(0xff8240, 32)
    check("ESC = campaign menu: video base and palette as before the editor", (base1[0], base1[2]) == (base0[0], base0[2]) and pal1 == pal0, f"base {base1[0]:02x}{base1[2]:02x}00 was {base0[0]:02x}{base0[2]:02x}00")
    r.shot("4_menu_after"); log(f"menu selection after the editor: {r.w(0x100406)}")
    check("no Bus/Address error line while the editor was open", r.errlines() == err0, f"{err0} -> {r.errlines()}")
    if not a.norace:
        goto_item(3)
        send(0x1c); time.sleep(2); r.shot("5_playlist"); send(0x1c)                     # LOADED CAMPAIGN -> PLAY FROM TRACK 1
        res = r.play_races(1, "race")
        check("race 1 = campaign track 1 from the store, driven to the BAR", len(res) == 1 and 0x110000 <= res[0][2] < 0x130000 and r.b(0x1024) == 0xff, f"{res}")
        r2 = r.wait_race(tmo=240, label="race2")                                          # the shop is left with the real EXIT click
        r.st("race 2 start"); r.shot("race2")
        check("race 2 started after the shop (EXIT click): campaign track 2, base level 3", r2 is not None and r2[1] == 3 and r2[3] == 1, f"{r2}")
        r.poke(0x6105, 0x01); time.sleep(8); p1 = r.w(0x5ff8); time.sleep(4); p2 = r.w(0x5ff8); sp = r.w(0x130c); r.poke(0x6105, 0x00)
        check("race 2 runs: the car moves", p2 > p1 > 0, f"$5ff8 {p1} -> {p2}, speed $130c {sp}")
    mk2 = r.mem(0xb2700, 5)
    check("marker MSPO, gate open, at the end", mk2[:4] == b"MSPO" and mk2[4] == 0xff)
    log(f"Bus/Address error lines in the Hatari log at the end: {r.errlines()}")
except Exception as e:
    import traceback; log("EXCEPTION", traceback.format_exc()); FAILS.append("exception")
finally:
    r.close()
log(f"RESULT {tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
