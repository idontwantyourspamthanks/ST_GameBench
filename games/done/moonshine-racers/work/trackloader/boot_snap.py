#!/usr/bin/env python3
"""Cold boot a game folder to the first race (tools/msr.py recipe) and save a memstate + a few raw peeks.
   run via work/trackloader/run_hatari_env.sh (private HOME, local Hatari).
   boot_snap.py --game DIR --machine ste --mem 4096 --out work/trackloader/snap/NAME [--tos 2.06] [--dump]"""
import argparse, sys, time, shutil, os
from pathlib import Path
G = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools"))
from msr import Moonshine
from stharness import TOS
ap = argparse.ArgumentParser()
ap.add_argument("--game", required=True); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
ap.add_argument("--tos"); ap.add_argument("--out", required=True); ap.add_argument("--dump", action="store_true", help="also savebin all RAM")
a = ap.parse_args()
kw = {"tos": TOS[a.tos]} if a.tos else {}
h = Moonshine(machine=a.machine, memsize_kb=a.mem, game_dir=a.game, **kw)
try:
    ok = h.boot_to_race()
    print("boot_to_race (true already on the TITLE screen: $1021=2 there) =", ok, "vbl", h.vbl(), flush=True)
    # press SPACE until the race loop really runs: track stream pointer $23c0 set up and the loop counter $100e > 30
    for k in range(14):
        if ok and h.peekl(0x23c0) != 0 and h.peekw(0x100e) > 30 and h.peekw(0x100e) < 1000: break
        h.keypress(57); time.sleep(6)
        print("wait race", k, "vbl", h.vbl(), "$23c0", hex(h.peekl(0x23c0)), "$100e", h.peekw(0x100e), "$1021", h.peekb(0x1021), flush=True)
    time.sleep(2)
    ok = h.peekl(0x23c0) != 0 and h.peekw(0x100e) > 30
    print("RESULT in_race =", ok, "vbl", h.vbl(), "$102c", h.peekw(0x102c), "$5ff8", h.peekw(0x5ff8), "$130c", h.peekw(0x130c))
    for ad in (0x2dc, 0x42e, 0x436, 0x1021):
        print(f"PEEK ${ad:x}:", h.debug(f"m ${ad:x} 16", 0.8).strip())
    if ok:
        time.sleep(2)
        h.shot(a.out + ".png")
        if a.dump:
            h.dump(a.out + ".bin", 0, a.mem * 1024)
            time.sleep(3)
        # where does the shortcut write the memstate?
        # the shortcut writes $HOME/.config/hatari/hatari.sav (private HOME); Hatari blocks on an overwrite dialog if it exists
        sav = Path(os.environ["HOME"]) / ".config/hatari/hatari.sav"
        sav.unlink(missing_ok=True)
        h.state = sav
        h.savemem(a.out + ".sav")
        sav.unlink(missing_ok=True)
finally:
    h.close()
