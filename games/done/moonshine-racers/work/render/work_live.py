#!/usr/bin/env python3
"""Raw work per pass (cycles) keyed by the pass counter $100e, stock vs live-patched, mt_* OFF unless named.

    MSRPATCH_TOOL=work/render/msrpatch_priv.py python3 work/render/work_live.py SNAP [--only mr_edge ...] [--passes 40] [--out FILE.json]
A chain of one-shot breakpoints at the loop top ($796a) and the flip entry ($d1ca) logs `e VBL`, `e FrameCycles` and `m $100e 2`; pass work =
t($d1ca) - t($796a) (interrupts included, idle wait excluded: the stock wait is AFTER the flip entry).  Absolute time = VBL*160256 + FrameCycles with
the frame-wrap offset fitted as in tools/msrstages.py.  Prints mean/min/max over the passes and (with --out) saves {pass: cycles} for a
same-pass comparison between runs (`--cmp A.json B.json`)."""
import argparse, json, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
from msr import Moonshine  # noqa
import msrabtest as ab  # noqa

CYC = 160256


def measure(snap, live, npass, tag="w"):
    h = Moonshine(snapshot=snap)
    try:
        time.sleep(1.5)
        if live:
            ab.apply_live(h, live, 0x7A88)
        time.sleep(0.5)
        pcs = [0x796A, 0xD1CA]
        for i, pc in enumerate(pcs):
            nxt = pcs[(i + 1) % 2]
            (h.R / f"{tag}_{pc:x}.txt").write_text(f"e VBL\ne FrameCycles\nm $100e 2\nb pc = ${nxt:x} :trace :once :file {h.R}/{tag}_{nxt:x}.txt\n")
        h.debug("b all", 0.3)
        n0 = len(h._logtext())
        h.cmd(f"hatari-debug b pc = $796a :trace :once :file {h.R}/{tag}_796a.txt")
        t0 = time.time()
        while h._logtext()[n0:].count("$100e") < 0 or len(re.findall(r"#\d+ \(dec\)", h._logtext()[n0:])) < npass * 4:
            if time.time() - t0 > 900:
                break
            time.sleep(1)
        h.debug("b all", 0.5)
        log = h._logtext()[n0:]
    finally:
        h.close()
    ev = []   # (pc, vbl, fc, pass)
    cur = None; vals = []
    for ln in log.splitlines():
        m = re.match(r"\tpc = \$([0-9a-f]+) :once :trace", ln)
        if m:
            if cur is not None and len(vals) == 3: ev.append((cur, *vals))
            cur = int(m.group(1), 16); vals = []; continue
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m and cur is not None: vals.append(int(m.group(1))); continue
        m = re.match(r"([0-9a-f]{8}):\s+([0-9a-f]{2}) ([0-9a-f]{2})", ln, re.I)
        if m and cur is not None and int(m.group(1), 16) == 0x100E: vals.append(int(m.group(2) + m.group(3), 16))
    if cur is not None and len(vals) == 3: ev.append((cur, *vals))
    raw = [(pc, v, fc, p) for pc, v, fc, p in ev]
    best = None
    for c0 in sorted({fc for _, _, fc, _ in raw}) + [CYC]:
        t = [(v + (1 if fc < c0 else 0)) * CYC + fc for _, v, fc, _ in raw]
        bad = sum(1 for i in range(1, len(t)) if t[i] < t[i - 1])
        if best is None or bad < best[0]: best = (bad, c0)
    c0 = best[1]
    tt = [(pc, (v + (1 if fc < c0 else 0)) * CYC + fc, p) for pc, v, fc, p in raw]
    res = {}
    for i in range(1, len(tt)):
        if tt[i][0] == 0xD1CA and tt[i - 1][0] == 0x796A:
            res[tt[i - 1][2]] = tt[i][1] - tt[i - 1][1]
    # period: loop top to next loop top
    per = {}
    for i in range(2, len(tt)):
        if tt[i][0] == 0x796A and tt[i - 2][0] == 0x796A:
            per[tt[i - 2][2]] = tt[i][1] - tt[i - 2][1]
    return res, per, best[0]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("snap", nargs="?")
    ap.add_argument("--only", nargs="*", default=[]); ap.add_argument("--passes", type=int, default=40)
    ap.add_argument("--out"); ap.add_argument("--cmp", nargs=2)
    a = ap.parse_args()
    if a.cmp:
        x, y = (json.load(open(f))["work"] for f in a.cmp)
        com = sorted(set(x) & set(y), key=int)
        mx = sum(x[k] for k in com) / len(com); my = sum(y[k] for k in com) / len(com)
        print(f"common passes {len(com)}: {a.cmp[0]} mean {mx:,.0f} ({mx / CYC:.3f} VBL) -> {a.cmp[1]} mean {my:,.0f} ({my / CYC:.3f} VBL): saving {mx - my:,.0f} cycles = {100 * (mx - my) / mx:.1f}%")
        return
    snap = ab.snap_path(a.snap)
    live = ab.live_build(a.only) if a.only else None
    res, per, bad = measure(snap, live, a.passes)
    v = list(res.values())
    print(f"{a.snap} {'+'.join(a.only) or 'stock'}: {len(v)} passes, wrap violations {bad}; work/pass mean {sum(v) / len(v):,.0f} cycles = {sum(v) / len(v) / CYC:.3f} VBL, min {min(v):,} max {max(v):,}; "
          f"period mean {(sum(per.values()) / max(1, len(per))) / CYC:.3f} VBL")
    if a.out:
        json.dump({"work": {str(k): x for k, x in res.items()}, "period": {str(k): x for k, x in per.items()}}, open(a.out, "w"))


if __name__ == "__main__":
    main()
