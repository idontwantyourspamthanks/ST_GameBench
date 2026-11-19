#!/usr/bin/env python3
"""Prediction gate for qol_hover's `predict` (feature 4: "Invent here: ...").  For ~300 scenarios on settlement 0 of the get_men snapshot (posture x
resident professions x terrain height x forest distance x mine x slot x parity) the emulator itself writes the scenario into the game's variables,
runs predict (read-only replay of the chooser) and then the game's REAL invention order $5cde (patches/test_qolinv.s), and this script compares:
the item the real order stored in $c(settlement) must be the predicted one (the predicted pair in the ambiguous high-ground-near-forest case: the item
for the parity bit that was set).

    python3 tools/pmqol_inv.py [BATCH=100]
"""
from __future__ import annotations

import itertools
import struct
import sys
import time

import pmab
import pmtick
from pm import PM, SNAP

ITEM = {0: "-", 2: "pike", 4: "sword", 6: "bow", 8: "plough", 0xA: "boat", 0xC: "pot", 0xE: "catapult", 0x10: "cannon"}
CELL = 0x0B56
TX, TY = CELL & 63, CELL >> 6


def forest(kind):
    return {"near": ((TY + 5) << 6) | TX, "far": ((TY + 30) << 6) | TX, "none": 0}[kind]


def scenarios():
    out = []
    for p, F, H, D, mine in itertools.product((0, 1, 2), (0, 1, 2, 4, 6, 3), (8, 32), ("near", "far", "none"), (0, 1)):
        amb = (mine == 0 and H >= 16 and D == "near")
        for par in ((0, 1) if amb else (0,)):
            out.append(dict(p=p, F=F, H=H, D=D, mine=mine, par=par, slot=1))
            if mine == 0 and F & 1:
                out.append(dict(p=p, F=F, H=H, D=D, mine=mine, par=par, slot=0))
    return out


def expected(sc, W):
    A, B = (W >> 6) & 31, W & 31
    if W & 0x8000 == 0:
        return None
    if A == 0:
        return {0}
    if B == 0:
        return {A}
    return {A} if sc["par"] == 0 else {B}


def run_batch(batch, tag):
    tbl = b"".join(struct.pack(">8H", sc["p"], sc["F"], sc["H"], forest(sc["D"]), sc["mine"], sc["par"], sc["slot"], 0) for sc in batch)
    f = pmab.WORK / f"inv_{tag}.bin"
    f.parent.mkdir(exist_ok=True)
    f.write_bytes(tbl)
    live = pmab.make_live(["pm_tooltip", "qol_hover", "qol_hover2", "test_qolinv"])
    h = PM(snapshot=str(SNAP / "get_men.sav"))
    try:
        time.sleep(1.5)
        h.set_cpuclock(16)
        pmtick.at_flip(h, pmab.apply_cmds(live) + [f"loadbin {f} $e0000", f"w $cec02 ${len(batch) >> 8:02x} ${len(batch) & 255:02x}", "w $cec00 $00 $01"])
        t = time.time()
        while h.peekw(0xCEC04) != 1:
            if time.time() - t > 120:
                raise TimeoutError("scenario loop did not finish")
            time.sleep(0.5)
        res = h.ram(0xE8000, 8 * len(batch))
    finally:
        h.close()
    return [struct.unpack(">HH", res[8 * i:8 * i + 4]) for i in range(len(batch))]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    sc = scenarios()
    print(f"{len(sc)} scenarios")
    bad, amb, kinds = 0, 0, {}
    for b0 in range(0, len(sc), n):
        batch = sc[b0:b0 + n]
        for s, (W, c) in zip(batch, run_batch(batch, b0)):
            exp = expected(s, W)
            A, B = (W >> 6) & 31, W & 31
            amb += (B != 0)
            kinds[(A, B)] = kinds.get((A, B), 0) + 1
            if exp is None or c not in exp:
                bad += 1
                print(f"MISMATCH {s}: predict W=${W:04x} (A {ITEM.get(A)}, B {ITEM.get(B)}), the game made {ITEM.get(c, c)}")
    print(f"{len(sc)} scenarios, {amb} ambiguous (two answers), {bad} mismatches; predicted (A, B) pairs seen: "
          + ", ".join(f"{ITEM[a]}/{ITEM[b]}:{k}" for (a, b), k in sorted(kinds.items())))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
