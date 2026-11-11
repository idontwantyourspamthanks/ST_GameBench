#!/usr/bin/env python3
"""Stall investigation: log tick-head entries ($b4000, p3b) with game state; run at MHz.
usage: trace.py MHZ VBLS [hz] [--only ...]   (default patch set = p3b default tick set)"""
import sys, re, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
import mw2tick as T
from mw2harness import Hatari

ONLY = "tick_vbl p3b_head p3b_render p3b_pos p3b_hdg p3b_alt p3b_bank p3b_save p3b_probe".split()
mhz = int(sys.argv[1]); vbls = int(sys.argv[2]); hz = int(sys.argv[3]) if len(sys.argv) > 3 else 50
snap = sys.argv[4] if len(sys.argv) > 4 else "work/snapshots/1mb_ingame_walking.sav"
live = T.live_image(ONLY)
h = Hatari(snapshot=str(GAME / snap), memsize_kb=1024)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    at = h.vbl() + 100
    T.at_flip(h, T.apply_cmds(live) + (["w $ff820a $00"] if hz == 60 else []), at)
    time.sleep(1.0)
    lf = h.R / "tr.txt"
    lf.write_text("e VBL\nm $b3400 4\nm $b42e0 32\nm $66e6 8\nm $6220 2\nm $40b6 2\nm $700a 2\nm $6298 2\nm $eb8c 2\nm $6290 2\nm $764c 2\nm $6772 2\nm $6742 2\n")
    h.debug("b all", 0.3)
    s2 = len(h._logtext()); v0 = h.vbl()
    h.cmd(f"hatari-debug b pc = $b4000 :trace :file {lf}")
    time.sleep(0.2)
    h.cmd(f"hatari-debug b VBL > {v0+vbls} :trace :once")
    T.wait_gone(h, s2)
    out = h._logtext()[s2:]
    h.debug("b all", 0.3)
    Path(HERE / f"trace_{mhz}_{hz}.txt").write_text(f"v0={v0}\n" + out)
    print("ok", len(out))
finally:
    h.close()
