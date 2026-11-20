#!/usr/bin/env python3
"""Cold boot a game folder (STE, 1 MB) to the first race, shoot the standing start, drive for N seconds, shoot again, report liveness.
(derived from work/trackstudy/run_race.py: same boot recipe, own output dir, private HOME, drive time as a parameter)

    python3 work/trackedit/run_race.py GAMEDIR TAG [--drive-s 60] [--out work/trackedit/shots]
"""
import argparse
import os
import sys
import time
from pathlib import Path

G = Path(__file__).resolve().parents[2]
os.environ["HOME"] = f"/tmp/msrtrack_home_{os.getpid()}"          # private HOME: Hatari writes its config there, never the real one
Path(os.environ["HOME"]).mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(G / "tools"))
sys.path.insert(0, str(G.parent.parent.parent / "tools"))
from msr import Moonshine   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("gamedir")
ap.add_argument("tag")
ap.add_argument("--drive-s", type=int, default=60)
ap.add_argument("--out", default=str(G / "work/trackedit/shots"))
a = ap.parse_args()
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
h = Moonshine(game_dir=a.gamedir, workdir=f"/tmp/msrtrack_{a.tag}")
try:
    ok = h.boot_to_race()
    print("in_race", ok, "vbl", h.vbl(), flush=True)
    for k in range(12):          # in_race can fire on the title screen: SPACE until the race is set up ($23c0 = track stream pointer)
        if h.peekl(0x23c0) != 0 and h.peekw(0x100e) > 30:
            break
        h.keypress(57)
        time.sleep(6)
        print("wait race", k, "vbl", h.vbl(), "23c0", hex(h.peekl(0x23c0)), "100e", h.peekw(0x100e), flush=True)
    time.sleep(3.0)
    print("102c", hex(h.peekw(0x102c)), "5ff8", h.peekw(0x5ff8), "130c", h.peekw(0x130c), "100e", h.peekw(0x100e), flush=True)
    for n in range(2):
        h.shot(str(out / f"{a.tag}_grid{n}.png"))
        time.sleep(0.5)
    print(h.debug("m $1bb0 8"), h.debug("m $23c0 4"), flush=True)
    print(h.debug("m $1bbc 32"), flush=True)
    print(h.debug("m $13b0 16"), h.debug("m $17b0 16"), h.debug("m $23c8 16"), flush=True)
    h.drive(True)
    t0 = time.time()
    k = 0
    while time.time() - t0 < a.drive_s:
        time.sleep(10)
        k += 1
        print(f"drive t={time.time() - t0:4.0f}s vbl {h.vbl()} 5ff8 {h.peekw(0x5ff8)} 130c {h.peekw(0x130c)} 1021 {h.peekb(0x1021)} 102c {h.peekw(0x102c):#x}", flush=True)
        if k in (1, 3, 6):
            h.shot(str(out / f"{a.tag}_drive{k}.png"))
    h.drive(False)
    print("END alive after", int(time.time() - t0), "s of driving; vbl", h.vbl(), "5ff8", h.peekw(0x5ff8), flush=True)
finally:
    h.close()
