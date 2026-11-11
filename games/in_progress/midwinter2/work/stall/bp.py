#!/usr/bin/env python3
"""bp.py MHZ HZ VBLS [--unpatched]: log entry ($31df6) / exit ($31f12) of the local-map rebuild sub_031dee, and the loop head."""
import sys, re, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
import mw2tick as T
from mw2harness import Hatari
ONLY = "tick_vbl p3b_head p3b_render p3b_pos p3b_hdg p3b_alt p3b_bank p3b_save p3b_probe".split()
mhz, hz, vbls = map(int, sys.argv[1:4])
unp = "--unpatched" in sys.argv
live = None if unp else T.live_image(ONLY)
h = Hatari(snapshot=str(GAME / "work/snapshots/1mb_ingame_walking.sav"), memsize_kb=1024)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    at = h.vbl() + 100
    T.at_flip(h, (T.apply_cmds(live) if live else []) + (["w $ff820a $00"] if hz == 60 else []), at)
    time.sleep(1.0)
    f = h.R / "bp.txt"
    f.write_text("e VBL\ne CycleCounter\nm $66e6 8\nm $66bc 4\nm $66f6 8\nm $6288 2\nm $6220 2\nm $eb8c 2\nm $b3400 4\n")
    h.debug("b all", 0.3)
    s2 = len(h._logtext()); v0 = h.vbl()
    for pc in ("31df6", "31f12", "31486"):
        h.cmd(f"hatari-debug b pc = ${pc} :trace :file {f}"); time.sleep(0.2)
    h.cmd(f"hatari-debug b VBL > {v0+vbls} :trace :once")
    T.wait_gone(h, s2, 900)
    out = h._logtext()[s2:]
    h.debug("b all", 0.3)
    Path(HERE / f"bp_{mhz}_{hz}{'_unp' if unp else ''}.txt").write_text(f"v0={v0}\n" + out)
    print("ok", len(out))
finally:
    h.close()
