#!/usr/bin/env python3
"""Cold boot a game folder to the TITLE screen (Billy Joe / Ike's cousin), screenshot + RAM dump + memstate.
   env.sh python3 title_snap.py --game DIR --machine ste --mem 2048 --out snap/NAME"""
import argparse, sys, time, os
from pathlib import Path
G = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools"))
from msr import Moonshine
from stharness import TOS
ap = argparse.ArgumentParser()
ap.add_argument("--game", required=True); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--tos"); ap.add_argument("--out", required=True); ap.add_argument("--dump", action="store_true")
a = ap.parse_args()
kw = {"tos": TOS[a.tos]} if a.tos else {}
h = Moonshine(machine=a.machine, memsize_kb=a.mem, game_dir=a.game, **kw)
try:
    ok = h.boot_to_race(log=lambda *x: None)
    print("boot_to_race (title or race)", ok, "vbl", h.vbl(), "$1021", h.peekb(0x1021), "$23c0", hex(h.peekl(0x23c0)), flush=True)
    time.sleep(2)
    h.shot(a.out + ".png")
    if a.dump:
        h.dump(a.out + ".bin", 0, a.mem * 1024); time.sleep(3)
    sav = Path(os.environ["HOME"]) / ".config/hatari/hatari.sav"
    sav.unlink(missing_ok=True); h.state = sav
    h.savemem(a.out + ".sav"); sav.unlink(missing_ok=True)
finally:
    h.close()
