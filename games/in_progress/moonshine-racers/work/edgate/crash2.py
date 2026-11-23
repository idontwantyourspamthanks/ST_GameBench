#!/usr/bin/env python3
"""EXPLORATION: boot at 1 MB like play.sh, raise Hatari's memory to 2 MB (cold reset, no alert dialog), see whether the game restarts."""
import argparse, functools
import ed2lib
from ed2lib import *
_Run = ed2lib.Run
ed2lib.Run = lambda *a, **k: _Run(*a, extra_args=["--alert-level", "fatal"], **k)
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="crash2"); ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--to", type=int, default=2048)
a = ap.parse_args()
e = Ed(a.tag, "ste", a.mem, os.environ["ED_BUILD"], None); r = e.r
try:
    ok = r.boot_title(); log("title:", ok, "$42e", hex(r.l(0x42e)))
    r.shot("1_title")
    r.h.cmd(f"hatari-option --memsize {a.to}"); time.sleep(6)
    for i in range(8):
        time.sleep(5)
        try: log("t+", 5*i+5, "$42e", hex(r.l(0x42e)), "$100e", r.w(0x100e), "$1021", r.b(0x1021), "marker", r.mem(0xb2700,4))
        except Exception as ex: log("read failed", ex)
        try: r.shot(f"2_t{5*i+5}")
        except Exception as ex: log("shot failed", ex)
finally:
    e.close()
