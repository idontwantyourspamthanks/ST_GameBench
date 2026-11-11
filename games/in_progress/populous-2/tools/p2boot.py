#!/usr/bin/env python3
"""Cold-boot acceptance for the display patches: build an HD game folder with the chosen patches, cold boot it on Hatari and play to the first battle.

    python3 tools/p2boot.py --machine ste [--only pop2_spr pop2_ptr_a pop2_ptr_b pop2_clamp] [--mem 2048] [--out build/disp_hd]

Prints: marker ($7fff8: P2PO = every patch applied), the sprite path word BLT ($88200: $b17e0001 blitter, $b17e0002 pre-shifted cache, set by pop2_spr's
first call), pop2_clamp's drop counter ($86f10), the turn counter before and after 3 s (play), and saves a screenshot to work/shots/<tag>.png.
--machine st uses TOS 1.04 on a plain ST (no STE blitter, no DMA sound): the cache path must be chosen.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(HERE), str(GAME.parent.parent.parent / "tools")]
from populous2 import Populous2  # noqa: E402
from stharness import TOS  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default="ste", choices=["st", "ste", "megaste"])
    ap.add_argument("--tos", default=None)
    ap.add_argument("--mem", type=int, default=2048)
    ap.add_argument("--only", nargs="*", default=["pop2_spr", "pop2_spr16", "pop2_ptr_a", "pop2_ptr_b", "pop2_clamp"])
    ap.add_argument("--out", default="build/disp_hd")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--nobuild", action="store_true", help="use the existing --out folder (parallel runs)")
    a = ap.parse_args()
    names = ["pop2_credit"] + a.only if a.only else []
    cmd = [sys.executable, str(HERE / "pop2patch.py"), "build", "--out", a.out]
    if a.only is not None:
        cmd += ["--only", *names]
    if not a.nobuild:
        subprocess.run(cmd, check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    tos = TOS[a.tos or {"st": "1.04", "ste": "1.62", "megaste": "2.06"}[a.machine]]
    tag = a.tag or f"disp_{a.machine}_{a.mem // 1024}mb"
    h = Populous2(game_dir=GAME / a.out, machine=a.machine, tos=tos, memsize_kb=a.mem)
    try:
        ok = h.boot_to_game()
        t0 = h.peekw(h.TURN)
        time.sleep(3)
        t1 = h.peekw(h.TURN)
        marker = h.marker()
        blt = h.peekl(0x88200)
        drops = h.peekl(0x86F10)
        shot = GAME / "work" / "shots" / f"{tag}.png"
        try:
            h.shot(str(shot))
        except Exception as e:  # noqa: BLE001
            print("screenshot failed:", e)
        print(f"{a.machine} {a.mem} KB TOS {tos.name}: in_play={ok} marker={marker!r} turn {t0} -> {t1} BLT=${blt:08x} (clamp drops {drops}) patches={names}  shot={shot.name}")
        sys.exit(0 if ok and marker == "P2PO" and t1 != t0 else 1)
    finally:
        h.close()


if __name__ == "__main__":
    main()
