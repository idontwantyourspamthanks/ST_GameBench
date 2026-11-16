#!/usr/bin/env python3
"""Timer B ISR entry latency (LineCycles at $d616) while a real frame's type-0 draws are replayed with interrupts enabled: stock kernels vs the HOG blitter kernels."""
import sys, re, pickle, statistics, struct
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import unit, kb
budget = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
allc = pickle.load(open(HERE / "calls.pkl", "rb"))
S16 = lambda v: v - 65536 if v >= 32768 else v
out, syms = unit.assemble(HERE / "msb.s", [f"BUDGET={budget}"])
calls = [x for x in allc if x["sc"] == "race_start" and x["kind"] == "t0" and S16(x["rows"]) > 0 and x["cols"] and x["nib"] in (7, 11, 13, 15)]
# one frame worth: take the first 17 calls with interior geometry
sel = []
for x in calls:
    if x["x"] >= 0 and x["y"] >= 0 and (x["x"] >> 4) + x["cols"] + 1 <= 20 and x["rows"] <= 120:
        sel.append(x)
    if len(sel) == 17: break
def mk(kind):
    cs = []
    for x in sel:
        ptr = int.from_bytes(kb.D[x["ent"]:x["ent"] + 4], "big")
        k = x["kernel"] if kind == "stock" else syms[f"s_n{x['nib']}c{x['cols']}"]
        cs.append((k, x["x"], x["y"], S16(x["rows"]), 1, ptr))
    return cs
res = {}
for kind in ("stock", "blit"):
    f = kb.build(mk(kind), "isr" + kind)
    extra = [(0xd616, "e LineCycles\ne HBL\n")]
    tl, r, _ = unit.run(HERE / "kb3.s", "race_start", "ste", 1024, None, [], None, bins=[f"d0000:{f}", f"c2000:{out}"], timeout=300, extra=extra, defs=["LOOPS=30"])
    t = [c for n, c in tl if n in ("m_start", "m_end")]
    log = r["__log__"]
    lc = [int(m.group(1)) for m in re.finditer(r"> e LineCycles\n= [^\n]*#(\d+) \(dec\)", log)]
    res[kind] = (((t[1] - t[0]) & 0xffffffff) if len(t) >= 2 else None, lc)
    print(kind, "total cycles for 30 frames of draws (interrupts on):", res[kind][0], " Timer B ISR entries:", len(lc))
    if lc:
        lc.sort(); n = len(lc)
        print(f"   LineCycles at ISR entry: min {lc[0]} median {lc[n // 2]} p90 {lc[int(n * .9)]} p99 {lc[int(n * .99)]} max {lc[-1]}  (a scanline = 512 cycles)")
