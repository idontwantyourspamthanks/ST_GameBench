#!/usr/bin/env python3
"""Options (a) pre-masked, (b) pre-shifted, (c) generated kernel: real Hatari cycles vs the stock kernel, same screen checksums required."""
import argparse, re, struct, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import unit, kb
D = kb.D
def rows_of(ptr, w, h, c, P=3):
    out = []
    for r in range(h):
        base = ptr + r * c * 2 * P
        cols = [[0] * P for _ in range(c)]
        for col in range(c):
            for p in range(P):
                if col < 2 and c >= 2: off = (p * 2 + col) * 2
                elif c == 1: off = p * 2
                else: off = 4 * P + (col - 2) * 2 * P + p * 2
                cols[col][p] = struct.unpack(">H", D[base + off:base + off + 2])[0]
        out.append(cols)
    return out
def shifted(cols, s):
    c = len(cols); P = len(cols[0]); res = []
    for k in range(c + 1):
        res.append([(((cols[k - 1][p] << (16 - s)) if k > 0 else 0) | ((cols[k][p] >> s) if k < c else 0)) & 0xffff for p in range(P)])
    return res
def build_pb(ptr, w, h, c, s, rows):
    b = bytearray()
    for cols in rows_of(ptr, w, h, c)[:rows]:
        for out in shifted(cols, s):
            m = out[0] | out[1] | out[2]
            b += struct.pack(">IIII"[:3] if False else ">III", (~m & 0xffff) << 16 | (~m & 0xffff), out[0] << 16 | out[1], out[2] << 16)
    return bytes(b)
def build_pa(ptr, w, h, rows, s):
    b = bytearray()
    for cols in rows_of(ptr, w, h, 1)[:rows]:
        p = cols[0]; m = p[0] | p[1] | p[2]
        b += struct.pack(">HHHH", p[0], p[1], p[2], (~m & 0xffff) if s == 0 else m)
    return bytes(b)
ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
ap.add_argument("--snap", default="race_start"); ap.add_argument("--reps", type=int, default=3); ap.add_argument("--clock", type=int)
a = ap.parse_args()
out, syms = unit.assemble(HERE / "mk.s", [])
BASE = 0xD4000
blob = bytearray(); cases = [(0x122e8, 0, 0, 1, a.reps, 0x30000)]; meta = ["calib"]
def addcase(kind, k, x, rows, a1, tag):
    cases.append((k, x, 80, rows, a.reps, a1)); meta.append((kind, tag))
def put(data):
    off = BASE + len(blob); blob.extend(data)
    while len(blob) % 4: blob.append(0)
    return off
e1 = kb.pick(7, 1); e2 = kb.pick(7, 2); e4 = kb.pick(7, 4)
for s in (0, 4, 8, 12):
    x = 96 + s
    r1 = min(e1["h"], 10)
    addcase("stock", kb.FULL[(7, 1)], x, r1, e1["ptr"], f"c1 s{s} rows{r1}")
    if s == 0: addcase("(a) premasked aligned", syms["pa_al"], x, r1, put(build_pa(e1["ptr"], e1["w"], e1["h"], r1, 0)), f"c1 s{s} rows{r1}")
    else:
        addcase("(a) premasked shifted", syms["pa_sh"], x, r1, put(build_pa(e1["ptr"], e1["w"], e1["h"], r1, s)), f"c1 s{s} rows{r1}")
        addcase("(c) generated+zeroskip", syms["pc_c1"], x, r1, e1["ptr"], f"c1 s{s} rows{r1}")
    r2 = min(e2["h"], 16)
    addcase("stock", kb.FULL[(7, 2)], x, r2, e2["ptr"], f"c2 s{s} rows{r2}")
    if s: addcase("(b) preshifted", syms["pb_n3"], x, r2, put(build_pb(e2["ptr"], e2["w"], e2["h"], 2, s, r2)), f"c2 s{s} rows{r2}")
    r4 = min(e4["h"], 16)
    addcase("stock", kb.FULL[(7, 4)], x, r4, e4["ptr"], f"c4 s{s} rows{r4}")
    if s: addcase("(b) preshifted", syms["pb_n5"], x, r4, put(build_pb(e4["ptr"], e4["w"], e4["h"], 4, s, r4)), f"c4 s{s} rows{r4}")
f = kb.build(cases, "mk"); datf = HERE / "mk_data.bin"; datf.write_bytes(bytes(blob))
n = len(cases)
tl, res, _ = unit.run(HERE / "kb.s", a.snap, a.machine, a.mem, a.clock, [f"d8000:{4 * n}"], None, bins=[f"d0000:{f}", f"c3000:{out}", f"d4000:{datf}"], timeout=600)
cyc = []; mc = None
for name, c in tl:
    if name == "m_case": mc = c
    elif name == "m_end" and mc is not None: cyc.append((c - mc) & 0xffffffff); mc = None
txt = [v for k, v in res.items() if k.startswith("d8000")][0]
bs = b"".join(bytes.fromhex(m.group(2).replace(" ", "")) for m in re.finditer(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ?){1,16})", txt, re.M))
sums = [struct.unpack(">I", bs[i:i + 4])[0] for i in range(0, min(len(bs), 4 * n), 4)]
base = cyc[0] / a.reps; ref = {}
for i in range(1, n):
    kind, tag = meta[i]; c = cyc[i] / a.reps - base
    if kind == "stock": ref[tag] = (c, sums[i]); print(f"{tag:22s} {kind:24s} {c:8.0f}")
    else:
        rc, rs = ref[tag]; print(f"{tag:22s} {kind:24s} {c:8.0f}  ratio {c / rc:5.2f}  {'IDENTICAL' if sums[i] == rs else 'DIFFER'}")
