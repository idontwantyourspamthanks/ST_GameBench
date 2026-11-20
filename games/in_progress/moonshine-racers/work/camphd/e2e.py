#!/usr/bin/env python3
"""HD campaign end-to-end from the title snapshot (campaign patches applied live): F10 menu -> load -> Play from track N -> race(s).
   env.sh python3 e2e.py --snap snap/ste2m_title.sav --machine ste --mem 2048 --src hd|a --camp c3 [--track 0] [--races 3]"""
import argparse, sys, time, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cplib import *
ap = argparse.ArgumentParser()
ap.add_argument("--snap", default=str(HERE / "snap/ste2m_title.sav")); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--tos"); ap.add_argument("--src", default="hd"); ap.add_argument("--camp", default="c3"); ap.add_argument("--track", type=int, default=0)
ap.add_argument("--races", type=int, default=1); ap.add_argument("--tag", default="e2e"); ap.add_argument("--build", default="b2")
ap.add_argument("--drive-wait", type=float, default=30)
a = ap.parse_args()
camp = HERE / "camp"
gd = HERE / f"run_{a.tag}"; shutil.rmtree(gd, ignore_errors=True); shutil.copytree(HERE / a.build, gd)
extra = []
if a.src == "hd":
    shutil.copy(camp / f"{a.camp}.trk", gd / "FILES" / "MSTRACKS.TRK")
else:
    extra = ["--disk-a", str(camp / f"{a.camp}.st")]
h = Moonshine(snapshot=a.snap, game_dir=str(gd), machine=a.machine, memsize_kb=a.mem, extra=extra, **({"tos": TOS[a.tos]} if a.tos else {}))
shot = lambda n: h.shot(str(HERE / f"snap/{a.tag}_{n}.png"))
def st(tag):
    log(f"[{tag}] vbl={h.vbl()} $102c={W(mem(h,0x102c,2)):#06x} CPV={mem(h,0xb8e00,12).hex()} $57890.len={W(mem(h,0x57890,2))} $23c0={L(mem(h,0x23c0,4)):#x} $1024={mem(h,0x1024,1).hex()} $1021={mem(h,0x1021,1).hex()} $100e={W(mem(h,0x100e,2))} $5ff8={W(mem(h,0x5ff8,2))} $10ce={W(mem(h,0x10ce,2))}")
try:
    time.sleep(2)
    apply_live(h)
    h.keypress(0x44); time.sleep(3); shot("1_main")
    for i in range(a.src == "a" and 2 or 1):
        h.keypress(0x50); time.sleep(0.6)                       # Down
    shot("2_sel")
    h.keypress(0x1c)                                          # Return = load
    t0 = time.time()
    if a.src == "a":
        time.sleep(3); shot("3_loading")
    ok = False
    while time.time() - t0 < a.drive_wait:
        time.sleep(1)
        if mem(h, 0xb8e01, 1)[0]:
            ok = True; break
    log("loaded flag", ok, f"after {time.time()-t0:.1f}s; COUNT", W(mem(h, 0xb8e02, 2)), "first bytes of store", mem(h, 0x110000, 16).hex())
    time.sleep(1.5); shot("4_list")
    for i in range(a.track):
        h.keypress(0x50); time.sleep(0.4)
    shot("5_list_sel")
    h.keypress(0x1c)                                          # Return = play from track
    time.sleep(2); st("after play key")
    races = 0
    t0 = time.time(); lastp = None
    while time.time() - t0 < 900 and races < a.races:
        time.sleep(5)
        s = (W(mem(h, 0x1024, 2)) >> 8, W(mem(h, 0x100e, 2)), L(mem(h, 0x23c0, 4)))
        if s[2] and s[1] > 30 and (mem(h, 0x6105, 1)[0] & 1) == 0:
            h.debug("w $6105 $01", 0.3)                       # drive: joystick up
            st("race start"); shot(f"6_race{races}")
        if s[2] and s[1] > 30:
            pass
        else:
            h.keypress(57)                                    # SPACE through the screens
        if s[0] == 0xff or mem(h, 0x1024, 1)[0] == 0xff:
            st("race over"); shot(f"7_over{races}"); races += 1; h.debug("w $6105 $00", 0.3)
            time.sleep(8)
    st("end")
finally:
    h.close()
