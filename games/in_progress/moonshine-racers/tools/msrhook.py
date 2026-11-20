#!/usr/bin/env python3
"""Cold boot and, at each PC given, print the registers, selected memory and the GEMDOS trace; the instruments of work/notes/delivery.md.
    python3 tools/msrhook.py [--machine ste --mem 1024 --tos 1.62 --game DIR] --pcs b1fa6,b204e --mem-at b2700:32,c0:8 [--dump out.bin@PC] [--timeout 300]
Each PC arms `b pc = $X :trace :once :file cmds`; cmds = `r`, `m` for every --mem-at (hex addr:len), `savebin` when --dump F@PC is given.
Prints the filtered log (breakpoint hits in order, registers, memory)."""
import argparse, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine
from stharness import TOS
ap = argparse.ArgumentParser()
ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--tos")
ap.add_argument("--game"); ap.add_argument("--pcs", required=True); ap.add_argument("--mem-at", default="")
ap.add_argument("--dump", action="append", default=[], help="FILE@PC (hex): savebin of RAM 0..mem at that PC")
ap.add_argument("--timeout", type=int, default=300); ap.add_argument("--gemdos", action="store_true")
a = ap.parse_args()
h = Moonshine(machine=a.machine, memsize_kb=a.mem, game_dir=a.game, extra=(["--trace", "gemdos"] if a.gemdos else []),
              **({"tos": TOS[a.tos]} if a.tos else {}))
try:
    h.debug("b all", 0.3)
    pcs = [int(x, 16) for x in a.pcs.split(",")]
    dumps = {int(x.split("@")[1], 16): x.split("@")[0] for x in a.dump}
    for pc in pcs:
        f = h.R / f"hook_{pc:x}.txt"
        lines = ["r"] + [f"m ${m.split(':')[0]} {int(m.split(':')[1])}" for m in a.mem_at.split(",") if m]
        if pc in dumps:
            lines.append(f"savebin {dumps[pc]} 0 ${a.mem * 1024:x}")
        f.write_text("\n".join(lines) + "\n")
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :once :file {f}")
        time.sleep(0.3)
    t = time.time()
    while time.time() - t < a.timeout:
        n = h._logtext().count("Removed CPU breakpoint")
        if n >= len(pcs):
            break
        time.sleep(2)
    time.sleep(3)
    log = h._logtext()
finally:
    h.close()
print("\n".join(l for l in log.splitlines()
                if re.search(r"breakpoint|pc = |^\s+D0|^\s+D4|^\s+A0|^\s+A4|^\s+A6|SR=|USP|^[0-9a-fA-F]{8}: |Fread|Fseek|Pexec|Super|WARN|Bus", l)))
