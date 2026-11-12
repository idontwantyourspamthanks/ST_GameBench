#!/usr/bin/env python3
"""sample.py MHZ HZ rel_start rel_end step: apply p3b set as trace.py, dump r + stack + state at VBL samples."""
import sys, re, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
import mw2tick as T
from mw2harness import Hatari
ONLY = "tick_vbl p3b_head p3b_render p3b_pos p3b_hdg p3b_alt p3b_bank p3b_save p3b_probe".split()
mhz, hz, a, b, st = map(int, sys.argv[1:6])
live = None if "--unpatched" in sys.argv else T.live_image(ONLY)
snap = "work/snapshots/1mb_ingame_walking.sav"
h = Hatari(snapshot=str(GAME / snap), memsize_kb=1024)
res=[]
try:
    if mhz != 8: h.set_cpuclock(mhz)
    at = h.vbl() + 100
    T.at_flip(h, (T.apply_cmds(live) if live else []) + (["w $ff820a $00"] if hz == 60 else []), at)
    time.sleep(1.0)
    v0 = h.vbl()
    f = h.R / "s.txt"
    f.write_text("e VBL\nr\nm a7 80\nm $66e6 8\nm $6220 2\nm $b3400 4\nm $b42e0 16\nm $eb8c 2\nm $6290 2\n")
    for n in range(a, b+1, st):
        h.debug("b all", 0.3)
        s = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {v0+n} :trace :once :file {f}")
        T.wait_gone(h, s, 300)
        res.append(f"=== rel {n}\n" + h._logtext()[s:])
    (HERE / f"sample_{mhz}_{hz}.txt").write_text(f"v0={v0}\n" + "\n".join(res))
finally:
    h.close()
