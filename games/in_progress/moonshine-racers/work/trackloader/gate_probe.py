#!/usr/bin/env python3
"""gate_probe.py --machine ste --mem 2048 [--tos 2.06]: cold boot of the shipped HD build; a breakpoint on the TRAMPOLINE ($b2708, `pc = $b2708`) runs a debugger script
that prints the values a TABLE2 gate would read at the hook instant: $42e (phystop), $436, $2dc (HAGA base), the HAGA machine type (HAGA+$83), the signatures, $b2700.
   (The debugger has no pointer expressions: the HAGA base is taken as phystop - $8000 and checked against the `$2dc` line.)"""
import argparse, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
G = HERE.parents[1]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools"))
from msr import Moonshine
from stharness import TOS
ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--tos")
ap.add_argument("--game", default="/tmp/msrl_dist/MOONSHR"); a = ap.parse_args()
kw = {"tos": TOS[a.tos]} if a.tos else {}
h = Moonshine(machine=a.machine, memsize_kb=a.mem, game_dir=a.game, **kw)
try:
    b = a.mem * 1024 - 0x8000          # HAGA base = phystop - $8000 (confirmed by the $2dc line of the same script)
    (HERE / "gp.txt").write_text(f"e VBL\nm $2dc 4\nm $42e 4\nm $436 4\nm ${b + 0x83:x} 1\nm ${b + 0xaf:x} 1\nm ${b + 0x17be:x} 4\nm ${b + 0x1166:x} 4\nm ${b + 0x1372:x} 4\nm ${b + 0x3228:x} 2\nm $b2700 8\nr\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $b2708 :trace :once :file {HERE}/gp.txt")
    t0 = time.time()
    while time.time() - t0 < 200 and "Removed CPU breakpoint" not in h._logtext()[n0:]:
        time.sleep(1)
    time.sleep(2)
    print(h._logtext()[n0:][-2500:])
finally:
    h.close()
