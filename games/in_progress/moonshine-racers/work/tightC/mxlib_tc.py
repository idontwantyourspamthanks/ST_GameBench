"""mxlib with the private patch tool and the tc_* variants. TC = default tick set + tc_*, XC = default extras set + tc_*"""
import sys, subprocess
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
import mxlib
from mxlib import *
GAME = mxlib.GAME
TCSET = ("tc_clr", "tc_ord", "tc_dist", "tc_hit1", "tc_hit2", "tc_proj")
import os
if os.environ.get('TCSET'): TCSET = tuple(os.environ['TCSET'].split(','))
def live_build_tc(names, tag):
    out = f"work/tightC/live/{tag}"
    (GAME / "work/tightC/live").mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(GAME / "work/tightC/msrpatch_priv.py"), "live", "--only", *names, "--out", out], capture_output=True, text=True, cwd=GAME, env=dict(os.environ, MSR_PATCHDIR=str(GAME / "work/tightC/pd")))
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return GAME / out
mxlib.live_build = live_build_tc
_old = mxlib.variant_names
def variant_names(v):
    if v == "TC": return NAMES_T + TCSET
    if v == "XC": return NAMES_X + TCSET
    return _old(v)
mxlib.variant_names = variant_names
