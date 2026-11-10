#!/usr/bin/env python3
"""A/B gate for the qol_ patches (qol_keys qol_keys2 qol_hover qol_hover2) against the same set without them, built on tools/pmab.py (same live sets, same frame matching by (world tick, pass kind), same cycle counter).

    python3 tools/pmqol_ab.py --ptr 150,60                     # pointer away from every village: must be IDENTICAL, cost = the hooks
    python3 tools/pmqol_ab.py --ptr 197,111 --poke 4e520:0004 --poke 4e524:0007   # on a village of get_men, item 4 (sword) with countdown 7: tooltip only
    python3 tools/pmqol_ab.py --ptr 197,111 --poke 57fd4:000e                    # Invent selected: "Invent here: ..."
    options: --snapshot get_men ... --mhz 8 16 --vbls 700 --base p4_ptr_a p4_ptr_b p4_spr (patches both runs carry besides the tick set)

Both runs carry tick_* + test_walk* (pointer driver) + --base; the patched run adds pm_tooltip.  The pointer is held at --ptr in BOTH runs
(entry 0 of the test_walk position table, $ce0c0, is poked in both).  compare() prints, for every differing frame, the number of bytes, the rows
and the 16-px columns that differ: the tooltip rectangle is rows 0-5, columns 7-19.  This script additionally fails a differing frame whose
bounding box leaves that rectangle, and prints the overall bounding box of every difference.
"""
from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pmab
from pmab import (TESTSET, TICK, WORK, at_vbl_for, compare, make_live, mean, one, snap_path, tag_for)

RECT_ROWS, RECT_COLS = (0, 5), (7, 19)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ptr", default="150,100")
    ap.add_argument("--snapshot", nargs="*", default=["get_men"])
    ap.add_argument("--mhz", nargs="*", type=int, default=[8])
    ap.add_argument("--vbls", type=int, default=700)
    ap.add_argument("--base", nargs="*", default=[])
    ap.add_argument("--st", action="store_true")
    ap.add_argument("--poke", action="append", default=[], help="ADDR:HEXBYTES applied in BOTH runs (world state, e.g. 4e520:0004)")
    a = ap.parse_args()
    x, y = (int(v) for v in a.ptr.split(","))
    poke = f"ce0c0:{x:04x}{y:04x}"
    pokes = (poke, *a.poke)
    pmab.WORK.mkdir(exist_ok=True)
    QOL = ["qol_keys", "qol_keys2", "qol_hover", "qol_hover2"]
    bnames, pnames = TICK + TESTSET + a.base + ["pm_tooltip"], TICK + TESTSET + a.base + ["pm_tooltip"] + QOL
    blive, plive = make_live(bnames), make_live(pnames, a.st)
    print(f"base set    : {' '.join(bnames)}\npatched set : {' '.join(pnames)}\npointer held at ({x},{y}); world pokes {a.poke}")
    bad = False
    for sn in a.snapshot:
        sp = snap_path(sn)
        at = at_vbl_for(sp)
        for mhz in a.mhz:
            tag = f"{sp.stem}_{mhz}_{at}_qol{x}_{y}" + "".join("_" + p.replace(":", "") for p in a.poke)
            bd = WORK / f"bt_{tag_for(bnames, False)}" / tag
            pd = WORK / f"pt_{tag_for(pnames, a.st)}" / tag
            with ThreadPoolExecutor(2) as ex:
                fb = ex.submit(one, sp, at, blive, bd, a.vbls, mhz, False, True, False, pokes)
                fp = ex.submit(one, sp, at, plive, pd, a.vbls, mhz, False, True, False, pokes)
                B, P = fb.result(), fp.result()
            ok, notes, st = compare(B, P, SimpleNamespace(neg=False))
            boxes = []
            for n in notes:
                m = re.search(r"rows (\d+)-(\d+), 16-px columns (\d+)-(\d+)", n)
                if m:
                    boxes.append(tuple(int(v) for v in m.groups()))
            r0 = min((b[0] for b in boxes), default=None)
            r1 = max((b[1] for b in boxes), default=None)
            c0 = min((b[2] for b in boxes), default=None)
            c1 = max((b[3] for b in boxes), default=None)
            inside = all(b[0] >= RECT_ROWS[0] and b[1] <= RECT_ROWS[1] and b[2] >= RECT_COLS[0] and b[3] <= RECT_COLS[1] for b in boxes)
            bw, pw = mean(B["work"]), mean(P["work"])
            pr = [(b["work"], r["work"]) for b, r in st["paired"] if b["work"] is not None and r["work"] is not None]
            bq, pq = mean([u for u, _ in pr]), mean([v for _, v in pr])
            res = "IDENTICAL" if ok else ("DIFFER (confined to the tooltip rectangle)" if inside else "DIFFER OUTSIDE THE TOOLTIP RECTANGLE")
            print(f"{sn} @{mhz} MHz ptr ({x},{y}): {res}; back frames matched {st['nback']}, shown matched {st['nshown']}, "
                  f"differing frame reports {len(boxes)}" + (f", overall bbox rows {r0}-{r1} cols {c0}-{c1}" if boxes else "")
                  + f"; work/pass {bw:.0f} -> {pw:.0f} ({pw - bw:+.0f}, {100 * (pw - bw) / bw if bw else 0:+.3f} %; n {len(B['work'])}/{len(P['work'])})"
                  f"; paired (same tick+pass kind) {bq:.0f} -> {pq:.0f} ({pq - bq:+.0f}, {100 * (pq - bq) / bq if bq else 0:+.3f} %; n {len(pr)})"
                  f"; flips {len(B['recs'])}/{len(P['recs'])}", flush=True)
            for n in notes[:6]:
                print("   ", n)
            bad |= (not ok) and not inside
            if ok is False and not boxes:
                bad = True
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
