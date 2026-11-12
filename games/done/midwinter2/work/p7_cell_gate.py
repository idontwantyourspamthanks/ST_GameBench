#!/usr/bin/env python3
"""P7 cell-cull gate: p4 baseline vs p4 + patches, pixel identity and cycles per frame.

    python3 work/p7_cell_gate.py [--flips 10 40] [--snapshot S ...] [--mine p7_cell_pre p7_cell_cull]

For each snapshot and flip count: capture both screen buffers with the p4 default set applied live
(base) and with p4 set + --mine applied live, at the same absolute VBL and flip (Hatari.capture_frames),
compare md5.
Max two Hatari instances at a time.
"""
import argparse, hashlib, json, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari  # noqa: E402

P4 = ["p4_grid", "p4_hud_pfx_fill", "p4_hud_pfx_replay", "p4_hud_pfx_ymin", "p4_hud_reset",
      "p4_proj_axis", "p4_proj_cols", "p4_proj_div", "p4_walk", "p4_walk_c4", "p4_walk_ret", "p4_walk_tab"]
SNAPS = ["work/snapshots/1mb_ingame_walking.sav", "work/snapshots/1mb_ingame_foot.sav",
         "work/snapshots/ingame_foot_banked_turn.sav"]


def mk_live(names, tag):
    out = ROOT / "build" / "p7cell" / tag / "live"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "mw2patch.py"), "live", "--only", *names,
                    "--out", str(out.relative_to(ROOT))], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    return out


def at_vbl_for(snap):
    h = Hatari(snapshot=snap)
    try:
        v = h.vbl()
    finally:
        h.close()
        shutil.rmtree(h.R, ignore_errors=True)
    return (v // 100 + 4) * 100


def cap(snap, at, live, out, flips):
    h = Hatari(snapshot=snap)
    try:
        h.capture_frames(str(out), live=str(live), at_vbl=at, nth_flip=flips)
    finally:
        h.close()
        shutil.rmtree(h.R, ignore_errors=True)
    return {n: hashlib.md5((out / n).read_bytes()).hexdigest() for n in ("buf60000.bin", "buf70000.bin")}


def diffbytes(a, b):
    n = 0
    for f in ("buf60000.bin", "buf70000.bin"):
        x, y = (a / f).read_bytes(), (b / f).read_bytes()
        n += sum(1 for i in range(len(x)) if x[i] != y[i])
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flips", type=int, nargs="+", default=[10, 40])
    ap.add_argument("--snapshot", nargs="*", default=SNAPS)
    ap.add_argument("--mine", nargs="+", default=["p7_cell_pre", "p7_cell_cull"])
    ap.add_argument("--base-extra", nargs="*", default=[])
    a = ap.parse_args()
    base = mk_live(P4 + a.base_extra, "base_" + "_".join(a.base_extra or ["p4"]))
    mine = mk_live(P4 + a.base_extra + a.mine, "mine_" + "_".join(a.mine))
    ok = True
    for snap in a.snapshot:
        at = at_vbl_for(snap)
        name = Path(snap).stem
        for fl in a.flips:
            bd = ROOT / "build" / "p7cell" / "cap" / f"base_{name}_{at}_{fl}"
            md = ROOT / "build" / "p7cell" / "cap" / f"mine_{'_'.join(a.mine)}_{name}_{at}_{fl}"
            with ThreadPoolExecutor(2) as ex:
                fb = ex.submit(cap, snap, at, base, bd, fl)
                fm = ex.submit(cap, snap, at, mine, md, fl)
                b, m = fb.result(), fm.result()
            same = b == m
            ok &= same
            nd = 0 if same else diffbytes(bd, md)
            print(f"{name} at_vbl={at} flips={fl}: {'IDENTICAL' if same else f'DIFFER ({nd} bytes)'}  "
                  f"md5 {b['buf60000.bin'][:8]} {b['buf70000.bin'][:8]} | {m['buf60000.bin'][:8]} {m['buf70000.bin'][:8]}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
