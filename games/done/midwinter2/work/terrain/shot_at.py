#!/usr/bin/env python3
"""shot_at.py CELLX ROW HEADING OUT: standing snapshot, poke player to window cell (x,row) and heading, screenshot."""
import sys, time
from pathlib import Path
GAME = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(GAME / "tools"))
from mw2harness import Hatari
cx, row, hdg, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
ALT = int(sys.argv[5]) if len(sys.argv) > 5 else None
X = cx * 512 + 256; Y = (99 - row) * 512 + 256
h = Hatari(snapshot=str(GAME / "work/snapshots/1mb_ingame_walking.sav"), memsize_kb=1024)
try:
    h.set_cpuclock(16)
    def L(v): return " ".join(f"${(v >> s) & 255:02x}" for s in (24, 16, 8, 0))
    def W(v): return " ".join(f"${(v >> s) & 255:02x}" for s in (8, 0))
    h.debug("w $66e6 $00 $00 $13 $50", 0.3)     # trigger the local-map rebuild first: the grid then matches /tmp/terr/grid_shaded.bin
    time.sleep(14)
    for a in (0x66e6, 0x66ee, 0x66f6): h.debug(f"w ${a:x} {L(X)}", 0.3)
    for a in (0x66ea, 0x66f2, 0x66fa): h.debug(f"w ${a:x} {L(Y)}", 0.3)
    for a in (0x6742, 0x6294, 0x764a): h.debug(f"w ${a:x} {W(hdg)}", 0.3)
    if ALT is not None: h.debug(f"w $764c {W(ALT)}", 0.3)
    time.sleep(16)
    print(h.shot(str(GAME / "work/shots" / out)))
    print(h.peekw(0x764c), h.peekw(0x6742))
finally:
    h.close()
