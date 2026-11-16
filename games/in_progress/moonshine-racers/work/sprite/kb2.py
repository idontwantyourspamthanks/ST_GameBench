#!/usr/bin/env python3
"""Stock full-entry kernels vs the blitter prototype (msb.s) on the real sprite banks: cycles and screen checksums.
    python3 work/sprite/kb2.py [--machine ste] [--mem 1024] [--clock N] [--snap race_start] [--reps 4] [--budget 1800]"""
import argparse, sys, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import unit, kb

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--clock", type=int); ap.add_argument("--snap", default="race_start"); ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--budget", type=int, default=1800); ap.add_argument("--rows", type=int, default=16); ap.add_argument("--out")
    ap.add_argument("--shifts", nargs="*", type=int, default=[0, 3, 4, 8, 15]); ap.add_argument("--cols", nargs="*", type=int, default=[1, 2, 3, 4])
    ap.add_argument("--nibs", nargs="*", type=int, default=[7, 11, 15])
    a = ap.parse_args()
    out, syms = unit.assemble(HERE / "msb.s", [f"BUDGET={a.budget}"])
    cases = [(0x122e8, 0, 0, 1, a.reps, 0x30000)]; meta = ["calib"]
    for nib in a.nibs:
        for cols in a.cols:
            e = kb.pick(nib, cols)
            if not e: continue
            rows = min(e["h"], a.rows)
            for s in a.shifts:
                x = 96 + s
                for kind in ("stock", "blit"):
                    k = kb.FULL[(nib, cols)] if kind == "stock" else syms[f"s_n{nib}c{cols}"]
                    cases.append((k, x, 80, rows, a.reps, e["ptr"])); meta.append((kind, nib, cols, s, rows))
    f = kb.build(cases, "cmp")
    n = len(cases)
    # extra binary: msb at $C2000, loaded with the harness
    tl, res, _ = unit.run(HERE / "kb.s", a.snap, a.machine, a.mem, a.clock, [f"d8000:{4 * n}"], None, bins=[f"d0000:{f}", f"c2000:{out}"], timeout=900)
    cyc = []; mc = None
    for name, c in tl:
        if name == "m_case": mc = c
        elif name == "m_end" and mc is not None: cyc.append((c - mc) & 0xffffffff); mc = None
    txt = list(res.values())[0] if res else ""
    bs = b"".join(bytes.fromhex(m.group(2).replace(" ", "")) for m in re.finditer(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ?){1,16})", txt, re.M))
    import struct
    sums = [struct.unpack(">I", bs[i:i + 4])[0] for i in range(0, min(len(bs), 4 * n), 4)]
    base = cyc[0] / a.reps
    lines = []
    i = 1
    while i + 1 < n:
        st, bl = meta[i], meta[i + 1]
        cs, cb = cyc[i] / a.reps - base, cyc[i + 1] / a.reps - base
        same = sums[i] == sums[i + 1]
        lines.append(f"n{st[1]:2d} c{st[2]} s{st[3]:2d} rows{st[4]:3d}  stock {cs:8.0f}  blit {cb:8.0f}  ratio {cb / cs:5.2f}  {'IDENTICAL' if same else 'DIFFER'}")
        i += 2
    print("\n".join(lines))
    if a.out: Path(a.out).write_text("\n".join(lines) + "\n")

main()
