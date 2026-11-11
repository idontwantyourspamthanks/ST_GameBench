#!/usr/bin/env python3
"""One benchmark job on a 1 MB ski snapshot (Midwinter 1).

    python3 work/bench.py SNAP [--mhz 8|16] [--fps 1000] [--profile 250] [--trace 300] --out work/bench

Writes work/bench/<snap>_<mhz>mhz.json with
  fps      {vbls, flips, fps, vbls_per_frame}   over --fps VBLs
  trace    [(vbl, x, z, speed, heading)] at every flip, over --trace VBLs   (world state per frame)
  profile  [(bucket_addr, cycles)]               bucketed by call target (m68dis.call_targets), --profile VBLs
Each measurement restores the snapshot afresh, so they all start from the same state.
"""
import argparse
import bisect
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME / "tools"))
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from mw1 import MW1, SNAP  # noqa: E402
import m68dis  # noqa: E402


def bucket(rows, targets):
    out = {}
    for addr, cyc in rows:
        i = bisect.bisect_right(targets, addr) - 1
        key = f"${targets[i]:x}" if (m68dis.CODE_LO <= addr < m68dis.CODE_HI and i >= 0) else f"ext${addr >> 16:x}xxxx"
        out[key] = out.get(key, 0) + cyc
    return sorted(out.items(), key=lambda kv: -kv[1])


def run(snap, mhz, what):
    h = MW1(snapshot=str(SNAP / f"{snap}.sav"))
    try:
        if mhz != 8:
            h.set_cpuclock(mhz)
        return what(h)
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snap")
    ap.add_argument("--mhz", type=int, default=8)
    ap.add_argument("--fps", type=int, default=1000)
    ap.add_argument("--profile", type=int, default=0)
    ap.add_argument("--trace", type=int, default=0)
    ap.add_argument("--out", default=str(HERE / "bench"))
    a = ap.parse_args()
    res = {"snap": a.snap, "mhz": a.mhz}
    if a.fps:
        res["fps"] = run(a.snap, a.mhz, lambda h: h.fps(a.fps))
    if a.trace:
        res["trace"] = run(a.snap, a.mhz, lambda h: h.flip_trace(a.trace))
    if a.profile:
        def prof(h):
            ram = HERE / "bench" / f"ram_tmp_{a.snap}_{a.mhz}.bin"
            ram.parent.mkdir(exist_ok=True)
            h.dump(str(ram), 0, 0x100000)
            rows = h.profile(a.profile)
            data = ram.read_bytes()
            ram.unlink()
            tg = m68dis.call_targets(data)
            tot = sum(c for _, c in rows)
            return {"vbls": a.profile, "total_cycles": tot, "instr_addrs": len(rows),
                    "buckets": bucket(rows, tg)[:60]}
        res["profile"] = run(a.snap, a.mhz, prof)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.snap}_{a.mhz}mhz.json").write_text(json.dumps(res))
    print(json.dumps({k: v for k, v in res.items() if k not in ("trace", "profile")}))


if __name__ == "__main__":
    main()
