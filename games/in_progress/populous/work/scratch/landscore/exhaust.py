#!/usr/bin/env python3
"""Exhaustive check of the land score: original $18244 vs patches/pop_land_score.s vs the Python model.

    python3 exhaust.py                 # the standard set (both snapshots, real and fuzzed maps)

For each run: restore a snapshot, stop at the main loop's `jsr $db8a` on a chosen turn, save
the whole RAM, (optionally overwrite map_blk / map_bk2 with random tiles), load the blob at
$c0000 WITHOUT hooking it, and run exhaust.s, which calls the original and the new routine for
every input of the table and compares d0.l, CCR, $3b040, $37ef4 and all registers inside the
emulator. The Python model is then compared with the original's records on the saved RAM.
"""
from __future__ import annotations

import random
import struct
import sys
import time
from pathlib import Path

import lslib
from lslib import MAP_BLK, MAP_BK2, Run, load_patch, model_18244, parse_source

HERE = Path(__file__).resolve().parent
STD = [(0, 0, 4096), (1, 0, 4096)]                               # every cell, both players
EXT = [(o, c, n) for o in (0, 1, 2, 0x10, 0xE1, 0xF0, 0xFF)      # garbage arguments
       for c, n in ((-140 & 0xFFFF, 140), (4096, 145))] + [(2, 0, 800), (0xE1, 1900, 400), (0x10, 3000, 400), (0xF0, 100, 300)]
TILES = [0, 0, 0x0F, 0x0F, 0x0F, 0x0F, 0x1F, 0x1F, 0x20, 0x20, 0x2F, 0x01, 0x0E, 0x10, 0x1E, 0x21, 0x30, 0x35, 0x42, 0xFF]
OBJS = [0] * 14 + [0x20, 0x21, 0x28, 0x29, 0x2A, 0x2A, 0x2A, 0x2B, 0x2C, 0x2D, 0x32, 0x34, 0x7F, 0x80, 0xA9, 0xFF]


def fuzz_maps(seed: int, dense: int) -> tuple[bytes, bytes]:
    r = random.Random(seed)
    if dense == 3:   # rock and water round flat cells: negative and sub-35 scores
        blk = bytes(r.choice((0x2F,) * 7 + (0, 0x0F, 0x0F, 0x1F, 0x20, 0x05)) for _ in range(4096))
        bk2 = bytearray(4096)
        for _ in range(60):
            bk2[r.randrange(4096)] = r.choice((0x2A, 0x21, 0x32))
        return blk, bytes(bk2)
    if dense:        # mostly good land, so scans run long and reach the tails (dense = 2: very few defects)
        pb, po, nc = (0.12, 0.06, 300) if dense == 1 else (0.02, 0.008, 120)
        blk = bytes(r.choice(TILES) if r.random() < pb else r.choice((0x0F, 0x1F, 0x20)) for _ in range(4096))
        bk2 = bytes(r.choice(OBJS[14:]) if r.random() < po else 0 for _ in range(4096))
        bk2 = bytearray(bk2)
        for _ in range(nc):                                      # castle centres with pieces round them
            c = r.randrange(4096)
            bk2[c] = 0x2A
            perfect = r.random() < 0.5
            for o in (-65, -64, -63, -1, 1, 63, 64, 65):
                if 0 <= c + o < 4096 and (perfect or r.random() < 0.8):
                    bk2[c + o] = r.choice((0x29, 0x2B, 0x2C) if perfect else (0x29, 0x2A, 0x2B, 0x2C, 0x2C, 0x28, 0x2D, 0))
        return blk, bytes(bk2)
    return bytes(r.choice(TILES) for _ in range(4096)), bytes(r.choice(OBJS) for _ in range(4096))


