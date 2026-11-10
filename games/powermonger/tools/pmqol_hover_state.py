#!/usr/bin/env python3
"""World-state equality gate for qol_hover(+qol_hover2): U = tick set + pm_tooltip, P = U + qol_hover + qol_hover2; both restore the same snapshot,
get the same pokes at the first flip (pointer resting on a house of settlement 0, optional world pokes), and dump RAM $0-$60000 at every loop top
(pmtick.log_passes); compared per world tick with pmtick's masks (+ the two hook sites).  The tooltip buffer lives at $CDC00 (not in the compared range).
    python3 tools/pmqol_hover_state.py [--invent] [--item] [--mhz 8] [--vbls 1000]"""
import argparse, sys, threading, time
import pmab, pmtick
from pm import PM, SNAP
ap = argparse.ArgumentParser()
ap.add_argument("--invent", action="store_true", help="poke $57fd4 = $e (Invent selected): 'Invent here: ...'")
ap.add_argument("--item", action="store_true", help="poke settlement 0 to making swords 7/14 (workshop text with a percentage)")
ap.add_argument("--mhz", type=int, default=8)
ap.add_argument("--vbls", type=int, default=1000)
ap.add_argument("--snap", default="get_men")
a = ap.parse_args()
pmtick.SITE_MASKS += [(0x12138, 0x1213E), (0x130B6, 0x130BC), (0x13034, 0x1303A), (0x194C, 0x1956), (0x1956, 0x1960)]   # + test_walk sites (the pointer driver both runs carry)
pokes = ["w $ce0c0 $00 $df $00 $6c"]        # test_walk: the pointer held at (223,108) in BOTH runs (as pmqol_ab does)
if a.item:
    pokes += ["w $4e520 $00 $04", "w $4e524 $00 $07"]
if a.invent:
    pokes += ["w $57fd4 $00 $0e"]
base = pmab.TICK + pmab.TESTSET + ["pm_tooltip"]
lu, lp = pmab.make_live(base), pmab.make_live(base + ["qol_hover", "qol_hover2"])
_orig = pmtick.apply_cmds
pmtick.apply_cmds = lambda live: _orig(live) + pokes        # pokes AFTER the loadbin (it would overwrite test_walk's table)
res = {}
def one(name, lv):
    h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
    try:
        time.sleep(1.5)
        res[name] = pmtick.log_passes(h, lv, a.mhz, a.vbls, name)
        res[name + "_st"] = (h.peekl(0xCD5E2), h.peekw(0xCDC12), h.peekw(0xCDC04), h.peekw(0xCD5E6))
    finally:
        h.close()
ts = [threading.Thread(target=one, args=("U", lu)), threading.Thread(target=one, args=("P", lp))]
[t.start() for t in ts]; [t.join() for t in ts]
U, P = res["U"], res["P"]
ub = {}
for it, k, b in U:
    ub.setdefault(k, b)
print(f"{a.snap} {a.mhz} MHz pokes {pokes[1:] if len(pokes)>1 else 'pointer only'}: base {len(U)} loop tops (ticks {U[0][1]}..{U[-1][1]}), with hover {len(P)} (ticks {P[0][1]}..{P[-1][1]})")
print(f"hover state at the end (P): HIT ${res['P_st'][0]:x}, text flag sHK {res['P_st'][1]}, icon id {res['P_st'][2]}, RES {res['P_st'][3]}; (U): HIT ${res['U_st'][0]:x}")
bad, n, ticks = {}, 0, set()
for it, k, b in P:
    u = ub.get(k)
    if u is None: continue
    n += 1; ticks.add(k)
    for g in pmtick.group(pmtick.diff_words(u, b)):
        bad.setdefault(tuple(g), []).append(it)
print(f"compared {n} loop tops over {len(ticks)} distinct world ticks")
neg = sum(1 for it, k, b in P if ub.get(k + 1) is not None and pmtick.diff_words(ub[k + 1], b))
print(f"negative control: tick k vs k+1 differs in {neg} of {sum(1 for it, k, b in P if ub.get(k + 1) is not None)} loop tops")
if not bad:
    print("IDENTICAL (everything in $0-$60000 except the pmtick MASKS and the two hook sites)"); sys.exit(0)
for (lo, hi), its in sorted(bad.items())[:40]:
    print(f"DIFF ${lo:x}-${hi:x} in {len(its)} loop tops, first iters {its[:4]}")
sys.exit(1)
