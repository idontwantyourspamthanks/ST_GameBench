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
    """THE SQUEEZE: a full ring of ledge, a low stone ceiling (row 8) over columns 10..5, and two fast up/down eyes each side of the frog, staggered in
    height and direction.  Eyes rebound between the ledge (row 1) and the ceiling, so each sweeps the whole corridor in a few frames."""
    rows = 24
    g = blank(rows)
    put(g, range(16), 1, LEDGE)
    put(g, span(10, 5), 8, PILLAR)                                   # the ceiling: 6 columns left of the start, 6 right
    for col, row, v in ((14, 3, EYE_V_FAST), (12, 6, EYE_V_FAST | 1), (2, 6, EYE_V_FAST), (4, 3, EYE_V_FAST | 1)):
        g[col][row] = v
    put(g, [8], 2, EXIT); put(g, [8], 3, EXIT); put(g, [8], 4, EXIT)  # the way out is on the far side of the ring
    return dict(name='THE SQUEEZE', rows=rows, grid=g, time=0x0200)


def level_escalator():
    """THE ESCALATOR: three identical floors (a ledge ring segment, a charging ball each side, a lift to the next floor).  Lifts alternate between columns 1 and 15
    (an arrival platform in the ledge row cannot also be the next slab).  Only 4 creatures live at once, so floors 1 and 2 fill the slots and floor 3 waits."""
    rows = 40
    g = blank(rows)
    bases = (1, 12, 23)
    for base in bases:
        put(g, span(11, 5), base, LEDGE)
        g[3][base + 1] = BALL_WAIT                                    # 24 units to the right of the frog's column
        g[13][base + 1] = BALL_WAIT                                   # 20 units to the left
    for n, base in enumerate(bases[:-1]):                             # lifts last: the end marker replaces a ledge cell of the next floor
        ovl.add_lift(g, 1 if n % 2 == 0 else 15, base + 1, bases[n + 1])
    put(g, [14], 24, EXIT); put(g, [14], 25, EXIT); put(g, [14], 26, EXIT)
    return dict(name='THE ESCALATOR', rows=rows, grid=g, time=0x0300)


def level_no_mans_land():
    """NO MAN'S LAND: the frog starts on a one-cell ledge, the next ledges are one jump away on either side (a gap of one column), each patrolled by a fast
    horizontal eye; the same again one jump further out.  Horizontal eyes only rebound off terrain: the exit door (column 8, the far side of the ring) is
    the wall they sweep towards."""
    rows = 24
    g = blank(rows)
    put(g, [0], 1, LEDGE)
    put(g, span(2, 4), 1, LEDGE); put(g, span(12, 14), 1, LEDGE)     # near ledges (gap columns 1 and 15)
    put(g, span(6, 8), 1, LEDGE); put(g, span(9, 10), 1, LEDGE)      # far ledges (gap columns 5 and 11)
    for c in (1, 5, 11, 15):                                         # one-high stones in the gaps: the eyes rebound off them, the frog jumps over
        g[c][2] = PILLAR
    g[3][2] = EYE_H_FAST; g[13][2] = EYE_H_FAST | 1
    g[7][2] = EYE_H_FAST; g[10][2] = EYE_H_FAST | 1
    put(g, [8], 2, EXIT); put(g, [8], 3, EXIT); put(g, [8], 4, EXIT)
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