def run(snap: str, table, ccrin: int, fuzz: tuple[int, int] | None = None, turns_ahead: int = 6) -> dict:
    h = Run(snap)
    try:
        t0 = h.peekw(lslib.TURN) + turns_ahead
        ramf = h.R / "ram.bin"
        patch = load_patch("pop_land_score")
        src = (HERE / "exhaust.s").read_text().replace("CCRIN", f"${ccrin:02x}")
        src += "".join(f"        dc.w    ${o:x},${c & 0xFFFF:x},{n}\n" for o, c, n in table) + "        dc.w    $ffff\n"
        stub = parse_source(src)["segs"]
        cmds = [f"savebin {ramf} 0 $100000"]
        maps = None
        if fuzz:
            maps = fuzz_maps(*fuzz)
            cmds += h.load_cmds({MAP_BLK: maps[0], MAP_BK2: maps[1]}, "fz")
        cmds += h.load_cmds(patch["blobs"], "bl") + h.load_cmds(stub, "st")
        cmds.append("w $b808 $00 $0b $21 $00")                    # jsr $db8a -> jsr $b2100, never returns
        h.at_turn(t0, cmds)
        h.fast()
        n = sum(t[2] for t in table)
        deadline = time.time() + 600
        while time.time() < deadline:
            time.sleep(1)
            if "44 4f 4e 45" in h.debug("m $b200c 4", 0.4).lower():
                break
        else:
            raise TimeoutError(h._logtext()[-600:])
        h.fast(False)
        ro, rn, st = h.R / "o.bin", h.R / "n.bin", h.R / "s.bin"
        h.debug(f"savebin {ro} $60000 ${6 * n:x}", 1.0)
        h.debug(f"savebin {rn} $6c000 ${6 * n:x}", 1.0)
        h.debug(f"savebin {st} $b2000 $10", 1.0)
        ram = bytearray(ramf.read_bytes())
        if maps:
            ram[MAP_BLK:MAP_BLK + 4096] = maps[0]
            ram[MAP_BK2:MAP_BK2 + 4096] = maps[1]
        total, mism, regf = struct.unpack(">3I", st.read_bytes()[:12])
        o, nw = ro.read_bytes(), rn.read_bytes()
        model_bad = 0
        py_pair_bad = 0
        hist: dict = {}
        paths: set = set()
        i = 0
        for own, c0, cnt in table:
            for k in range(cnt):
                cell = (c0 + k) & 0xFFFF
                d0, cn, fl, ccr, flg = struct.unpack_from(">HBBBB", o, 6 * i)
                if o[6 * i:6 * i + 4] != nw[6 * i:6 * i + 4] or (o[6 * i + 4] ^ nw[6 * i + 4]) & 0x1F:
                    py_pair_bad += 1
                # the model reads RAM as the routine does: garbage cells index outside the maps, as in the real one
                m = model_18244(ram, own, cell)
                if (m[0], m[1] & 0xFF, m[2] & 0xFF) != (d0, cn, fl):
                    model_bad += 1
                hist[d0] = hist.get(d0, 0) + 1
                if own <= 1 and cell < 4096:
                    paths.add(lslib.model_path(ram, own, cell))
                i += 1
        return {"snap": snap, "turn": t0, "fuzz": fuzz, "ccr_in": ccrin, "inputs": total, "expected": n,
                "emu_mismatch": mism, "reg_faults": regf, "py_orig_vs_new": py_pair_bad,
                "model_vs_orig": model_bad, "nonzero": n - hist.get(0, 0), "castle": hist.get(0xBEA, 0), "paths": paths}
    finally:
        h.close()


def main() -> int:
    jobs = [("busy_castles", STD, 0x00, None), ("busy_quake_volcano", STD, 0x1F, None),
            ("busy_castles", EXT, 0x1F, None), ("busy_quake_volcano", EXT, 0x00, (7, 0)),
            ("busy_castles", STD, 0x1F, (1, 0)), ("busy_castles", STD, 0x00, (2, 1)),
            ("busy_quake_volcano", STD, 0x10, (3, 1)), ("busy_quake_volcano", STD, 0x0F, (4, 0)),
            ("genesis_start", STD, 0x00, None),
            ("busy_castles", STD, 0x1F, (5, 2)), ("busy_quake_volcano", STD, 0x00, (6, 2)),
            ("busy_castles", STD, 0x15, (8, 2)), ("busy_quake_volcano", STD, 0x0A, (9, 1)),
            ("busy_castles", STD, 0x00, (10, 3)), ("busy_quake_volcano", STD, 0x1F, (11, 3))]
    bad = 0
    allp: set = set()
    for snap, tab, ccr, fz in jobs:
        r = run(snap, tab, ccr, fz)
        allp |= r.pop("paths")
        print(r, flush=True)
        bad += r["emu_mismatch"] + r["reg_faults"] + r["py_orig_vs_new"] + r["model_vs_orig"] + (r["inputs"] != r["expected"])
    want = lslib.all_paths()
    print(f"paths covered {len(allp & want)} of {len(want)}; missing {sorted(want - allp)}")
    print("RESULT", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
