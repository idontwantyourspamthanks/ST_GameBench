#!/usr/bin/env python3
"""Build the EXAMPLE campaign file (3 hand-designed levels + 2 campaigns) for the community site / the game's campaign disk.
   python3 work/editor/mk_example.py OUT.ovl      then:  tools/nebcampaign.py new OUT.st --ovl OUT.ovl      (+ .msa)
Every level is designed to the frog's MEASURED reach (work/notes/example.md section 2) and played through in the game (section 4):
  * the frog starts at x=4 (column 0), standing on the row-1 ring (feet y=8): every level has the full ring on row 1;
  * a solid cell c supports the frog's x in [8c+1, 8c+8] (8 units per column, 4 units per row, 16 columns);
  * a RISER of 1 row is climbed by walking into it (automatic hop), a riser of 2 rows by jumping (fire while walking) from the wall or up to
    9 units before it; 3 rows cannot be climbed at all (jump apex +9 units = 2.25 rows); taller: LIFTS;
  * a same-height gap of 1 empty column is crossable only in the last ~4 units of the ledge: the stairs here have NO gaps (adjacent treads);
  * a lift = slab $85 at the lower row (+ledge $81 under it), end marker $08 at the upper row, optional stop $0c; the frog steps off onto a ledge
    in the SAME row as the end marker, next to the shaft;
  * the exit = three $c3 cells in one column on a tread, the frog stands under them (row+1..row+3) and presses Up.
The same geometry feeds work/example/plan.py (the scripted play-throughs)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ovl

LEDGE, BLUE, EXIT = 0x81, 0x82, 0xC3
RED, STONE, EYE = 0x20, 0x10, 0x40


def blank(rows):
    return [[0] * rows for _ in range(16)]


def ring(g, row=1):
    for a in range(16):
        g[a][row] = LEDGE


def tread(g, row, col, width):
    for i in range(width):
        g[(col + i) % 16][row] = LEDGE


def exit_door(g, a, row):                   # the ledge is at `row`, the door cells are the three rows above it
    for r in range(row + 1, row + 4):
        g[a % 16][r] = EXIT


# ---- SPIRAL: a staircase round the tower: 3-wide treads, risers 1,2,1,2,... (1 = walk into it, 2 = jump), two 6-wide landings with a ball each
SPIRAL_RISERS = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
SPIRAL_WIDTHS = {7: 6, 14: 6}               # tread index -> width (landings), the others are 3 wide


def spiral_treads():
    """[(row, first column, width)]: tread 0 sits on the ring (row 2); tread k+1 starts in the column after tread k and is risers[k] rows higher"""
    out = []; row, col = 2, 3
    for k in range(len(SPIRAL_RISERS) + 1):
        w = SPIRAL_WIDTHS.get(k, 3)
        out.append((row, col % 16, w))
        col += w
        if k < len(SPIRAL_RISERS): row += SPIRAL_RISERS[k]
    return out


def level_spiral():
    tr = spiral_treads()
    rows = tr[-1][0] + 6
    g = blank(rows)
    ring(g)
    for (r, c, w) in tr:
        tread(g, r, c, w)
    for k, kind in ((7, RED), (14, STONE)):  # a ball on each landing, 4 columns in (the frog arrives at the left end and can shoot along the landing)
        r, c, w = tr[k]
        g[(c + 4) % 16][r + 1] = kind
    r, c, w = tr[-1]
    exit_door(g, c + 1, r)                   # exit in the middle of the (3-wide) top tread
    return ovl.level(1, 0, rows, g, time=0x0300, name="SPIRAL")


# ---- LIFTS: ring -> lift 1 (11 rows) -> ledge -> lift 2 with a stop (14 rows) -> top ledge with the exit
def level_lifts():
    rows = 34
    g = blank(rows)
    ring(g)
    ovl.add_lift(g, 5, 1, 11)                # slab in the ring (col 5, row 1), ride 10 rows up, step off to the right
    tread(g, 11, 6, 6)                       # cols 6..11, row 11
    g[9][12] = STONE                         # stone ball rolling on the landing (it turns at the ends)
    ovl.add_lift(g, 12, 11, 25, stops=(18,))  # slab at the end of the landing, stop half way, end at row 25
    tread(g, 18, 13, 2)                      # a ledge beside the stop (rest, or step off)
    tread(g, 25, 13, 6)                      # top landing: cols 13..15,0..2
    g[0][26] = RED                           # red ball on the top landing, between the lift and the exit
    exit_door(g, 2, 25)
    return ovl.level(1, 1, rows, g, time=0x0150, name="LIFTS")


# ---- BLOCKS: a roofed corridor shut by two blue blocks with a red ball behind them, then stairs
BLOCK_TREADS = [(3, 10, 3), (5, 13, 3), (6, 0, 3), (8, 3, 3), (9, 6, 5)]     # (row, first column, width); risers 1,2,1,2,1 from the corridor floor (row 2, columns 2..9)


def level_blocks():
    rows = 17
    g = blank(rows)
    ring(g)
    tread(g, 2, 2, 8)                        # corridor floor: cols 2..9, row 2 (riser 1 from the ring)
    tread(g, 6, 4, 5)                        # its roof (row 6, cols 4..8): the frog cannot hop the blocks (the hop would hit the roof), it has to shoot them;
                                             # the roof ends before the corridor does, so the hop onto the first stair (col 10) is free
    g[6][3] = BLUE
    g[7][3] = BLUE                           # two blue blocks side by side (two shots)
    g[9][3] = RED                            # red ball behind them
    for (r, c, w) in BLOCK_TREADS:
        tread(g, r, c, w)
    r, c, w = BLOCK_TREADS[-1]
    exit_door(g, c + 2, r)
    return ovl.level(1, 2, rows, g, time=0x0150, name="BLOCKS")


def main(out):
    lv = [level_spiral(), level_lifts(), level_blocks()]
    camps = [ovl.camp("EXAMPLE", [0, 1, 2]), ovl.camp("MIXED", [0, ovl.orig(1, 0), 1, ovl.orig(1, 1), 2])]
    data = ovl.build(lv, camps)
    Path(out).write_bytes(data)
    print(f"{out}: {len(data)} B, {len(lv)} levels, {len(camps)} campaigns")


if __name__ == "__main__":
    main(sys.argv[1])
