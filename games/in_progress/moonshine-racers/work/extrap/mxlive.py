"""Apply the msrpatch live image of mt_clock + mt_pre + mx_sync to a running Hatari (private copy of work/tick/mtlive.py)."""
import sys, json, subprocess, time
from pathlib import Path
MXD = Path(__file__).resolve().parent
MXG = MXD.parent.parent
sys.path.insert(0, str(MXG / "work/timing"))
from tlib import *
from live import apply_live

def live_build(names=("mt_clock", "mt_pre", "mx_pre", "mx_sync"), out="work/extrap/live/mx"):
    r = subprocess.run([sys.executable, str(MXD / "msrpatch_priv.py"), "live", "--only", *names, "--out", out], capture_output=True, text=True, cwd=MXG)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return MXG / out

def apply_mx(h, names=("mt_clock", "mt_pre", "mx_pre", "mx_sync"), at_pc=0x7a88, pokes=()):
    o = live_build(names)
    spec = json.loads(o.with_suffix(".json").read_text())
    img = o.with_suffix(".img").read_bytes()
    sites = [(s["addr"], bytes.fromhex(s["new"])) for s in spec["sites"]]
    sites += list(pokes)
    return apply_live(h, [(spec["img_base"], img)], sites, at_pc=at_pc)
