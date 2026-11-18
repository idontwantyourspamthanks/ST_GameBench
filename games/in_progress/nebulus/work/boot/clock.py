#!/usr/bin/env python3
"""Tower frame cost vs CPU clock and pacer target. Restore 1mb_tower.sav, wait 9 s (in tower), set --cpuclock, optionally poke the pacer
table word $3821c (2 -> 1), profile N VBLs (nothing else in the window), save to OUT/prof_<clk>_<tbl>.txt.
usage: clock.py OUTDIR [N=150] [clk,clk..] [tbl,tbl..]"""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 150
clks = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else '8,16,32').split(',')]
tbls = [int(x) for x in (sys.argv[4] if len(sys.argv) > 4 else '2,1').split(',')]
for clk in clks:
    for tbl in tbls:
        h = Nebulus(snapshot=str(HERE.parent / 'snapshots/1mb_tower.sav'), workdir='/tmp/nb2c')
        try:
            time.sleep(1.0)
            if clk != 8: h.set_cpuclock(clk)
            time.sleep(8.0)
            if tbl != 2: h.debug(f'w $3821c $00 ${tbl:02x}', 0.4)
            t0 = h.debug('m $3ad98 6', 0.5); v0 = h.vbl()
            prof = out / f'prof_{clk}_{tbl}.txt'
            end = out / 'end.cmd'; end.write_text(f'profile save {prof}\n')
            start = h._arm_vbl(N, f' :file {end}')
            h.cmd('hatari-debug profile on')
            h._wait_removed(start, timeout=300)
            t1 = h.debug('m $3ad98 6', 0.5); v1 = h.vbl()
            print('   timer words', t0.strip().splitlines()[-1][10:28], '->', t1.strip().splitlines()[-1][10:28], 'over', v1 - v0, 'VBL (incl. debug latency)')
            h.shot(str(out / f'{clk}_{tbl}.png'))
            print(clk, tbl, 'saved', prof.stat().st_size)
        finally:
            h.close()
