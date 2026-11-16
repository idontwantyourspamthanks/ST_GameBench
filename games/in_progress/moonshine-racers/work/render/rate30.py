#!/usr/bin/env python3
"""Pass rate of tick builds: MSR_PATCHDIR/MSR_LIVETAG select the patch dir (T=36 patches/ or T=30 work/render/patches30/).
python3 work/render/rate30.py SCENE T(30|36) NAMES... : prints passes per second over 600 VBL (flips at $d1ca), live-applied on the snapshot."""
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
scene, T, names = sys.argv[1], sys.argv[2], sys.argv[3:]
if T == "30":
    os.environ["MSR_PATCHDIR"] = str(HERE / "patches30"); os.environ["MSR_LIVETAG"] = "_t30"
import msrabtest as ab
live = ab.live_build(names)
r = ab.rate(ab.snap_path(scene), live, 600)
print(f"{scene} T={T} {' '.join(names)}: {r['flips']} passes / 600 VBL = {r['flips'] * 50 / 600:.3f} pass/s ({r['vbl_per_pass']:.3f} VBL/pass)")
