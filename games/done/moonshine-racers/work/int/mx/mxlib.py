"""Shared helpers for the integrated extra-frame gates (live images built by the REAL tools/msrpatch.py)."""
import sys, json, subprocess, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent.parent
sys.path.insert(0, str(GAME / "work/timing")); sys.path.insert(0, str(GAME / "tools"))
from tlib import *
from live import apply_live
NAMES_T = ("mr_digit", "mr_edge", "mr_map", "mt_clock", "mt_pre", "mt_sync", "rd_draw", "rd_geom", "rd_init")
NAMES_X = ("mr_digit", "mr_edge", "mr_map", "mt_clock", "mt_pre", "mx_pre", "mx_sync", "rd_draw", "rd_geom", "rd_init")
def live_build(names, tag):
    out = f"work/int/mx/live/{tag}"
    (GAME / "work/int/mx/live").mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(GAME / "tools/msrpatch.py"), "live", "--only", *names, "--out", out], capture_output=True, text=True, cwd=GAME)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return GAME / out
def parse_pokes(args):
    return [(int(x.split('=')[0], 16), bytes.fromhex(x.split('=')[1])) for x in args if '=' in x]
def apply_names(h, names, tag, at_pc=0x7a88, pokes=()):
    if not names:
        return apply_live(h, [], list(pokes), at_pc=at_pc)
    o = live_build(names, tag)
    spec = json.loads(o.with_suffix(".json").read_text())
    img = o.with_suffix(".img").read_bytes()
    sites = [(s["addr"], bytes.fromhex(s["new"])) for s in spec["sites"]] + list(pokes)
    return apply_live(h, [(spec["img_base"], img)], sites, at_pc=at_pc)
from msr import Moonshine, SNAP as SNAPDIR
from stharness import TOS
MACHINES = {"megaste60": dict(machine="megaste", memsize_kb=4096, tos="2.06"), "ste1024": {}, "ste4096": dict(memsize_kb=4096)}
def open_snap(name, mhz, tag=None):
    kw = MACHINES.get(tag or "", {})
    if "tos" in kw: kw = dict(kw); kw["tos"] = TOS[kw["tos"]]
    h = Moonshine(snapshot=str(SNAPDIR / name), **kw)
    time.sleep(3)
    if mhz: h.set_cpuclock(mhz)
    return h
def variant_names(v):
    return {"A": None, "T": NAMES_T, "X": NAMES_X}[v]
