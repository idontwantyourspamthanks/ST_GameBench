#!/usr/bin/env python3
"""Show `msrpatch.py live` working on a running snapshot (no boot, no cold start): restore a race snapshot, load the patch image and write every
site's new bytes the way `stharness.Hatari.capture_frames(live=...)` does, then measure the patched code over a VBL window.
    python3 tools/msr_live_test.py [--snap work/snapshots/ste1m_race_start.sav] [--only test_framecount] [--vbls 200]
`test_framecount` increments $B2FF4 once per presented frame; the printout is its delta over the window (= presented frames)."""
import argparse, json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, GAME

ap = argparse.ArgumentParser()
ap.add_argument("--snap", default="work/snapshots/ste1m_race_start.sav")
ap.add_argument("--only", nargs="*", default=["test_framecount"])
ap.add_argument("--vbls", type=int, default=200)
ap.add_argument("--out", default="build/live/patches")
ap.add_argument("--drive", action="store_true", help="hold accelerate ($6105 = 1) for the window")
a = ap.parse_args()
r = subprocess.run([sys.executable, str(GAME / "tools" / "msrpatch.py"), "live", "--only", *a.only, "--out", a.out], capture_output=True, text=True)
print((r.stdout or r.stderr).strip())
if r.returncode:
    raise SystemExit("live build failed")
out = GAME / a.out
h = Moonshine(snapshot=str(GAME / a.snap))
try:
    spec = json.loads(out.with_suffix(".json").read_text())
    h.debug("b all", 0.3)
    h.debug(f"loadbin {out.with_suffix('.img')} ${spec['img_base']:x}", 1.5)
    for s in spec["sites"]:
        h.debug(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])), 0.6)
        print(f"applied {s['name']} at ${s['addr']:x}: {s['orig']} -> {s['new']}")
    print("read back $d1ca:", h.debug("m $d1ca 8", 0.6).splitlines()[-1])

    def ctr():
        line = h.debug("m $b2ff4 4", 0.6).splitlines()[-1]
        return int("".join(re.findall(r"[0-9a-f]{2}", line.split(":")[1])[:4]), 16)
    def frame():
        return h.peekw(0x100E)
    if a.drive:
        h.drive(True)
    c0, f0 = ctr(), frame()
    h._wait_removed(h._arm_vbl(a.vbls))
    c1, f1 = ctr(), frame()
    n, m = (c1 - c0) & 0xFFFFFFFF, (f1 - f0) & 0xFFFF
    print(f"counter $B2FF4: {c0} -> {c1} = {n} increments; the game's own frame counter $100e: {f0} -> {f1} = {m} frames "
          f"({n == m if m < 0x8000 else 'restart in window'})")
finally:
    h.close()
