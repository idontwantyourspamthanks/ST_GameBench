#!/usr/bin/env python3
"""Payload images of the shipped v1.0.1 (commit 9493139), for the ab1m.py control run C (loadbin of the OLD image over the old game: tells a loadbin perturbation from a real payload effect).
   python3 mkv101img.py   -> /tmp/msrc3/v101_hd_image.bin, /tmp/msrc3/v101_fl_image.bin  (tree: git archive 9493139 patches tools into /tmp/msrc3/o/x/y/old; originals/alt/work symlinked; BENCH tools symlinked at /tmp/msrc3/o/tools)"""
import subprocess, sys, shutil, os
from pathlib import Path
G = Path(__file__).resolve().parents[2]
O = Path("/tmp/msrc3/o"); T = O / "x/y/old"
if not (T / "tools/msrpatch.py").exists():
    shutil.rmtree(O, ignore_errors=True); T.mkdir(parents=True)
    (O / "tools").symlink_to(G.parents[2] / "tools")
    subprocess.run(f"git -C {G} archive 9493139 patches tools | tar -x -C {T}", shell=True, check=True)
    for d in ("originals", "alt", "work"): (T / d).symlink_to(G / d)
sys.path.insert(0, str(T / "tools"))
import msrpatch as P
for kind in ("hd", "fl"):
    fl = kind == "fl"
    sel, fsel = P.default_selection(P.load_patches(), P.load_file_patches(), fl)
    sel = [p for p in sel if p.site is not None]
    if fl:
        getattr(P, "set_flavour", lambda x: None)(True); tb = P.IB + 0x120
        img, _ = P.build_image(sel, table=tb, min_end=tb + 0x100, floppy=True)
    else:
        getattr(P, "set_flavour", lambda x: None)(False); img, _ = P.build_image(sel, fnames=[p.name for p in fsel])
    Path(f"/tmp/msrc3/v101_{kind}_image.bin").write_bytes(img); print(kind, len(img))
