#!/usr/bin/env python3
"""tightB A/B in Hatari: reference = BASE (default set, tick patches off) vs BASE + EXTRA (live images from the private tool).
   python3 tbab.py --extra tb_car tb_carph [--snapshots ...] [--flips 10 40] [--state 120] [--poke addr=hex ...] [--machine ste --mem 1024]
   Pixels: both 32000-byte buffers at the N-th flip after the apply instant (as tools/msrabtest.py).  State: msrabtest STATE_RANGES per pass keyed by $100e, masked: $100c.
   Exit 0 = identical."""
import sys, os, hashlib, argparse
from pathlib import Path
GAME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(GAME / 'tools'))
os.environ.setdefault('MSRPATCH_TOOL', str(GAME / 'work/tightB/msrpatch_priv.py')); os.environ.setdefault('MSR_LIVETAG', '_tb')
import msrabtest as ab
BASE = ['mr_edge', 'rd_geom', 'rd_draw', 'rd_init', 'hd_stage', 'hd_init', 'hd_clouds', 'hd_nomap', 'hd_nomap2']
OUT = GAME / 'work/tightB/ab'
ap = argparse.ArgumentParser()
ap.add_argument('--extra', nargs='+', required=True); ap.add_argument('--snapshots', nargs='*', default=ab.DEFAULT_SNAPS)
ap.add_argument('--flips', nargs='*', type=int, default=[10, 40]); ap.add_argument('--state', type=int, default=0)
ap.add_argument('--poke', nargs='*', default=[]); ap.add_argument('--base', nargs='*', default=BASE); ap.add_argument('--tag', default='')
a = ap.parse_args()
ptag = hashlib.md5((' '.join(a.poke) + a.tag).encode()).hexdigest()[:6]
ref = ab.live_build(a.base)
live = ab.with_pokes(ab.live_build(a.base + a.extra), a.poke, 'tb_' + '+'.join(a.extra)[:30] + ptag)
ok = True
print('reference:', ' '.join(a.base), '\npatched  : + ', ' '.join(a.extra), ('  pokes ' + ' '.join(a.poke)) if a.poke else '')
for name in a.snapshots:
    snap = ab.snap_path(name); at = ab.at_vbl_for(snap)
    for fl in a.flips:
        bd = OUT / 'base' / f'{name}_{at}_{fl}'
        if not (bd / 'b78000.bin').exists(): ab.capture(snap, at, ref, bd, fl)
        bm = {n: hashlib.md5((bd / f'{n}.bin').read_bytes()[:ab.VISIBLE]).hexdigest() for n in ab.BUFFERS}
        pd = OUT / 'patched' / ('+'.join(a.extra)[:40] + ptag) / f'{name}_{at}_{fl}'
        pm = ab.capture(snap, at, live, pd, fl)
        same = bm == pm; ok &= same
        nd = 0 if same else ab.diffbytes(bd, pd)
        print(f"PIXELS {name:11s} VBL {at} flip {fl:3d}: {'IDENTICAL' if same else f'DIFFER ({nd} bytes of 64000)'}  md5 {pm['b70000'][:8]} {pm['b78000'][:8]} (ref {bm['b70000'][:8]} {bm['b78000'][:8]})", flush=True)
    if a.state:
        sa = ab.state_run(snap, ref, a.state); sb = ab.state_run(snap, live, a.state)
        n, nd, where = ab.state_compare(sa, sb)
        where = {k: v for k, v in where.items() if not (0x100c <= k < 0x100e)}
        nd = sum(len(v) for v in where.values()); ok &= (nd == 0 and n > 0)
        print(f"STATE  {name:11s}: ref {len(sa)} passes, patched {len(sb)}, common {n}; {ab.state_compare.compared // max(n, 1)} bytes/pass; differing bytes (excluding $100c) {nd} at {len(where)} addresses" + (' -> ' + ', '.join(f'${x:04x}' for x in sorted(where)[:12]) if where else ''), flush=True)
print('RESULT:', 'ALL IDENTICAL' if ok else 'DIFFERENCES FOUND'); sys.exit(0 if ok else 1)
