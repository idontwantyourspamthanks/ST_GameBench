#!/usr/bin/env python3
"""keytime2.py SNAP SET MHZ DV: when are the Esc pokes ($7687 = ff, runtype 'esc<dv>') done and when does the key handler $1b43a see them (VBL numbers)."""
import sys, re, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
import vgate
snap, sset, mhz, dv0 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
live = build_live(vgate.SETS[sset], 'kt2_' + sset)
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=2048)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    v = h.vbl()
    f = h.R / 'kt.txt'; f.write_text('e VBL\nm $7686 2\n')
    lc = []
    for i in range(10):
        lf = h.R / f'late{i}.txt'; lf.write_text('e VBL\nw $7687 $ff\n')
        lc.append(f"b VBL > {v + 100 + dv0 + 4*i} :trace :once :file {lf}")
    cmds = apply_cmds(live) + (['w $b42e4 $ff $d0'] if sset == 'P' else []) + lc + [f'b pc = $1b43a :trace :file {f}']
    start = len(h._logtext())
    at_flip(h, cmds, v + 100)
    time.sleep(8)
    h.debug('b all', 0.5)
    txt = h._logtext()[start:]
    ev = []
    for m in re.finditer(r'#(\d+) \(dec\)[^\n]*\n> (\w) [^\n]*\n(?:0*7686:\s+(\w\w) (\w\w))?', txt):
        ev.append((int(m.group(1)) - (v + 100), 'poke' if m.group(2) == 'w' else 'tick key=%s%s' % (m.group(3), m.group(4))))
    print(sset, mhz, 'dv', dv0, ev[:40])
finally:
    h.close()
