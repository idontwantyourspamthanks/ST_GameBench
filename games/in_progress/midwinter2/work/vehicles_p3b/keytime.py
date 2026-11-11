#!/usr/bin/env python3
"""keytime.py SNAP SET MHZ [SECONDS]: VBL of every execution of the key handler $1b43a (once per tick, pre-calls) and of the sim hook point $31570,
with the 4 passes' structure (PH $b42e6). Prints the VBL list, to check that tick starts are VBL-aligned between A and P."""
import sys, re, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
import vgate
snap, sset, mhz = sys.argv[1], sys.argv[2], int(sys.argv[3]); n = int(sys.argv[4]) if len(sys.argv) > 4 else 20
live = build_live(vgate.SETS[sset], 'kt_' + sset)
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=2048)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    v = h.vbl()
    f = h.R / 'kt.txt'; f.write_text('e VBL\n')
    cmds = apply_cmds(live) + (['w $b42e4 $ff $d0'] if sset == 'P' else []) + [f'b pc = $1b43a :trace :file {f}']
    start = len(h._logtext())
    at_flip(h, cmds, v + 100)
    t = time.time()
    while True:
        txt = h._logtext()[start:]
        vb = [int(x) for x in re.findall(r'#(\d+) \(dec\)', txt)]
        if len(vb) >= n or time.time() - t > 600: break
        time.sleep(0.5)
    h.debug('b all', 0.5)
    print(sset, mhz, 'VBL', [x - vb[0] for x in vb], 'first', vb[0], 'flip-apply base', v + 100)
finally:
    h.close()
