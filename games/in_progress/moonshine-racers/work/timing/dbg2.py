import sys, re; sys.path.insert(0,'.')
from tlib import *
from live import *
from tickpatch import sync_only
variant, mhz = sys.argv[1], int(sys.argv[2])
blobs, sites, sy = (sync_only("sync2.s") if variant == "E" else sync_only("sync3.s") if variant == "F" else ([], [], {}))
h = open_snap("ste1m_race_start.sav", mhz)
try:
    if sites: apply_live(h, blobs, sites)
    time.sleep(1)
    pcs=[0x7a88, 0x7b0a, 0x17c42, 0x7b74, 0xd1ca, 0x7b7a, 0x7b86]
    if variant in ("E", "F"): pcs=[0x7a88, sy["wait"], 0x17c42, 0x7b74, 0xd1ca, 0x7b7a, 0x7b86]
    log = chain(h, pcs, ["e VBL","e FrameCycles"], 8, tag=f"d{variant}{mhz}")
finally:
    h.close()
ev = parse_chain(log, 2)
rows = [(pc, v[0][1], v[1][1]) for pc, v in ev if len(v) >= 2 and v[0][0] == "e" and v[1][0] == "e"]
best = None
for c0 in sorted({r[2] for r in rows}) + [CYC]:
    t = [(r[1] + (1 if r[2] < c0 else 0)) * CYC + r[2] for r in rows]
    bad = sum(1 for i in range(1, len(t)) if t[i] < t[i-1])
    if best is None or bad < best[0]: best = (bad, c0)
bad, c0 = best
t = [(r[1] + (1 if r[2] < c0 else 0)) * CYC + r[2] for r in rows]
t0 = t[0]
print(variant, mhz, "rows", len(rows), "viol", bad, "c0", c0)
for r, tt in list(zip(rows, t))[-14:]:
    print(f"{r[0]:05x} t={(tt - t0) / CYC:8.3f}")
