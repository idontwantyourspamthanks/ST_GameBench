#!/usr/bin/env python3
"""Object-zoo campaigns for the test-drive crash hunt (RESULTS_tdcrash.md): ONE track, base level 0, straight (segments of 256 units), the BAR at 19958, and
  zoo1.trk  every non-BAR type of the base level's type list once (131 types), 12 units apart from unit 150, lateral cycling -100 / 0 / 100 / -128 / 127 / 40
  zoo2.trk  the same 131 types as a CLUSTER: 1 unit apart from unit 1500 (131 objects in 131 units: far more than the 32 scenery slots), extreme laterals
  zoo3.trk  every type again at 3 lateral extremes (-128, 0, 127) in three clusters
  python3 work/edgate/mkzoo.py"""
import sys, copy
from pathlib import Path
HERE = Path(__file__).resolve().parent; G = HERE.parents[1]
sys.path.insert(0, str(G / "tools"))
import msrtrack as M
ms2 = M.read_ms2()
base, _ = M.decode_stock(ms2, 0)
bt = {n + 1 for n, e in enumerate(base["types"]) if e[2] == M.BAR_SPRITE}
nonbar = [n + 1 for n in range(len(base["types"])) if n + 1 not in bt]
BAR = sorted(bt)[0]
LAT = [-100, 0, 100, -128, 127, 40]
def track(name, objs):
    t = copy.deepcopy(base); t["name"] = name
    t["curve"] = [[256, 0]] * 128; t["left"] = [[256, 36]] * 128; t["right"] = [[256, 34]] * 128; t["hill"] = [[256, 0]] * 128
    objs = sorted(objs + [(19958, BAR, 0)])
    t["objects"] = [{"at": a, "type": ty, "lateral": la} for a, ty, la in objs]
    iss = [x for x in M.validate_track(t) if x.level == "ERROR"]
    assert not iss, iss
    return t
z1 = track("ZOO SPREAD", [(150 + 12 * i, ty, LAT[i % 6]) for i, ty in enumerate(nonbar)])
z2 = track("ZOO CLUSTER", [(1500 + i, ty, LAT[i % 6]) for i, ty in enumerate(nonbar)])
z3 = track("ZOO EXTREMES", [(150 + 400 * c + 2 * i, ty, (-128, 0, 127)[c]) for c in range(3) for i, ty in enumerate(nonbar)])
for n, t in (("zoo1", z1), ("zoo2", z2), ("zoo3", z3)):
    blk = M.encode_track(t); (HERE / f"{n}.trk").write_bytes(M.build_campaign([(t["name"], 0, blk)]))
    print(n, len(blk), "bytes", len(t["objects"]), "objects", [x.code if hasattr(x, "code") else x for x in M.validate_track(t)][:4])
