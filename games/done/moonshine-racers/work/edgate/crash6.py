#!/usr/bin/env python3
"""FUZZ: PLAIN STRAIGHT in the editor, random user-like edits (length / copy / split / merge / delete / hill / curve / widths / add object / object type / side / Tab), then P from the cursor, a short drive, Esc, repeat.
The segment and object lists before every P are saved to /tmp/msrcrash/fuzz/<tag>_<n>.json; stops at the first Address Error / unexpected Bus Error.
work/edgate/envcrash.sh python3 work/edgate/crash6.py --tag T --seed N --iters 30 [--level 0]"""
import argparse, random, json, re as _re
import ed2lib
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="crash6"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--machine", default="ste")
ap.add_argument("--seed", type=int, default=1); ap.add_argument("--iters", type=int, default=30); ap.add_argument("--level", type=int, default=0); ap.add_argument("--ops", type=int, default=6); ap.add_argument("--drive", type=float, default=3.0)
a = ap.parse_args()
VTD = 0xb8e0e
OUT = Path("/tmp/msrcrash/fuzz"); OUT.mkdir(exist_ok=True, parents=True)
e = Ed(a.tag, a.machine, 2048, a.build, None); r = e.r
rnd = random.Random(a.seed)
_idle = e.idle
e.idle = lambda tmo=8: _idle(tmo)
def bad():
    out = []
    for l in r.h._logtext().splitlines():
        if "Address Error" in l: out.append(l)
        elif "Bus Error" in l:
            m = _re.search(r"at address \$([0-9a-f]+)", l)
            if not m or (int(m.group(1), 16) & 0xffffff) < 0xff8000: out.append(l)
    return out
def back_to_grid():
    if e.vu("focus"): e.send(0x0f); e.wait(lambda: e.vu("focus") == 0, 5, 0.1)
def pick(key, what):
    e.send(key)
    if not e.wait(lambda: e.vu("lopen") == 1, 8, 0.2): log(f"   {what}: list did not open: state {e.vu('state')} focus {e.vu('focus')} lopen {e.vu('lopen')} msg '{e.msgtext()}'"); r.shot(f"pickfail_{what.replace(' ', '_')}"); return
    time.sleep(0.3); cnt = e.vu("lcnt") + 1; idx = rnd.randrange(cnt); e.list_goto(idx); e.settle()
    bad_ = e.vu("lbad"); val = e.v("lval")
    e.send(0x01 if bad_ else 0x1c); e.wait(lambda: e.vu("lopen") == 0, 20, 0.2); e.idle()
    log(f"   {what}: idx {idx} value {val}" + (" refused" if bad_ else ""))
def op():
    if e.vu("lopen") or e.vu("state") != 1:
        log(f"   (stray state: lopen {e.vu('lopen')} state {e.vu('state')}: Esc)"); r.shot("stray"); e.send(0x01); time.sleep(1.0)
    k = rnd.randrange(max(1, e.vu("nseg"))); back_to_grid()
    c = rnd.choice(["len", "len", "copy", "copy", "copy", "split", "split", "hill", "hill", "curve", "wl", "wr", "obj", "obj", "obj", "obj", "obj", "objtype", "objtype", "objtype", "objside", "tab"])
    if c in ("len", "copy", "split", "merge", "del", "hill", "curve", "wl", "wr", "obj"): e.seg_goto(min(k, e.vu("nseg") - 1)); e.idle()
    log(f"  op {c} at seg {e.vu('seg')} (of {e.vu('nseg')}, {e.vu('nobj')} objects)")
    if c == "len": pick(0x26, "length")
    elif c == "copy": e.send(0x17); e.idle()
    elif c == "split": e.send(0x1f); e.idle()
    elif c == "merge": e.send(0x32); e.idle()
    elif c == "del": e.send(0x53); e.idle()
    elif c == "hill": pick(0x23, "hill")
    elif c == "curve": pick(0x2e, "curve")
    elif c == "wl": pick(0x11, "width L")
    elif c == "wr": pick(0x12, "width R")
    elif c == "obj": e.send(0x18); time.sleep(0.4); e.idle(); log(f"   object added? focus {e.vu('focus')} nobj {e.vu('nobj')}")
    elif c == "objtype":
        e.send(0x0f); e.wait(lambda: e.vu("focus") == 1, 3, 0.1)
        if e.vu("focus"): pick(0x14, "object type")
    elif c == "objside":
        e.send(0x0f); e.wait(lambda: e.vu("focus") == 1, 3, 0.1)
        if e.vu("focus"): pick(0x1f, "object side")
    elif c == "tab": e.send(0x0f); e.idle()
try:
    e.boot_editor(False)
    check("viewer up", e.open_track("straight", a.level, ntr=0))
    for it in range(a.iters):
        log(f"== iteration {it}")
        for _ in range(a.ops):
            try: op()
            except Exception as ex: log("   op failed:", repr(ex))
        e.idle(); back_to_grid()
        if rnd.random() < 0.6: e.seg_goto(0); e.idle()
        sg, ob = e.segs(), e.objs(); json.dump({"segs": sg, "objs": ob, "barat": e.vl("barat"), "pos": e.vl("pos"), "seg": e.vu("seg")}, open(OUT / f"{a.tag}_{it}.json", "w"))
        log(f"   P from unit {e.vl('pos')} (seg {e.vu('seg')}): {len(sg)} segments, {len(ob)} objects, length sum {sum(s[1] for s in sg)}")
        hit0 = r.w(EV + VAR["tdhit"]); e.send(0x19); t0 = time.time(); up = False; msg = ""
        while time.time() - t0 < 45 and not bad():
            time.sleep(0.4)
            try:
                if r.w(EV + VAR["tdhit"]) > hit0 and r.b(0x1024) == 0 and r.b(VTD) == 0xff: up = True; break
                if e.vu("state") == 1 and r.b(VTD) == 0 and time.time() - t0 > 3: msg = e.msgtext(); break          # refused (behind the BAR etc.)
            except Exception: pass
        if bad(): log(f"   CRASH at the start: {bad()[:2]}"); break
        if not up: log(f"   no race: '{msg}'"); continue
        time.sleep(0.5); e.jpoke(1); time.sleep(a.drive); e.jpoke(0)
        log(f"   race up, $5ff8 {r.w(0x5ff8)} bad {len(bad())}")
        if bad(): log(f"   CRASH while driving: {bad()[:2]}"); break
        if r.b(VTD) == 0xff: e.send(0x01)                                  # (a race the BAR / the time bar already ended returns by itself: an Esc then would leave the editor)
        ok = e.wait(lambda: r.b(VTD) == 0 and e.vu("state") == 1 and e.vu("redraw") == 0 and r.b(0x1028) == 0, 60)
        log(f"   back in the editor: {ok}")
        if not ok: break
        for w in (0.5, 1.5, 3.0):
            time.sleep(w); log(f"   +{w}s: state {e.vu('state')} redraw {e.vu('redraw')} V_TD {r.b(VTD)} $1028 {r.b(0x1028)} $1024 {r.b(0x1024):#x} $100e {r.w(0x100e)} $5ff8 {r.w(0x5ff8)} msg '{e.msgtext()}' vTdWhy {r.b(EV + VAR['tdwhy'])} nseg {e.vu('nseg')}")
        if e.vu("state") != 1: r.shot(f"after_td_{it}"); log("   STATE LOST after the test drive"); break
        e.idle()
    r.shot("end")
finally:
    e.close()
log("RESULT", a.tag, "CRASH" if bad() else "no error")
