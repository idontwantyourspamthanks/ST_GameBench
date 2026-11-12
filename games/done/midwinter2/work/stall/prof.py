#!/usr/bin/env python3
"""prof.py MHZ START VBLS [--unpatched]: profile VBLS frames starting at rel VBL START after apply."""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
import mw2tick as T
from mw2harness import Hatari
ONLY = "tick_vbl p3b_head p3b_render p3b_pos p3b_hdg p3b_alt p3b_bank p3b_save p3b_probe".split()
mhz, start, n = map(int, sys.argv[1:4])
live = None if "--unpatched" in sys.argv else T.live_image(ONLY)
h = Hatari(snapshot=str(GAME / "work/snapshots/1mb_ingame_walking.sav"), memsize_kb=1024)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    at = h.vbl() + 100
    T.at_flip(h, T.apply_cmds(live) if live else [], at)
    time.sleep(1.0)
    v0 = h.vbl()
    h.debug("b all", 0.3)
    s = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v0+start} :trace :once")
    T.wait_gone(h, s, 300)
    p = h.profile(n)
    agg = {}
    for a, c in p: agg[a] = c
    tot = sum(agg.values())
    print("total cycles", tot, "VBL", n, "= cycles/VBL", tot/n)
    for a, c in sorted(agg.items(), key=lambda x: -x[1])[:40]:
        print(f"{a:06x} {c}")
finally:
    h.close()
