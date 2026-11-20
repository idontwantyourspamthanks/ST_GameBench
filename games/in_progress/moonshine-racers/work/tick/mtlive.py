"""Apply the msrpatch.py live image of the mt_* patches to a running Hatari (loadbin + site writes at a one-shot breakpoint)."""
import sys, json, subprocess, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "work/timing"))
from tlib import *
from live import apply_live

def live_build(names=("mt_clock", "mt_sync", "mt_pre"), out="work/tick/live/mt"):
    r = subprocess.run([sys.executable, str(GAME / "tools/msrpatch.py"), "live", "--only", *names, "--out", out], capture_output=True, text=True, cwd=GAME)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return GAME / out

def apply_mt(h, names=("mt_clock", "mt_sync", "mt_pre"), at_pc=0x7a88):
    o = live_build(names)
    spec = json.loads(o.with_suffix(".json").read_text())
    img = o.with_suffix(".img").read_bytes()
    sites = [(s["addr"], bytes.fromhex(s["new"])) for s in spec["sites"]]
    return apply_live(h, [(spec["img_base"], img)], sites, at_pc=at_pc)
