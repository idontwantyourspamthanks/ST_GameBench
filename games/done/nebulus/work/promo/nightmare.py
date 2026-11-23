#!/usr/bin/env python3
"""The three NIGHTMARE levels of the release video, built programmatically as NEBLEVEL.OVL records (format: work/notes/editor.md section 3, tools: work/editor/ovl.py).

    python3 nightmare.py [OUT.OVL]      writes the campaign file + renders each level to OUT_<n>.png and prints the maps

Facts the layouts rely on (work/notes/editor.md section 7, enemies.md):
  * 4 creature slots; markers spawn in scan order (row-major from the bottom) as their row reaches the top of the screen, a marker waits for a free slot.
  * `$40/$50` vertical eye disc (speed 1/2), `$60/$70` horizontal eye disc: they only rebound off terrain or other creatures; start direction = low nibble bit 0
    (`$50` up/right, `$51` down/left).  `$30` waiting red ball: charges when the frog is on its row within 32 angle units (4 columns).  Marker = the row ABOVE a ledge.
  * Row = 4 px, a column = 8 px (16 columns = 128 px ring), the frog starts at column 0 on the row-1 ledge (editor frog marker: column 0, row 2).
  * Lift: `85` slab on a `81` ledge, `08` end marker above in the same column (ovl.add_lift).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'editor'))
import ovl

LEDGE, PILLAR, EXIT = 0x81, 0x80, 0xC3
EYE_V, EYE_V_FAST, EYE_H, EYE_H_FAST, BALL_WAIT = 0x40, 0x50, 0x60, 0x70, 0x30


def blank(rows):
    return [[0] * rows for _ in range(16)]


def put(g, cols, row, v):
    for c in cols:
        g[c % 16][row] = v


def span(a, b):
    """columns a..b inclusive going up around the ring (wraps)"""
    return [(a + i) % 16 for i in range((b - a) % 16 + 1)]


def level_squeeze():
    """THE SQUEEZE:   LLLLLLL      a ledge above and a ledge below, the frog in the middle, and a fast up/down eye on each of the two spots directly to its
                       EEFEE       left and right (touching distance), staggered in height and direction.  The roof is 7 rows above the floor ledge so the
                      LLLLLLL      frog's jump fits under it.  The gap beyond the ledges leads nowhere: the way out is a door on the far side of the ring."""
    rows = 24
    g = blank(rows)
    put(g, range(16), 1, LEDGE)                                       # the ground ring (the frog's start is on it)
    put(g, span(13, 3), 8, LEDGE)                                     # the roof: 3 columns each side of the frog's column
    for col, row, v in ((15, 2, EYE_V_FAST), (14, 5, EYE_V_FAST | 1), (1, 4, EYE_V_FAST), (2, 3, EYE_V_FAST | 1)):
        g[col][row] = v
    put(g, [8], 2, EXIT); put(g, [8], 3, EXIT); put(g, [8], 4, EXIT)
    return dict(name='THE SQUEEZE', rows=rows, grid=g, time=0x0200)


def level_escalator():
    """THE ESCALATOR: two identical floors, a charging ball each side of the lift column (right: 3 columns out, left: 2 columns out), a lift between them.
    The frog rides up to the same pair of balls.  Four creatures fill the four slots, so everything is on screen at once."""
    rows = 24
    g = blank(rows)
    bases = (1, 12)
    for base in bases:
        put(g, span(11, 5), base, LEDGE)
        g[3][base + 1] = BALL_WAIT                                    # 24 units to the right of the frog's column
        g[14][base + 1] = BALL_WAIT                                   # 16 units to the left
    ovl.add_lift(g, 1, 2, bases[1])                                   # slab on the ledge, end marker in the upper floor's ledge row
    put(g, [5], 13, EXIT); put(g, [5], 14, EXIT); put(g, [5], 15, EXIT)      # the way out is past the right-hand ball
    return dict(name='THE ESCALATOR', rows=rows, grid=g, time=0x0300)


def level_no_mans_land():
    """NO MAN'S LAND: high up the tower.  A lift from the ground ring carries the frog to a single ledge cell (the lift's top platform, column 1, row 12); a gap of one
    column on each side, then a ledge with a fast up/down eye (ceiling above it for the eye to bounce off), another gap, another eyed ledge."""
    rows = 30
    g = blank(rows)
    put(g, range(16), 1, LEDGE)
    top = 12
    ovl.add_lift(g, 1, 2, top)                                        # the resting cell is the lift's top platform
    for c in (15, 3, 13, 5):                                          # ledges 2 and 4 columns either side of the resting cell (gaps at 0/2 and 14/4)
        g[c][top] = LEDGE
        g[c][top + 7] = LEDGE                                         # roof for the eye
    for c, row, v in ((15, top + 1, EYE_V_FAST), (3, top + 3, EYE_V_FAST | 1), (13, top + 4, EYE_V_FAST), (5, top + 2, EYE_V_FAST | 1)):
        g[c][row] = v
    g[7][top] = LEDGE                                                 # one more jump out (gap at column 6): the landing ledge with the exit door
    put(g, [7], top + 1, EXIT); put(g, [7], top + 2, EXIT); put(g, [7], top + 3, EXIT)
    return dict(name='NO MANS LAND', rows=rows, grid=g, time=0x0200)


LEVELS = (level_squeeze, level_escalator, level_no_mans_land)


def build(colours=(8, 7, 3)):
    levs = []
    for fn, col in zip(LEVELS, colours):
        d = fn()
        levs.append(ovl.level(1, 0, d['rows'], d['grid'], time=d['time'], name=d['name'], colours=col, enemies=0))
    return levs


def show(d):
    g, rows = d['grid'], d['rows']
    print(d['name'], rows)
    top = max(r for r in range(rows) if any(g[c][r] for c in range(16)))
    for r in range(top, -1, -1):
        print('%2d ' % r + ' '.join('%02x' % g[c][r] if g[c][r] else '..' for c in range(16)))


if __name__ == '__main__':
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/promo/nightmare.ovl')
    levs = build()
    out.write_bytes(ovl.build(levs, [ovl.camp('NIGHTMARE', [0, 1, 2])]))
    probs = ovl.validate(out.read_bytes())
    print('validate:', 'OK' if not probs else probs)
    for i, fn in enumerate(LEVELS):
        d = fn(); show(d)
        ovl.render(d['grid'], d['rows'], str(out.with_name(out.stem + f'_{i+1}.png')))
