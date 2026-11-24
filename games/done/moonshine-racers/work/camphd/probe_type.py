#!/usr/bin/env python3
"""Cold boot a build to the title and print what the gate sees: $2dc, $42e, HAGA+$83/+$af, marker, IB+4, the campaign site bytes.
   env.sh python3 probe_type.py --game DIR --machine st|megast|ste|megaste|tt|falcon --mem 2048 [--tos 1.04] [--out snap/NAME] [--shot]"""
import argparse, sys, time, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cplib import *
ap = argparse.ArgumentParser()
ap.add_argument("--game", required=True); ap.add_argument("--machine", default="st"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--tos"); ap.add_argument("--out"); ap.add_argument("--extra", nargs="*", default=[])
a = ap.parse_args()
kw = {"tos": TOS[a.tos]} if a.tos else {}
h = Moonshine(machine=a.machine, memsize_kb=a.mem, game_dir=a.game, extra=a.extra, **kw)
try:
    ok = h.boot_to_race(log=lambda *x: None)
    log("title/race reached", ok, "vbl", h.vbl(), "$1021", h.peekb(0x1021))
    base = h.peekl(0x2dc)
    log(f"$2dc={base:#x} $42e={h.peekl(0x42e):#x} HAGA+$83={mem(h, base+0x83, 1).hex()} HAGA+$af={mem(h, base+0xaf, 1).hex()}")
    log("marker", mem(h, 0xb2700, 8).hex(), "(4d53504f = MSPO; byte IB+4 = ff when list 2 was applied)")
    log("sites", {hex(ad): mem(h, ad, n).hex() for ad, n in ((0x72c4,6),(0x77da,12),(0xfda2,6),(0x731e,6),(0x7252,6),(0x74fe,6),(0x8418,6))})
    time.sleep(1)
    h.shot(str(HERE / f"snap/probe_{a.machine}_{a.mem}.png"))
    if a.out:
        sav = Path(os.environ["HOME"]) / ".config/hatari/hatari.sav"; sav.unlink(missing_ok=True); h.state = sav
        h.savemem(a.out + ".sav"); sav.unlink(missing_ok=True)
finally:
    h.close()
