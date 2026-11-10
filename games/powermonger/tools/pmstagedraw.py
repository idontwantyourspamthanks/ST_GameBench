#!/usr/bin/env python3
"""Which world stage of the main loop pass writes the screen buffers?  (notes/rain.md section 4)
(extra argv: debugger commands, e.g. force rain). Unpatched game from a snapshot; `savebin` of both screen buffers ($1c700-$2c100) at consecutive call sites of ONE pass; diff of neighbours.
    python3 tools/pmstagedraw.py get_men"""
import sys, time, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent / "tools"), str(HERE)]
from pm import PM, SNAP

SITES = [(0x13040, "$127e6 sound queue"), (0x13046, "$6522"), (0x1304c, "$d322 group scan"), (0x13052, "$3e06 captains"), (0x13058, "after $3e06"),
         (0x13090, "VBL wait"), (0x130b0, "before $1abaa weather"), (0x130b6, "after $1abaa"), (0x130c2, "before $14b62 men"), (0x130c8, "after $14b62 men")]
LO, LEN = 0x1C700, 0x10000


def main():
    snap = sys.argv[1]
    h = PM(snapshot=str(SNAP / f"{snap}.sav"))
    try:
        time.sleep(1.5)
        if len(sys.argv) > 2:      # extra debugger pokes, e.g. 'w $4bb42 $00 $02'
            from pmtick import at_flip
            at_flip(h, sys.argv[2:])
            time.sleep(0.5)
            print("kind", h.peekw(0x4BB42), "left", h.peekw(0x4BB44))
        it = h.peekl(0x2DF70) + 6
        h.debug("b all", 0.3)
        for a, name in SITES:
            f = h.R / f"sd_{a:x}.txt"
            f.write_text(f"savebin {h.R}/sd_{a:x}.bin ${LO:x} ${LEN:x}\n")
            h.cmd(f"hatari-debug b pc = ${a:x} && ($2df70).l = {it} :trace :once :file {f}")
        t = time.time()
        while time.time() - t < 120 and not all((h.R / f"sd_{a:x}.bin").exists() for a, _ in SITES):
            time.sleep(0.5)
        time.sleep(1.0)
        prev = None
        for a, name in SITES:
            b = (h.R / f"sd_{a:x}.bin").read_bytes()
            if prev is not None:
                d = [i for i in range(0, len(b), 2) if b[i:i + 2] != prev[1][i:i + 2]]
                print(f"${prev[0]:x} -> ${a:x} ({prev[2]} -> {name}): {len(d)} screen words differ" + (f", ${LO + d[0]:x}..${LO + d[-1]:x}" if d else ""))
            prev = (a, b, name)
    finally:
        h.close()


main()
