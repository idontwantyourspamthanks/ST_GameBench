#!/usr/bin/env python3
"""World-rate and fps gates for triple buffering (HunterTB2; notes work/notes/triple.md section 6).

    python3 tools/hunttb_rate.py world [--hz 50 60] [--mhz 8 16]     item 1: player u/s, hn_hz ticks/s, clock ticks/s, fps; base vs tb
    python3 tools/hunttb_rate.py fps   [--mhz 8]                     item 2: fps on the 7 scenes, base vs tb

Reuses hunthz.trace (the loop-top logger) but applies the live patch set at the 3D LOOP TOP `$253e`, not at the flip `$5fee`
(the tb flip never executes $5fee).  Everything is counted in VBLs (the run is fast-forwarded: wall clock means nothing).
base = p4_ikbd p4_edge p4_poly snd_core hn_hz (the v1.1 default set minus jag_*, whose site $c64c is the hunthz stick-poke
breakpoint); tb = base + tb_flip tb_frame tb_vbl.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
import hunthz  # noqa: E402

hunthz.FLIP = hunthz.LOOP
BASE = hunthz.BASE_SET + ["hn_hz"]
TB = BASE + ["tb_flip", "tb_frame", "tb_vbl"]
SETS = {"base": BASE, "tb": TB}
SCENES = [("foot_stand", "none"), ("foot_walk", "up"), ("car_stand", "none"), ("car_drive", "up"),
          ("car_turn", "upleft"), ("hills_stand", "none"), ("4mb_foot_stand", "none")]


def one(snap, label, hz, mhz, hold, secs, ta, tb):
    t = hunthz.trace(snap, SETS[label], hz, mhz, int(secs * hz) + 20, hold, "tbr_" + label)
    rows = t["rows"]
    if len(rows) < 3:
        return {"snap": snap, "set": label, "hz": hz, "mhz": mhz, "error": f"{len(rows)} loop tops"}
    r = hunthz.rates(rows, hz, ta, tb)
    r.update(snap=snap, set=label, hz=hz, mhz=mhz, hold=hold)
    return r


def run(jobs):
    with ThreadPoolExecutor(2) as ex:
        futs = [ex.submit(one, *j) for j in jobs]
        out = []
        for f in futs:
            r = f.result()
            print("ROW " + json.dumps(r), flush=True)
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["world", "fps"])
    ap.add_argument("--hz", nargs="*", type=int, default=[50, 60])
    ap.add_argument("--mhz", nargs="*", type=int, default=[8, 16])
    ap.add_argument("--scenes", nargs="*", default=None)
    a = ap.parse_args()
    if a.cmd == "world":
        jobs = [("foot_walk", lb, hz, mhz, "up", 10, 1.0, 9.0) for lb in SETS for hz in a.hz for mhz in a.mhz]
        rows = run(jobs)
        print("\nset  hz MHz | u/s     | hn_hz ticks/s | clock ticks/s | frames/s | cycles/VBL")
        for r in rows:
            if "error" in r:
                print(r)
                continue
            print(f"{r['set']:4s} {r['hz']:2d} {r['mhz']:3d} | {r['dZ_u_s']:7} | {r['ticks_per_s']:13} | {r['clock_ticks_per_s']:13} | "
                  f"{r['fps']:8} | {r['cycles_per_vbl']}")
    else:
        sc = [s for s in SCENES if not a.scenes or s[0] in a.scenes]
        jobs = [(s, lb, 50, mhz, h, 12, 1.0, 11.0) for s, h in sc for mhz in a.mhz for lb in SETS]
        rows = run(jobs)
        print("\nscene            MHz | base fps | tb fps | gain")
        for s, _ in sc:
            for mhz in a.mhz:
                b = next(r for r in rows if r["snap"] == s and r["set"] == "base" and r["mhz"] == mhz)
                t = next(r for r in rows if r["snap"] == s and r["set"] == "tb" and r["mhz"] == mhz)
                if "error" in b or "error" in t:
                    print(s, b, t)
                    continue
                print(f"{s:16s} {mhz:3d} | {b['fps']:8} | {t['fps']:6} | {100 * (t['fps'] / b['fps'] - 1):+.1f} %   "
                      f"(VBL/frame {50 / b['fps']:.2f} -> {50 / t['fps']:.2f})")


if __name__ == "__main__":
    main()
