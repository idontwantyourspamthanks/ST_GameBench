#!/usr/bin/env python3
"""Cycles per call of the land score and the multiply helper, unpatched and patched (Hatari profile, 8 MHz).

    python3 percall.py [SNAP ...]

Call counts come from the cycles of each routine's first instruction (link.w = 16 cycles, the patched
site's jmp abs.l = 12, the blob's first instruction = 16 / 12), so no breakpoint disturbs the run.
"""
from __future__ import annotations

import sys
import threading
import time

import gates
import lslib


def measure(snap: str) -> list[str]:
    h = lslib.Run(snap)
    t0 = h.peekw(lslib.TURN) + 12
    h.close()
    out: dict = {}
    th = [threading.Thread(target=gates.rate, args=(snap, n, 500, t0, out, k))
          for k, n in (("unpatched", []), ("patched", gates.NAMES))]
    for t in th:
        t.start()
        time.sleep(1.0)
    for t in th:
        t.join()
    lines = []
    for k in ("unpatched", "patched"):
        rows = out[k]["profile"]
        cyc = dict(rows)
        tot = out[k]["profile_cycles"]
        b = lambda lo, hi: sum(c for a, c in rows if lo <= a < hi)   # noqa: E731
        if k == "unpatched":
            n_score = cyc.get(0x18244, 0) // 16
            n_step = cyc.get(0x181D6, 0) // 16
            n_mul = cyc.get(0x20796, 0) // 16
            mul = b(0x20796, 0x207F0)
            lines.append(f"{snap} unpatched: profile {tot} cycles; $18244 calls {n_score}, {b(0x18244, 0x18344)} cycles own code "
                         f"= {100 * b(0x18244, 0x18344) / tot:.2f}% ; $181d6 calls {n_step}, {b(0x181D6, 0x18244)} cycles "
                         f"= {100 * b(0x181D6, 0x18244) / tot:.2f}% ({b(0x181D6, 0x18244) // max(1, n_step)} per call) ; "
                         f"$20796 calls {n_mul}, {mul // max(1, n_mul)} cycles/call = {100 * mul / tot:.2f}%")
        else:
            n_score = cyc.get(0x18244, 0) // 12
            n_fast = cyc.get(0xC0028, 0) // 56            # movem.l d1-d5/a0,-(sp): 8 + 8 * 6
            n_edge = cyc.get(0xC0874, 0) // 56
            n_step = cyc.get(0x181D6, 0) // 16
            n_mul = cyc.get(0x20796, 0) // 12
            score = b(0x18244, 0x1824C) + b(0xC0000, 0xC1000)
            mul = b(0x20796, 0x2079E) + b(0xC1000, 0xC1040)
            lines.append(f"{snap} patched:   profile {tot} cycles; $18244 calls {n_score} (interior {n_fast}, edge {n_edge}), "
                         f"{score // max(1, n_score)} cycles/call = {100 * score / tot:.2f}% ; other $181d6 calls {n_step} = "
                         f"{100 * b(0x181D6, 0x18244) / tot:.2f}% ; $20796 calls {n_mul}, {mul // max(1, n_mul)} cycles/call = "
                         f"{100 * mul / tot:.2f}%")
    return lines


if __name__ == "__main__":
    for s in sys.argv[1:] or gates.SNAPS:
        for line in measure(s):
            print(line, flush=True)
