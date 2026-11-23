#!/usr/bin/env python3
"""Milestone 2c smoke: boot the HD build to the editor, screenshot the grid, dump the new variables.  env6.sh python3 smoke6.py [--kind stock|straight|none] [--machine ste] [--mem 2048] [--tag T]"""
import argparse, os, sys, time, struct
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--kind", default="stock"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--tag", default=None); ap.add_argument("--build", default=os.environ.get("ED_BUILD", "/tmp/msred6/hd")); ap.add_argument("--level", type=int, default=3)
a = ap.parse_args()
short = {'ste':'ste','megaste':'mste','st':'st','megast':'mst'}[a.machine] + f"{a.mem//1024}m"
tag = a.tag or f"smoke6_{a.kind}_{short}"
logopen(tag)
EV = 0x140000
V = dict(nseg=34,nobj=36,total=38,end=42,rl=46,base=48,bart=50,barat=52,ntypes=56,nbar=58,seg=60,pos=62,obj=66,focus=68,
         first=70,tok=72,ocnt=74,of=76,otop=78,page=80,redraw=88,state=96,src=98,srcix=100,mod=200,lopen=254,vmsg=102,play=278)
camp = CAMP / "c3.trk" if a.kind == "stock" else None
r = Run("hd", a.machine, a.mem, tag, build=a.build, camp_hd=camp, sound=True)
def v(name, size=2):
    b = r.mem(EV + V[name], size)
    return struct.unpack(">h" if size == 2 else ">i", b)[0]
try:
    ok = r.boot_title(); log(f"title: {ok}"); r.menu_open(); time.sleep(1)
    log("marker", r.mem(0xb2700,5).hex(), "IB+4", r.b(0xb2704), "$2dc", hex(r.l(0x2dc)))
    def goto_item(n):
        for _ in range(12):
            s = r.w(0x100406)
            if s == n: return True
            r.h.cmd(f"hatari-event keypress {'0x50' if s < n else '0x48'}"); time.sleep(0.6)
        return r.w(0x100406) == n
    if a.kind == "stock":
        goto_item(1); r.h.cmd("hatari-event keypress 0x1c"); t0=time.time()
        while time.time()-t0<60 and not r.b(0xb8e01): time.sleep(0.5)
        time.sleep(2.5); goto_item(3); r.h.cmd("hatari-event keypress 0x1c"); time.sleep(1.5); goto_item(4)
    else:
        goto_item(3)
    r.h.cmd("hatari-event keypress 0x1c"); t0=time.time()
    while time.time()-t0<30 and r.b(0xb8e0c)==0: time.sleep(0.2)
    time.sleep(1.0)
    log("V_EDOK", r.b(0xb8e0c), "state", v("state"))
    r.shot("1_tracklist")
    if a.kind == "stock":
        for _ in range(3): r.h.cmd("hatari-event keypress 0x50"); time.sleep(0.5)
        r.h.cmd("hatari-event keypress 0x1c"); time.sleep(1.0)
        for _ in range(a.level): r.h.cmd("hatari-event keypress 0x50"); time.sleep(0.35)
    elif a.kind == "straight":
        r.h.cmd("hatari-event keypress 0x50"); time.sleep(0.5); r.h.cmd("hatari-event keypress 0x1c"); time.sleep(1.0)
        for _ in range(a.level): r.h.cmd("hatari-event keypress 0x50"); time.sleep(0.35)
    r.h.cmd("hatari-event keypress 0x1c"); time.sleep(2.0)
    log("state", v("state"), "nseg", v("nseg"), "nobj", v("nobj"), "end", v("end",4), "base", v("base"), "barat", v("barat",4))
    log("first", v("first"), "tok", v("tok"), "seg", v("seg"), "pos", v("pos",4), "OCnt", v("ocnt"), "OF", v("of"), "redraw", v("redraw"))
    r.shot("2_grid")
    for i in range(3):
        r.h.cmd("hatari-event keypress 0x4d"); time.sleep(0.5)
        log(f"after RIGHT {i+1}: seg", v("seg"), "pos", v("pos",4), "first", v("first"), "ocnt", v("ocnt"))
    r.shot("3_moved")
    # tab into the object list if the segment has objects
    r.h.cmd("hatari-event keypress 0x0f"); time.sleep(0.8)
    log("focus", v("focus"), "obj", v("obj"), "ocnt", v("ocnt"))
    r.shot("4_objects")
    r.h.cmd("hatari-event keypress 0x62"); time.sleep(1.2); r.shot("5_help1")
    r.h.cmd("hatari-event keypress 0x39"); time.sleep(1.2); r.shot("6_help2")
    r.h.cmd("hatari-event keypress 0x39"); time.sleep(1.2)
    log("state", v("state"))
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
log(f"RESULT {tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
