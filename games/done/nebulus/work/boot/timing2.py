#!/usr/bin/env python3
"""Per-scenario profile windows from the lead's baseline snapshot (work/snapshots/1mb_tower.sav, 1 MB STE, in tower).
Each scenario = fresh Hatari restore -> optional held keys -> `profile on` ... `profile save` after N VBLs
(no other debugger command inside the window: any fifo command resets Hatari's profiler).
usage: timing2.py OUTDIR [N=200]  -> prof_<name>.txt, ram_<name>.bin"""
import re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
SNAP = HERE.parent / 'snapshots/1mb_tower.sav'
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200
SC = [('stand', (), N), ('right', ('Right',), 110), ('right_jump', ('Right', 'Control_R'), 110), ('left', ('Left',), 110)]
only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
for name, keys, n in SC:
    if only and name not in only: continue
    h = Nebulus(snapshot=str(SNAP), workdir='/tmp/nb2t')
    try:
        time.sleep(3)
        h.dump(str(out / f'ram_{name}.bin'), 0, 0x100000)
        v0 = h.vbl(); t0 = h.debug('m $3ad98 2')
        for k in keys: h._xdo('keydown', k)
        time.sleep(0.2)
        prof = out / f'prof_{name}.txt'
        end = out / 'end.cmd'; end.write_text(f'profile save {prof}\n')
        start = h._arm_vbl(n, f' :file {end}')
        h.cmd('hatari-debug profile on')
        h._wait_removed(start, timeout=300)
        for k in keys: h._xdo('keyup', k)
        h.shot(str(out / f'{name}.png'))
        print(name, 'vbl0', v0, 'timer0', t0.strip().splitlines()[-1], 'saved', prof.exists(), prof.stat().st_size if prof.exists() else 0)
    finally:
        h.close()
