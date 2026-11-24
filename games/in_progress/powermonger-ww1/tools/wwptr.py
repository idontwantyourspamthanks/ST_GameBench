#!/usr/bin/env python3
"""TT / Falcon pointer gate for tt_ptr (master's PMTT: work/notes/tt.md): is the game's software mouse pointer visible?

    python3 tools/wwptr.py cold --disk build/default/floppy.st --workdir DIR [--machine tt --tos 3.06 --mem 4096] [--trials 10] [--tag NAME]

Hatari's TT video follows the shifter base LIVE (a latching ST / STE does not), so the pointer, drawn by the VBL handler into the displayed buffer, is missing for part of every
flip frame.  The gate boots the BUILT floppy to the map view (noprot) and, `--trials` times, puts the pointer (game's own pointer words, harness `goto_st`) on a spot, takes
six screenshots 0.25 s apart and counts the screenshots in which a pointer-sized area around that spot differs from the same area with the pointer away (the scene is static
except the slow world tick; the arrow is bright).  Result `PTR <tag>: visible in N of M screenshots`; with tt_ptr every screenshot must show it (master: 20 of 20), the control build
(without tt_ptr) shows it in fewer.  Also prints LIVE ($75bf0).
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
from PIL import Image  # noqa: E402


def grab(h):
    im = Image.open(h.shot()).convert("RGB")
    return np.asarray(im, dtype=np.int16)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["cold"])
    ap.add_argument("--disk", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--machine", default="tt")
    ap.add_argument("--tos", default="3.06")
    ap.add_argument("--mem", type=int, default=4096)
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--tag")
    ap.add_argument("--extra", default="--mmu true --cpuclock 32 --monitor vga")   # as dist/run_tt.sh: with the harness' default RGB monitor TOS 3.06 boots TT medium and the ST-low game is tiled 2 x 2
    a = ap.parse_args()
    tag = a.tag or Path(a.disk).parent.name
    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine=a.machine, tos=pmww.TOS[a.tos], memsize_kb=a.mem, extra=a.extra.split())
    try:
        h.boot_to_map(noprot=True, swap=False, log=lambda s: print("  " + s, flush=True))
        time.sleep(3)
        live = h.ram(0x75BF0, 1)[0]
        print(f"  LIVE = ${live:02x}, marker {h.ram(0x727F8, 4)!r}", flush=True)
        probe = grab(h)
        H, W = probe.shape[:2]
        sc = 2 if W < 700 else 2                                    # ST low resolution shown doubled
        ox, oy = (0, 0) if W == 640 else (2, 64) if W == 648 else (96, 58)        # TT 640 wide: picture at (0,0); Falcon 648 x 602: (2,64); ST / STE 832: (96,58)
        spots = [(120, 90), (200, 70), (150, 120), (240, 100), (100, 60), (260, 130), (180, 40), (140, 150), (220, 150), (90, 110)][:a.trials]
        seen = tot = 0
        for (x, y) in spots:
            h.goto_st(x + 60, y + 40)
            time.sleep(0.5)
            away = grab(h)                                          # pointer elsewhere
            h.goto_st(x, y)
            time.sleep(0.4)
            hits = 0
            for _ in range(6):
                s = grab(h)
                X, Y = ox + sc * x, oy + sc * y
                reg = (slice(Y - 2, Y + 28), slice(X - 2, X + 22))
                d = np.abs(s[reg] - away[reg]).sum(axis=2)
                hits += int((d > 150).sum() > 12)
                time.sleep(0.25)
            seen += hits
            tot += 6
            print(f"  spot ({x},{y}): pointer visible in {hits} of 6 screenshots", flush=True)
        print(f"PTR {tag} {a.machine} TOS {a.tos}: visible in {seen} of {tot} screenshots (LIVE ${live:02x})", flush=True)
        return 0
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
