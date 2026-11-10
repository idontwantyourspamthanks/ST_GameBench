#!/usr/bin/env python3
"""headtrace.py SNAP SET MHZ SYNC [N]: VBL of the first N loop-head entries ($31486) and sim-end samples ($31586) after the live apply, with CLOCK and $6288."""
import sys, re, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
from vt import *
import vgate
snap, sset, mhz, sync = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]; n = int(sys.argv[5]) if len(sys.argv) > 5 else 12
live = build_live(vgate.SETS[sset], 'ht_' + sset)
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=2048)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    v = h.vbl()
    from pathlib import Path
    sp = Path(sync)
    if sset == 'A': sp.write_text(str(v))
    else:
        while not sp.exists() or not sp.read_text().strip(): time.sleep(0.05)
        v = int(sp.read_text())
    f1 = h.R / 'h1.txt'; f1.write_text('e VBL\nm $b3400 4\nm $6288 2\n')
    f2 = h.R / 'h2.txt'; f2.write_text('e VBL\n')
    cmds = apply_cmds(live) + (['w $b42e4 $ff $d0'] if sset == 'P' else []) + [f'b pc = $31486 :trace :file {f1}', f'b pc = $31586 :trace :file {f2}']
    start = len(h._logtext())
    at_flip(h, cmds, v + 100)
    time.sleep(6)
    h.debug('b all', 0.5)
    txt = h._logtext()[start:]
    ev = []
    for blk in re.split(r"Reading debugger commands from '", txt)[1:]:
        m = re.search(r"/(h[12])\.txt'.*?#(\d+) \(dec\)", blk, re.S)
        if not m: continue
        if m.group(1) == 'h1':
            c = re.search(r'b3400:\s+(\w\w) (\w\w) (\w\w) (\w\w)', blk); w = re.search(r'6288:\s+(\w\w) (\w\w)', blk)
            ev.append(('H', int(m.group(2)) - v, int(''.join(c.groups()), 16) if c else None, ''.join(w.groups()) if w else None))
        else:
            ev.append(('S', int(m.group(2)) - v))
    print(sset, mhz, ev[:n * 3])
finally:
    h.close()
