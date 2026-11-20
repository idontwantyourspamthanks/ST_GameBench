#!/usr/bin/env python3
"""Cycles of work per pass, stock vs live-patched (mt_* OFF unless named), from Hatari's instruction profile.

    MSRPATCH_TOOL=work/render/msrpatch_priv.py python3 work/render/prof_live.py SNAP NAME [--only mr_edge ...] [--vbls 150]
Writes work/render/prof/<name>.txt (profile save) and prints: passes (executions of the flip $d1ca), cycles/pass total, idle-wait cycles/pass
($d206-$d21b spin of the stock sync), WORK = total - idle (interrupts included), in cycles and VBL (160256 cycles/VBL), and the per-routine
exclusive cycles per pass for --ranges."""
import argparse, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
from msr import Moonshine, prof  # noqa
import msrabtest as ab  # noqa

LINE = re.compile(r"^\$([0-9a-f]+)\s.*% \((\d+), (\d+), \d+, \d+\)\s*$", re.I)
CYC = 160256


def load(path):
    d = {}
    for ln in open(path):
        m = LINE.match(ln)
        if m:
            d[int(m.group(1), 16)] = (int(m.group(3)), int(m.group(2)))
    return d


def summarize(path, ranges):
    d = load(path)
    flips = d[0xD1CA][1]
    tot = sum(c for c, _ in d.values())
    idle = sum(c for a, (c, _) in d.items() if 0xD206 <= a < 0xD21C)
    out = {"passes": flips, "total/pass": tot / flips, "idle/pass": idle / flips, "work/pass": (tot - idle) / flips,
           "work VBL": (tot - idle) / flips / CYC}
    for nm, (lo, hi) in ranges.items():
        out[nm] = sum(c for a, (c, _) in d.items() if lo <= a < hi) / flips
    return out


RANGES = {"edge $1058a": (0x1058A, 0x10800), "geom $100b4": (0x100B4, 0x10580), "road $17c24": (0x17C24, 0x18070), "horizon $18318": (0x18318, 0x18400),
          "clouds $de1c": (0xDE1C, 0xDEEE), "cloudk $122e4/$15052": (0x122E4, 0x1235E), "minimap $f22c": (0xF22C, 0xF3B6), "map $12690": (0x12690, 0x12788),
          "lines $127fa": (0x127FA, 0x12900), "score $f3b6/$11d42": (0xF3B6, 0xF430)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("name")
    ap.add_argument("--only", nargs="*", default=[]); ap.add_argument("--vbls", type=int, default=150)
    a = ap.parse_args()
    snap = ab.snap_path(a.snap)
    live = ab.live_build(a.only) if a.only else None
    out = HERE / "prof" / f"{a.name}.txt"
    out.parent.mkdir(exist_ok=True)
    h = Moonshine(snapshot=snap)
    try:
        time.sleep(2)
        if live:
            ab.apply_live(h, live, 0x7A88)
        time.sleep(1)
        v0 = h.vbl()
        while h.vbl() < v0 + 40:       # settle
            time.sleep(0.3)
        prof(h, a.vbls, str(out))
    finally:
        h.close()
    r = summarize(out, RANGES)
    print(f"{a.name}: " + "; ".join(f"{k} {v:,.0f}" if not k.endswith("VBL") else f"{k} {v:.3f}" for k, v in r.items()))


if __name__ == "__main__":
    main()
