#!/usr/bin/env python3
"""World-state equality gate for pm_tooltip (same method as tools/pmtick.py `ab`, which this reuses: full RAM $0-$60000 at every loop top,
compared per world tick, same masks).  Both runs carry the tick_* set; the second one also carries pm_tooltip.  No input is given, so the
pointer stays where the snapshot left it ((229,173) in get_men = on the Supply Food icon: the tooltip is up in the patched run).

    python3 tools/pmtt_state.py [SNAP=get_men] [MHZ=8] [VBLS=700]
"""
from __future__ import annotations

import sys
import threading
import time

import pmab
import pmtick
from pm import PM, SNAP

pmtick.SITE_MASKS.append((0x130A4, 0x130AA))        # the pm_tooltip site itself


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else "get_men"
    mhz = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    vbls = int(sys.argv[3]) if len(sys.argv) > 3 else 700
    lu = pmab.make_live(pmab.TICK)
    lp = pmab.make_live(pmab.TICK + ["pm_tooltip"])
    res = {}

    def one(name, lv):
        h = PM(snapshot=str(SNAP / f"{snap}.sav"))
        try:
            time.sleep(1.5)
            res[name] = pmtick.log_passes(h, lv, mhz, vbls, name)
            if name == "P":
                res["state"] = (h.peekw(0xCDC04), h.peekw(0xCDC06))
        finally:
            h.close()

    ts = [threading.Thread(target=one, args=("U", lu)), threading.Thread(target=one, args=("P", lp))]
    [t.start() for t in ts]
    [t.join() for t in ts]
    U, P = res["U"], res["P"]
    ub = {}
    for it, k, b in U:
        ub.setdefault(k, b)
    print(f"{snap} {mhz} MHz: tick-only run {len(U)} loop tops (ticks {U[0][1]}..{U[-1][1]}), with pm_tooltip {len(P)} (ticks {P[0][1]}..{P[-1][1]}); "
          f"tooltip state at the end: id {res['state'][0]} key {res['state'][1]} (0 = no tooltip up)")
    bad, n, ticks = {}, 0, set()
    for it, k, b in P:
        u = ub.get(k)
        if u is None:
            continue
        n += 1
        ticks.add(k)
        for g in pmtick.group(pmtick.diff_words(u, b)):
            bad.setdefault(tuple(g), []).append(it)
    print(f"compared {n} loop tops over {len(ticks)} distinct world ticks")
    neg = sum(1 for it, k, b in P if ub.get(k + 1) is not None and pmtick.diff_words(ub[k + 1], b))
    print(f"negative control: tick k vs tick k+1 differs in {neg} of {sum(1 for it, k, b in P if ub.get(k + 1) is not None)} loop tops")
    mv = sum(1 for i in range(512) if P[0][2][0x51B66 + i * 50 + 8:0x51B66 + i * 50 + 12] != P[-1][2][0x51B66 + i * 50 + 8:0x51B66 + i * 50 + 12])
    print(f"men records whose x/z changed first->last loop top: {mv}")
    if not bad:
        print("IDENTICAL (everything in $0-$60000 except the pmtick MASKS)")
        return 0
    for (lo, hi), its in sorted(bad.items())[:40]:
        print(f"DIFF ${lo:x}-${hi:x} in {len(its)} loop tops, first iters {its[:4]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
