"""Final-integration gate library (MSRFinalIntegrate): the REAL tools/msrpatch.py default set (HD, no file patch) as variants.
Default set now = mg_sync + mg_pace pacer, ta_rb ta_rb0 ta_nomouse ta_facestat, tb_blit*.
A = stock
F = default set, tick OFF (cycles baseline; no mt_clock/mt_pre/pacer)
T = default set with mt_sync instead of mg (tick ON, no extras)
X = the whole default (tick ON + mg extras)            (= `msrpatch.py build` default)
XM = default set with the previous pacer mx_pre + mx_sync (extras of the previous default machinery, new options)
P = the previous committed default (ta_face, no rb/rb0/nomouse/blit, mx pacer), tick ON (P) / tick OFF (PF)
R = test_hdref reference
env TINT_DROP=a,b removes patches from F/T/X/XM (bisect); TINT_ADD=a,b adds; TINT_SAFE=N builds X with `--set SAFE=N` (mg deadline margin)."""
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
PACER = ('mt_clock', 'mt_pre', 'mx_pre', 'mx_sync', 'mt_sync', 'mg_sync', 'mg_pace')
FIN = [n for n in DEFAULT if n not in PACER]
PREV_DROP = ('ta_facestat', 'ta_rb', 'ta_rb0', 'ta_nomouse', 'tb_blit', 'tb_blit11', 'tb_blit13', 'tb_blit15')
PREV = [n for n in FIN if n not in PREV_DROP] + ['ta_face']
drop = [x for x in os.environ.get('TINT_DROP', '').split(',') if x]
add = [x for x in os.environ.get('TINT_ADD', '').split(',') if x]
def _adj(l): return [n for n in l if n not in drop] + add
FIN = _adj(FIN)
MG = ['mt_clock', 'mt_pre', 'mg_sync', 'mg_pace']
MX = ['mt_clock', 'mt_pre', 'mx_pre', 'mx_sync']
MT = ['mt_clock', 'mt_pre', 'mt_sync']
SETS = {'F': FIN, 'T': FIN + MT, 'X': FIN + MG, 'XM': FIN + MX, 'XF': [n for n in FIN if n != 'ta_facestat'] + ['ta_face'] + MG, 'PF': PREV, 'P': PREV + MX, 'PT': PREV + MT, 'R': list(NAMES_R)}
TAG = os.environ.get('TINT_TAG', '')
SAFE = os.environ.get('TINT_SAFE', '')
def live_build_int(names, tag):
    out = f"work/tint2/live/{tag}{TAG}{('_s' + SAFE) if SAFE else ''}"
    (GAME / "work/tint2/live").mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(GAME / "tools/msrpatch.py"), "live", "--only", *names, "--out", out] + (['--set', f'SAFE={SAFE}'] if SAFE else [])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=GAME)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return GAME / out
mxlib.live_build = live_build_int
def variant_names(v):
    return None if v == 'A' else SETS[v]
mxlib.variant_names = variant_names
if __name__ == '__main__':
    print('DEFAULT', ' '.join(DEFAULT))
    for k, v in SETS.items(): print(k, ' '.join(v))
