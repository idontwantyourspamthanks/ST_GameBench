#!/usr/bin/env python3
"""16 MHz (or --clk) pacer experiment: flip deltas in VBL (pc=$3868e + `e VBL`) and in-game timer rate (words $3ad98/9a/9c), table $3821c = 2 vs 1.
usage: speed.py CLK TBL [N=200]"""
import re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
clk, tbl = int(sys.argv[1]), int(sys.argv[2]); N = int(sys.argv[3]) if len(sys.argv) > 3 else 200
h = Nebulus(snapshot=str(HERE.parent / 'snapshots/1mb_tower.sav'), workdir='/tmp/nb2k')
try:
    time.sleep(1.0)
    if clk != 8: h.set_cpuclock(clk)
    time.sleep(8.0)
    if tbl != 2: h.debug(f'w $3821c $00 ${tbl:02x}', 0.4)
    time.sleep(1.0)
    rd = lambda: [h.peekw(a) for a in (0x3AD98, 0x3AD9A, 0x3AD9C)]
    v0 = h.vbl(); t0 = rd()
    fc = HERE / 'scratch/flip.cmd'; fc.parent.mkdir(exist_ok=True); fc.write_text('e VBL\n')
    h.cmd(f'hatari-debug b pc = $3868e :trace :file {fc}'); time.sleep(0.3)
    start = h._arm_vbl(N); log = h._wait_removed(start)
    vb = [int(x) for x in re.findall(r'#(\d+) \(dec\)', log)]
    v1 = h.vbl(); t1 = rd()
    # first number is the _arm_vbl's own `e VBL`; flips are the rest
    vb = vb[1:-1] if len(vb) > 2 else vb
    d = [b - a for a, b in zip(vb, vb[1:])]
    print(f'clk {clk} tbl {tbl}: flips {len(vb)} deltas {sorted(set(d))} counts {[d.count(x) for x in sorted(set(d))]}')
    print('  sequence', ''.join(map(str, d[:120])))
    print('  timer words', [hex(x) for x in t0], '->', [hex(x) for x in t1], 'over', v1 - v0, 'VBL')
finally:
    h.close()
