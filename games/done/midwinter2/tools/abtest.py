#!/usr/bin/env python3
"""A/B gate for display patches: pixel identity + fps, on saved snapshots.

    python3 tools/abtest.py --only span_walker [more patches] \
        [--snapshot work/snapshots/1mb_ingame_walking.sav ...] [--flips 10] [--runs 1]

For each snapshot it:
  1. Captures both screen buffers at flip N after a fixed VBL, unpatched (cached
     under build/ab/base/) and with the patch set applied live at that flip
     (tools/mw2patch.py live).
  2. Reports whether the framebuffers are byte-identical, and the number of
     differing bytes otherwise.
  3. Measures fps over 1000 VBL (1 flip = 0.05 fps resolution) right after the capture, unpatched vs patched.

Live application suits patches to resident code and to data that is already
loaded. Patches that must take effect at boot or at load time still need a
cold-boot test (mw2patch.py build + Hatari.boot_to_game).

Exit status 0 = every snapshot is pixel-identical. Speed is reported, not gated.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mw2harness import GAME_DIR, Hatari  # noqa: E402

# Compare only the 32000 displayed bytes per buffer. The 768 bytes after each buffer
# hold the clip window's off-screen row 200 (never displayed, never read; see
# work/notes/p7_cockpit_cull.md), which pixel-identical culling may leave unwritten.
VISIBLE = 32000

DEFAULT_SNAPS = ["work/snapshots/1mb_ingame_walking.sav", "work/snapshots/1mb_ingame_foot.sav"]


def at_vbl_for(snap: str) -> int:
    """A fixed absolute VBL 300 past the snapshot's own VBL (rounded), so every
    run of the same snapshot starts measuring at the same frame."""
    h = Hatari(snapshot=snap)
    try:
        v = h.vbl()
    finally:
        h.close()
    return (v // 100 + 4) * 100


def one(snap: str, at: int, live: str | None, out: Path, flips: int) -> dict:
    h = Hatari(snapshot=snap)
    try:
        h.capture_frames(str(out), live=live, at_vbl=at, nth_flip=flips)
        f = h.fps(1000)
    finally:
        h.close()
    md = {n: hashlib.md5((out / n).read_bytes()[:VISIBLE]).hexdigest() for n in ("buf60000.bin", "buf70000.bin")}
    return {"fps": f["fps"], "flips": f["flips"], "md5": md, "dir": out}


def diffbytes(a: Path, b: Path) -> int:
    n = 0
    for f in ("buf60000.bin", "buf70000.bin"):
        x, y = (a / f).read_bytes()[:VISIBLE], (b / f).read_bytes()[:VISIBLE]
        n += sum(1 for i in range(len(x)) if x[i] != y[i])
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", required=True)
    ap.add_argument("--snapshot", nargs="*", default=DEFAULT_SNAPS)
    ap.add_argument("--flips", type=int, default=10)
    a = ap.parse_args()
    # Short, stable dir name: Hatari truncates long debugger command lines, which
    # silently broke `loadbin <long path>` for big patch sets (payload never loaded).
    tag = f"{a.only[0]}+{len(a.only)}-{hashlib.md5('+'.join(sorted(a.only)).encode()).hexdigest()[:8]}"
    live = GAME_DIR / "build" / "ab" / tag / "live"
    subprocess.run([sys.executable, str(GAME_DIR / "tools" / "mw2patch.py"), "live", "--only", *a.only,
                    "--out", str(live.relative_to(GAME_DIR))], check=True, cwd=GAME_DIR,
                   stdout=subprocess.DEVNULL)
    ok = True
    for snap in a.snapshot:
        at = at_vbl_for(snap)
        name = Path(snap).stem
        base_dir = GAME_DIR / "build" / "ab" / "base" / f"{name}_{at}_{a.flips}"
        pat_dir = GAME_DIR / "build" / "ab" / tag / f"{name}_{at}_{a.flips}"
        with ThreadPoolExecutor(2) as ex:
            fb = ex.submit(one, snap, at, None, base_dir, a.flips)
            fp = ex.submit(one, snap, at, str(live), pat_dir, a.flips)
            b, p = fb.result(), fp.result()
        same = b["md5"] == p["md5"]
        ok &= same
        nd = 0 if same else diffbytes(base_dir, pat_dir)
        print(f"{name}: pixels {'IDENTICAL' if same else f'DIFFER ({nd} bytes)'}; "
              f"fps base {b['fps']:.1f} ({b['flips']} flips) -> patched {p['fps']:.1f} ({p['flips']} flips)")
        print(f"   base {base_dir}\n   patched {pat_dir}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
