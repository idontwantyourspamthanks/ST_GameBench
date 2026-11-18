"""Integration gate library: the REAL tools/msrpatch.py default set (HD, no file patch) as variants.
A = stock, T = default set with mt_sync instead of mx (tick ON, no extras), X = the whole default (tick ON + extras), R = test_hdref reference,
NT/NX = the previous (HUD-build) default tick / extras set, F = final tick OFF, N = HUD-build default tick OFF (cycles baseline).
env TINT_DROP=a,b removes patches from T/X/F (bisect); TINT_ADD=a,b adds."""
import sys, os, subprocess
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
import mxlib
from mxlib import *
GAME = mxlib.GAME
sys.path.insert(0, str(GAME / 'tools'))
import msrpatch
_p = msrpatch.load_patches()
DEFAULT = [p.name for p in msrpatch.default_selection(_p, msrpatch.load_file_patches(), False)[0]]
DEFAULT = [n for n in DEFAULT if n not in ('pp_bigram_cache',)]
PACER = ('mt_clock', 'mt_pre', 'mx_pre', 'mx_sync', 'mt_sync')
FIN = [n for n in DEFAULT if n not in PACER]
OLD_NEW = ['mr_edge', 'rd_geom', 'rd_draw', 'rd_init', 'hd_stage', 'hd_init', 'hd_clouds', 'hd_nomap', 'hd_nomap2']
drop = [x for x in os.environ.get('TINT_DROP', '').split(',') if x]
add = [x for x in os.environ.get('TINT_ADD', '').split(',') if x]
def _adj(l): return [n for n in l if n not in drop] + add
FIN = _adj(FIN)
SETS = {'F': FIN, 'N': OLD_NEW, 'T': FIN + ['mt_clock', 'mt_pre', 'mt_sync'], 'X': FIN + ['mt_clock', 'mt_pre', 'mx_pre', 'mx_sync'],
        'NT': OLD_NEW + ['mt_clock', 'mt_pre', 'mt_sync'], 'NX': OLD_NEW + ['mt_clock', 'mt_pre', 'mx_pre', 'mx_sync'], 'R': list(NAMES_R)}
TAG = os.environ.get('TINT_TAG', '')
def live_build_int(names, tag):
    out = f"work/tint/live/{tag}{TAG}"
    (GAME / "work/tint/live").mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(GAME / "tools/msrpatch.py"), "live", "--only", *names, "--out", out], capture_output=True, text=True, cwd=GAME)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return GAME / out
mxlib.live_build = live_build_int
def variant_names(v):
    return None if v == 'A' else SETS[v]
mxlib.variant_names = variant_names
if __name__ == '__main__':
    for k, v in SETS.items(): print(k, ' '.join(v))
