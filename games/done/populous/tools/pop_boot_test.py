#!/usr/bin/env python3
"""Cold-boot acceptance cell for the patched Populous HD build (build/hd): boots one machine configuration
to play and prints / saves the evidence.

    python3 tools/pop_boot_test.py NAME [--machine ste|st|megaste|tt|falcon] [--tos 1.62] [--mem 1024]
                                   [--cpuclock 16] [--game build/hd] [--extra ARGS...]

For the cell it prints: the payload header at $B3000 ('POPP' + marker 'POPO' + flags), the byte at $EE16 (the
protection branch, $60 when pop_noprot is applied), the text base check (code of the main loop at $B6F4 =
`jsr $14a28`), the turn counter moving, and writes work/shots/boot_<NAME>_menu.png (the TUTORIAL / CONQUEST /
CUSTOM screen with the credit line) and boot_<NAME>_play.png.  Needs a free display; at most 2 cells at once.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
from populous import Populous, HOME, CONQUEST_XY, START_XY  # noqa: E402
from stharness import TOS  # noqa: E402


def mem4(h, addr, n=4):
    out = h.debug(f"m ${addr:x} {n}", 0.6)
    import re
    hx = re.findall(rf"{addr:08x}:\s+((?:[0-9a-f]{{2}} ?)+)", out, re.I)
    return hx[-1].strip() if hx else out.strip()


def run(name, machine="ste", tos="1.62", mem=1024, cpuclock=None, game="build/hd", extra=None):
    shots = GAME / "work" / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    kw = dict(game_dir=GAME / game, snapshot=None, memsize_kb=mem, machine=machine, tos=TOS[tos])
    if extra:
        kw["extra"] = list(extra)
    h = Populous(**kw)
    try:
        time.sleep(16)
        if cpuclock:
            h.set_cpuclock(cpuclock)             # a --cpuclock command line option crashes TOS 2.06's boot on the Mega STE
        h.key("space", 0.5)                      # PP's hardware screen
        time.sleep(28)                           # the title: PP's picture ~20 s, then the menu from ~25 s on
        h.shot(str(shots / f"boot_{name}_menu.png"))     # the TUTORIAL / CONQUEST / CUSTOM menu with the credit line
        h.goto(*CONQUEST_XY, home_xy=HOME)
        h.click(hold=0.4)
        time.sleep(9)
        h.goto(*START_XY, home_xy=HOME)           # START GAME, in the black map window
        h.click(hold=0.4)
        time.sleep(10)
        ok = h.in_play()
        h.shot(str(shots / f"boot_{name}_play.png"))
        res = dict(cell=name, in_play=ok,
                   header=bytes.fromhex(mem4(h, 0xB3000, 16).replace(" ", "")).hex(),
                   marker=bytes.fromhex(mem4(h, 0xB3004, 4).replace(" ", "")).decode("latin1"),
                   flags=mem4(h, 0xB3008, 4),
                   ee16=mem4(h, 0xEE16, 2),
                   membot=mem4(h, 0x432, 4),
                   main_loop=mem4(h, 0xB6F4, 6))
        print(res)
        return res
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--cpuclock", type=int)
    ap.add_argument("--game", default="build/hd")
    ap.add_argument("--extra", nargs="*")
    a = ap.parse_args()
    run(a.name, a.machine, a.tos, a.mem, a.cpuclock, a.game, a.extra)


if __name__ == "__main__":
    main()
