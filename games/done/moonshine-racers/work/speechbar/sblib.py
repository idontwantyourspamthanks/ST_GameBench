"""Speech-bar gate library: live images built by the PRIVATE copy of the patch tool (work/speechbar/msrpatch_priv.py = tools/msrpatch.py + the private patch dir).
Sets (HD, no file patch):  F = the current default minus the pacer (tick OFF; cycles baseline; speech = ta_*), S = F with the speech bar,
T / X = F / S + mt_sync (tick ON, no extras) / + mx_* (tick ON + extras);  names with a leading 'x' prefix: XF/XS = default with extras (F + pacer)."""
import sys, os, subprocess
GAME_S = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME_S + '/work/hud/build'); sys.path.insert(0, GAME_S + '/work/speechbar'); sys.path.insert(0, GAME_S + '/tools')
import mxlib
from mxlib import *
GAME = mxlib.GAME
import msrpatch_priv as msrpatch
_p = msrpatch.load_patches()
DEFAULT = [p.name for p in msrpatch.default_selection(_p, msrpatch.load_file_patches(), False)[0]]
DEFAULT = [n for n in DEFAULT if n not in ('pp_bigram_cache',) and not n.startswith('sb_')]
PACER = ('mt_clock', 'mt_pre', 'mx_pre', 'mx_sync', 'mt_sync')
FIN = [n for n in DEFAULT if n not in PACER]
SB = ['sb_bar', 'sb_face', 'sb_glyph', 'sb_erase']
DROP = ('ta_face', 'ta_glyph', 'ta_erase', 'ta_init')
SBSET = [n for n in FIN if n not in DROP] + ['hd_init'] + SB
SBFSET = [n for n in SBSET if n != 'sb_face'] + ['sb_facestat']
SETS = {'F': FIN, 'S': SBSET, 'SF': SBFSET,
        'T': FIN + ['mt_clock', 'mt_pre', 'mt_sync'], 'TS': SBSET + ['mt_clock', 'mt_pre', 'mt_sync'],
        'X': FIN + ['mt_clock', 'mt_pre', 'mx_pre', 'mx_sync'], 'XS': SBSET + ['mt_clock', 'mt_pre', 'mx_pre', 'mx_sync'],
        'R': list(NAMES_R)}
TAG = os.environ.get('SB_TAG', '')
def live_build_sb(names, tag):
    out = f"work/speechbar/live/{tag}{TAG}"
    (GAME / "work/speechbar/live").mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(GAME / "work/speechbar/msrpatch_priv.py"), "live", "--only", *names, "--out", out], capture_output=True, text=True, cwd=GAME)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return GAME / out
mxlib.live_build = live_build_sb
live_build = live_build_sb
def variant_names(v):
    return None if v == 'A' else SETS[v]
mxlib.variant_names = variant_names
if __name__ == '__main__':
    for k, v in SETS.items(): print(k, ' '.join(v))
