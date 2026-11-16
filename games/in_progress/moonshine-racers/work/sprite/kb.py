#!/usr/bin/env python3
"""Kernel benchmark / differential driver (harness kb.s): stock kernels (and later the ms_ kernels) on the real sprite banks.
    python3 work/sprite/kb.py [--machine ste] [--mem 1024] [--clock N] [--snap race_start] [--set stock] [--reps 8]"""
import argparse, json, re, struct, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import unit
D = open(HERE.parent / "dumps/ram_race_start.bin", "rb").read()
L = lambda a: struct.unpack(">I", D[a:a + 4])[0]
W = lambda a: struct.unpack(">H", D[a:a + 2])[0]
FULL = {(7, 1): 0x12994, (11, 1): 0x12a98, (13, 1): 0x12bac, (15, 1): 0x12ce0, (7, 2): 0x12f60, (11, 2): 0x130e2, (13, 2): 0x1327e, (15, 2): 0x1345a,
        (7, 3): 0x13662, (11, 3): 0x1384c, (13, 3): 0x13a5e, (15, 3): 0x13cc8, (7, 4): 0x13f6e, (11, 4): 0x141cc, (13, 4): 0x1445c, (15, 4): 0x1475a}
BANKS = [(0x3d16e, 280), (0x5a402, 64), (0x306c4, 96), (0x2156a, 45)]


def entries():
    out = []
    for base, n in BANKS:
        for i in range(n):
            a = base + 14 * i
            p = L(a); w = W(a + 4); h = W(a + 6); fl = W(a + 12) & 15
            out.append(dict(ptr=p, w=w, h=h, nib=fl, cols=(w + 15) // 16, ent=a))
    return out


def pick(nib, cols, minrows=8):
    c = [e for e in entries() if e["nib"] == nib and e["cols"] == cols and e["h"] >= minrows and e["w"] > 16 * (cols - 1)]
    c.sort(key=lambda e: -e["h"])
    return c[0] if c else None


def build(cases, tag):
    b = struct.pack(">H", len(cases))
    for k, x, y, rows, reps, a1 in cases:
        b += struct.pack(">IhhhHI", k, x, y, rows, reps, a1)
    f = HERE / f"cases_{tag}.bin"
    f.write_bytes(b)
    return f


def run_cases(cases, tag, machine="ste", mem=1024, clock=None, snap="race_start", live=None):
    f = build(cases, tag)
    n = len(cases)
    tl, res, syms = unit.run(HERE / "kb.s", snap, machine, mem, clock, [f"d8000:{4 * n}"], live, bins=[f"d0000:{f}"], timeout=600)
    # timeline: pairs m_case, m_end
    cyc = []
    mc = None
    for name, c in tl:
        if name == "m_case": mc = c
        elif name == "m_end" and mc is not None: cyc.append((c - mc) & 0xffffffff); mc = None
    sums = []
    txt = list(res.values())[0] if res else ""
    for m in re.finditer(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ?){1,16})", txt, re.M):
        pass
    bs = b"".join(bytes.fromhex(m.group(2).replace(" ", "")) for m in re.finditer(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ?){1,16})", txt, re.M))
    sums = [struct.unpack(">I", bs[i:i + 4])[0] for i in range(0, min(len(bs), 4 * n), 4)]
    return cyc, sums


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--clock", type=int); ap.add_argument("--snap", default="race_start"); ap.add_argument("--reps", type=int, default=8)
    a = ap.parse_args()
    cases = []; meta = []
    # harness overhead calibration: kernel = an rts ($1235c? use $12998 is 'rts'?) -> use ROM-less address of a known rts: $122e8 is `rts`
    cases.append((0x122e8, 0, 0, 1, a.reps, 0x30000)); meta.append("calib")
    for nib in (7, 11, 13, 15):
        for cols in (1, 2, 3, 4):
            e = pick(nib, cols)
            if not e: continue
            rows = min(e["h"], 16)
            for s in (0, 1, 4, 8, 12, 15):
                x = 100 + s
                cases.append((FULL[(nib, cols)], x, 80, rows, a.reps, e["ptr"])); meta.append(f"n{nib} c{cols} s{s} rows{rows} {e['w']}x{e['h']}")
    cyc, sums = run_cases(cases, "stock", a.machine, a.mem, a.clock, a.snap)
    base = cyc[0] / a.reps if cyc else 0
    print("calibration (rts kernel) per rep:", base)
    for m, c, s in zip(meta, cyc, sums):
        print(f"{m:36s} {c / a.reps - base:9.0f} cyc/call   sum {s:08x}")
