"""Hatari A/B pixel gate: reference set R vs candidate C (full 32,000-byte buffers, both), flips N after the live apply.
python3 pix_hatari.py SNAPS FLIPS OUTTAG [neg]"""
import sys, os, hashlib
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/tools')
os.environ.setdefault('MSRPATCH_TOOL', GAME + '/work/tightA/msrpatch_priv.py'); os.environ.setdefault('MSR_LIVETAG', '_tA')
import msrabtest as ab
from pathlib import Path
snaps = sys.argv[1].split(','); flips = [int(x) for x in sys.argv[2].split(',')]; tag = sys.argv[3]; neg = 'neg' in sys.argv[4:]
BASE = ['hd_clouds', 'hd_nomap', 'hd_nomap2', 'hd_stage', 'mr_edge', 'rd_draw', 'rd_geom', 'rd_init']
R = ab.live_build(BASE + ['hd_init'])
C = ab.live_build(BASE + ['ta_init', 'ta_erase', 'ta_face', 'ta_glyph', 'ta_ymw', 'ta_rb', 'ta_rb0', 'ta_nomouse'])
if neg: C = ab.with_pokes(C, ['be112=600e'], 'tA_neg')        # ta_face: always "same": must DIFFER
out = ab.AB / 'tA' / tag; out.mkdir(parents=True, exist_ok=True)
tot = 0
for s in snaps:
    sp = ab.snap_path(s); at = ab.at_vbl_for(sp)
    for n in flips:
        d = {}
        for nm, lv in (('R', R), ('C', C)):
            d[nm] = ab.capture(sp, at, lv, out / f'{s}_{n}_{nm}', n)
        a = out / f'{s}_{n}_R'; b = out / f'{s}_{n}_C'
        nb = ab.diffbytes(a, b)
        print(f'{s} flip {n:3d} R hash {d["R"]["b70000"][:8]}/{d["R"]["b78000"][:8]} C hash {d["C"]["b70000"][:8]}/{d["C"]["b78000"][:8]}  differing bytes (both buffers, 64,000 compared): {nb}', flush=True)
        tot += nb
print('TOTAL differing bytes', tot, '(negative control)' if neg else '')
