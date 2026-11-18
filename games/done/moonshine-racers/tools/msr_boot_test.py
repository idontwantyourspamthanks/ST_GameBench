#!/usr/bin/env python3
"""Cold-boot test of the boot_to_race() recipe on a machine/TOS/RAM combination; prints the state log.
    python3 tools/msr_boot_test.py --machine megaste --mem 4096 [--snap out.sav]"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, GAME
ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
ap.add_argument("--snap"); ap.add_argument("--shots"); ap.add_argument("--game", help="game folder (default originals/MOONSHR; a patched build, e.g. build/marker)")
ap.add_argument("--tos"); ap.add_argument("--peek", nargs="*", default=[], help="addresses (hex) whose bytes are printed in the RESULT line")
a = ap.parse_args()
from stharness import TOS
h = Moonshine(machine=a.machine, memsize_kb=a.mem, game_dir=a.game, **({"tos": TOS[a.tos]} if a.tos else {}))
try:
    ok = h.boot_to_race(shots=a.shots)
    print("RESULT in_race =", ok, "vbl", h.vbl())
    for x in a.peek:
        ad = int(x, 16)
        print(f"PEEK ${ad:x}:", h.debug(f"m ${ad:x} 16", 0.8).strip())
    if ok:
        shot = (GAME / f"work/shots/boot_{a.machine}_{a.mem}.png") if not a.game else \
               (GAME / "build" / "shots" / f"boot_{Path(a.game).name}_{a.machine}_{a.mem}.png")
        shot.parent.mkdir(parents=True, exist_ok=True)
        h.shot(str(shot))
        if a.snap: h.savemem(a.snap)
finally:
    h.close()
