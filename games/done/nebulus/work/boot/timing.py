#!/usr/bin/env python3
"""Timing session: boot_to_game() (frozen recipe), then at the tower:
  flips (pc=$3868e = the `move.b $38759,$ff8201` of the game's flip routine $3868a) with the VBL number at each flip,
  one `profile save` window per scenario (stand / Right held / Right+fire held), plus a RAM dump.
usage: timing.py OUTDIR [vbls=250]"""
import re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 250
h = Nebulus(workdir=str(HERE / 'scratch/tim'))
def window(name, keys=(), n=N):
    """profile + flip log over n VBLs with `keys` held."""
    for k in keys: h._xdo('keydown', k)
    h.debug('b all', 0.3)
    prof = out / f'prof_{name}.txt'
    flipcmd = out / 'flip.cmd'; flipcmd.write_text('e VBL\n')
    end = out / 'end.cmd'; end.write_text(f'profile save {prof}\n')
    h.cmd(f'hatari-debug b pc = $3868e :trace :file {flipcmd}')
    time.sleep(0.3)
    start = h._arm_vbl(n, f' :file {end}')
    time.sleep(0.3)
    h.cmd('hatari-debug profile on')
    log = h._wait_removed(start, timeout=400)
    for k in keys: h._xdo('keyup', k)
    h.debug('b all', 0.3)
    vb = [int(x) for x in re.findall(r'#(\d+) \(dec\)', log)]
    (out / f'flips_{name}.txt').write_text('\n'.join(map(str, vb)) + '\n')
    return vb
try:
    ok = h.boot_to_game(shots=out)
    print('in tower', ok)
    h.dump(str(out / 'ram_tower.bin'), 0, 0x100000)
    print('vbl vars', h.debug('m $38210 16'))
    for name, keys in (('stand', ()), ('right', ('Right',)), ('right_fire', ('Right', 'Control_R'))):
        vb = window(name, keys)
        d = [b - a for a, b in zip(vb, vb[1:])]
        print(name, 'flips', len(vb), 'vbl span', vb[0] if vb else None, vb[-1] if vb else None, 'deltas', sorted(set(d)), [d.count(x) for x in sorted(set(d))])
        h.shot(str(out / f'{name}.png'))
finally:
    h.close()
