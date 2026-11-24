#!/usr/bin/env python3
"""Why did the study's 4 MB boot of build/hd not reach the race?  Boot the STALE build/hd (HAGA unpatched) at STE 4 MB for 170 s and read the payload marker,
the HAGA record and the state bytes.   usage: boot_stale.py GAMEDIR [mem_kb]"""
import sys, time
from pathlib import Path
G = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools"))
from msr import Moonshine
gd = sys.argv[1]; mem = int(sys.argv[2]) if len(sys.argv) > 2 else 4096
h = Moonshine(game_dir=gd, machine="ste", memsize_kb=mem)
try:
    ok = h.boot_to_race(timeout=170)
    print("boot_to_race =", ok, "vbl", h.vbl(), flush=True)
    for a, n in ((0xb2700, 16), (0x2dc, 4), (0x42e, 4), (0x1021, 2), (0x23c0, 4)):
        print(h.debug(f"m ${a:x} {n}", 0.8).strip(), flush=True)
    base = h.peekl(0x2dc)
    print("HAGA base", hex(base), flush=True)
    print(h.debug(f"m ${base + 0x3228:x} 4", 0.8).strip(), "(+$3228: 2412 = unpatched, 602a = pp_bigram_cache)", flush=True)
    h.shot(str(Path(__file__).resolve().parent / "snap" / "stale_hd_4m.png"))
finally:
    h.close()
