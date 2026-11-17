"""mxlib with the private tool (work/tightB/msrpatch_priv.py) and tb_* variants.  Variant names: A stock, T/X (tick / tick+extras sets), T+tb_car+tb_carph style: base letter + '+' + patches."""
import sys, subprocess
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
import mxlib
from mxlib import *
GAMEP = mxlib.GAME
def live_build(names, tag):
    out = f"work/tightB/live/{tag}"
    (GAMEP / "work/tightB/live").mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(GAMEP / "work/tightB/msrpatch_priv.py"), "live", "--only", *names, "--out", out], capture_output=True, text=True, cwd=GAMEP)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return GAMEP / out
mxlib.live_build = live_build
def variant_names(v):
    base, *extra = v.split('+')
    nm = {"A": None, "T": NAMES_T, "X": NAMES_X, "R": NAMES_R, "O": NAMES_O, "B": ("mr_edge", "rd_geom", "rd_draw", "rd_init", "hd_stage", "hd_init", "hd_clouds", "hd_nomap", "hd_nomap2")}[base]
    return (tuple(nm) + tuple(extra)) if nm is not None else None
