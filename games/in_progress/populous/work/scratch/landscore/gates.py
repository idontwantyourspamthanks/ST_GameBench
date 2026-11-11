#!/usr/bin/env python3
"""Gates for patches/pop_land_*.s (test scaffolding; the patches are applied live to snapshots).

    python3 gates.py trace  [SNAP ...]      # step 1: log the real $18244, turn-to-turn statistics
    python3 gates.py a      [SNAP ...]      # gate (a): shadow run, new vs original on every call
    python3 gates.py b      [SNAP ...]      # gate (b): per-turn hash of all game data + full-RAM checkpoints
    python3 gates.py bctl   [SNAP ...]      # the same with two unpatched runs (determinism control)
    python3 gates.py bfx    [SNAP ...]      # gate (b) with earthquakes, volcanoes and a flood issued at fixed turns
    python3 gates.py a-mutant SNAP          # negative control: a broken blob must fail gate (a)
    python3 gates.py c      [SNAP ...]      # gate (c): turns per second and cycles per turn at 8 MHz

Everything is applied when the main loop reaches $b800 on a chosen turn (lslib.Run.at_turn), so runs
of the same snapshot are comparable turn by turn. No input is sent after the harness start-up.
"""
from __future__ import annotations

import re
import struct
import sys
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

import lslib
from lslib import Run, load_patch, parse_source

HERE = Path(__file__).resolve().parent
GAME = lslib.GAME
DUMPS = GAME / "work" / "dumps"
NAMES = ["pop_land_score", "pop_land_mul"]
SNAPS = ["busy_castles", "busy_quake_volcano"]
# Hashed every turn: all game data + bss ($21100-$3d7ff) and the loaded data above the stack ($3f600-$4f4ff),
# except $24990-$249a3 = the sample player's state (repeat count, priority, pointer, length, position, playing
# flag), which the timer-A interrupt $1717e advances and clears in real time (landscore.md, gate b).
HASH_RANGES = [(0x21100, 0x24990), (0x249A4, 0x3D800), (0x3F600, 0x4F500)]
JMP = "$4e $f9 $00 $0b $22 ${:02x} $4e $71"                 # jmp $b22xx.l ; nop
# gate (b) with terrain effects: the game's own commands for player 0, written at fixed turns in BOTH runs
# (manna first; `w $21e4a 03 2c 20` = earthquake at the view, 06 = volcano, 0e 00 04 = flood: baseline.md)
MANNA = "w $3b270 $00 $04 $93 $e0"
EFFECTS = [(40, [MANNA, "w $21e4a $03 $2c $20"]), (110, [MANNA, "w $21e4a $06 $2c $20"]),
           (200, [MANNA, "w $21e4a $03 $2c $20"]), (260, [MANNA, "w $21e4a $06 $2c $20"]),
           (400, [MANNA, "w $21e4a $0e $00 $04"])]
MUTANT: list[str] = []                                      # negative control: debugger writes that break a blob


def stub(name: str, extra: str = "") -> dict[int, bytes]:
    return parse_source((HERE / f"{name}.s").read_text() + extra)["segs"]


def patches(names=NAMES) -> list[dict]:
    return [load_patch(n) for n in names]


# ---- step 1: the real routine, traced -----------------------------------------------
def trace(snap: str, turns: int = 85) -> dict:
    h = Run(snap)
    try:
        t0 = h.peekw(lslib.TURN) + 6
        out = DUMPS / f"trace_{snap}.bin"
        tv = h.R / "tv.bin"
        cmds = h.load_cmds(stub("trace"), "tr") + ["w $b2000 $00 $05 $f0 $00",
                                                    "w $18244 $4e $f9 $00 $0b $21 $00 $4e $71"]
        h.at_turn(t0, cmds)
        h.at_turn(t0 + turns, [f"savebin {tv} $b2000 $10", f"savebin {h.R}/t.bin $5f000 $18f00"])
        h.fast()
        h.wait_file(h.R / "t.bin", size=0x18F00)
        h.fast(False)
        ptr, n, dropped = struct.unpack(">3I", tv.read_bytes()[:12])
        raw = (h.R / "t.bin").read_bytes()[:14 * n]
        out.write_bytes(raw)
    finally:
        h.close()
    recs = [struct.unpack_from(">IHHHBBBx", raw, 14 * i) for i in range(n)]   # ret, turn, cell, d0, owner, cnt, flat
    sites = Counter(r[0] for r in recs)
    full = sorted({r[1] for r in recs})[1:-1]                    # whole turns only
    by_turn: dict = defaultdict(dict)
    dup = 0
    for ret, turn, cell, d0, owner, cnt, flat in recs:
        if ret == 0xE29A and turn in full:                       # the peep loop: once per building per turn
            if (owner, cell) in by_turn[turn]:
                dup += 1
            by_turn[turn][(owner, cell)] = (d0, cnt, flat)
    evals = same = same_d0 = first = 0
    for t in full:
        for k, v in by_turn[t].items():
            p = by_turn.get(t - 1, {}).get(k) if t - 1 in full else None
            if p is None:
                first += 1
                continue
            evals += 1
            same += v == p
            same_d0 += v[0] == p[0]
    return {"snap": snap, "first_turn": t0, "records": n, "dropped": dropped, "whole_turns": len(full),
            "calls_by_return_address": {f"${k:x}": v for k, v in sorted(sites.items())},
            "building_turns_with_previous": evals, "same_3_outputs_as_previous_turn": same,
            "same_d0_as_previous_turn": same_d0, "no_previous_turn": first, "duplicate_keys": dup,
            "calls_per_turn": round(n / max(1, len(full) + 1), 1)}


# ---- gate (a) ---------------------------------------------------------------------------
def gate_a(snap: str, turns: int = 150) -> dict:
    h = Run(snap)
    try:
        t0 = h.peekw(lslib.TURN) + 6
        cmds = []
        for p in patches():
            cmds += h.load_cmds(p["blobs"], p["name"][-5:])
        cmds += MUTANT + h.load_cmds({0xB2000: bytes(0x200)}, "z") + h.load_cmds(stub("shadow"), "sh")
        cmds += ["w $18244 " + JMP.format(0x00), "w $20796 " + JMP.format(0x04)]
        h.at_turn(t0, cmds)
        sv, lg = h.R / "sv.bin", h.R / "lg.bin"
        h.at_turn(t0 + turns, [f"savebin {lg} $60000 $1900", f"savebin {sv} $b2000 $40"])
        h.fast()
        h.wait_file(sv, size=0x40)
        h.fast(False)
        v = struct.unpack(">7IH2xII", sv.read_bytes()[:40])
        log = lg.read_bytes()
        res = {"snap": snap, "turns": f"{t0}..{t0 + turns - 1}",
               "score_calls": v[0], "score_mismatch": v[1], "score_reg_faults": v[2],
               "score_unrolled": v[8], "score_edge": v[9],
               "mul_calls": v[3], "mul_mismatch": v[4], "mul_reg_faults": v[5], "mul_fast_path": v[6],
               "logged": v[7]}
        res["first_records"] = [log[32 * i:32 * i + 32].hex() for i in range(min(v[7], 6))]
        return res
    finally:
        h.close()


# ---- gate (b) ---------------------------------------------------------------------------
def run_b(snap: str, patched: bool, turns: int, t0: int, tag: str, out: dict, checkpoints=(1, 0.5, 1.0),
          effects=()) -> None:
    h = Run(snap)
    try:
        now = h.peekw(lslib.TURN)
        if now + 3 > t0:
            raise RuntimeError(f"turn {now} too close to {t0}")
        ps = patches()
        cmds = []
        for p in ps:                                              # blobs in BOTH runs: only the sites differ
            cmds += h.load_cmds(p["blobs"], p["name"][-5:])
        if patched:
            cmds += MUTANT
        rng = "".join(f"        dc.l    ${a:x},{(b - a) // 4}\n" for a, b in HASH_RANGES) + "        dc.l    0\n"
        cmds += h.load_cmds(stub("cksum", rng), "ck")
        cmds += ["w $b2000 $00 $06 $00 $00", "w $b808 $00 $0b $21 $00"]
        if patched:
            cmds += [f"w ${p['site']:x} " + " ".join(f"${x:02x}" for x in p["new"]) for p in ps]
        h.at_turn(t0, cmds)
        for dt, ec in effects:
            h.at_turn(t0 + dt, ec)
        cps = []
        for c in checkpoints:
            t = t0 + (c if isinstance(c, int) else int(turns * c))
            f = DUMPS / f"gb_{snap}_{tag}_{t}.bin"
            f.unlink(missing_ok=True)
            h.at_turn(t, [f"savebin {h.R}/c{t}.bin 0 $100000", "r"])
            cps.append((t, f))
        ck = h.R / "ck.bin"
        h.at_turn(t0 + turns + 1, [f"savebin {ck} $60000 ${12 * (turns + 2):x}"])
        h.fast()
        h.wait_file(ck, size=12 * (turns + 2), timeout=1500)
        h.fast(False)
        peeps = []
        for t, f in cps:
            d = (h.R / f"c{t}.bin").read_bytes()
            f.write_bytes(d)
            (h.R / f"c{t}.bin").unlink()
            used = sum(1 for i in range(208) if d[0x3B2B6 + 22 * i + 4:0x3B2B6 + 22 * i + 6] != b"\0\0")
            rock = d[lslib.MAP_BLK:lslib.MAP_BLK + 4096].count(0x2F)
            water = d[lslib.MAP_BLK:lslib.MAP_BLK + 4096].count(0)
            peeps.append((t, used, rock, water))
        raw = ck.read_bytes()
        sps = [int(x, 16) for x in re.findall(r"A7 ([0-9A-F]{8})", h._logtext())]
        out[tag] = {"recs": [struct.unpack_from(">HHII", raw, 12 * i) for i in range(turns + 1)],
                    "cps": cps, "vbl_end": h.vbl(), "sp": sps, "peeps": peeps}
    finally:
        h.close()


def diff_ranges(a: bytes, b: bytes, gap: int = 16) -> list[tuple[int, int, int]]:
    out = []
    i, n = 0, len(a)
    while i < n:
        if a[i] != b[i]:
            j = last = i
            cnt = 0
            while j < n and j - last <= gap:
                if a[j] != b[j]:
                    last = j
                    cnt += 1
                j += 1
            out.append((i, last + 1, cnt))
            i = last + 1
        else:
            i += 1
    return out


def explain(lo: int, hi: int, sites, sp: int) -> str:
    """Why a byte range may differ between the patched and the unpatched run at the same turn."""
    for p in sites:
        if p["site"] <= lo and hi <= p["site"] + len(p["orig"]):
            return "site " + p["name"]
    for a, b, why in ((0x462, 0x46A, "TOS _vbclock/_frclock"), (0x4BA, 0x4BE, "TOS _hz_200"),
                      (0x16D2A, 0x16D2E, "game VBL counter (addq.l #1 at $16dde)"),
                      (0x2005E, 0x2005F, "IKBD packet byte counter (ACIA handler $1fff2)"),
                      (0x24990, 0x249A4, "sample player state (timer-A handler $1717e)"),
                      (0x8F0, 0x93A, "BIOS register save area below _savptr=$93a"),
                      (0x60000, 0x62000, "test log (hash records of the excluded turns)")):
        if a <= lo and hi <= b:
            return why
    if 0x3F000 <= lo and hi <= sp:
        return f"dead stack below SP=${sp:x}"
    if hi <= 0xA84E:
        return "TOS RAM below _membot $a84e"
    return "UNEXPLAINED"


def gate_b(snap: str, turns: int = 520, control: bool = False, effects=()) -> dict:
    h = Run(snap)
    t0 = h.peekw(lslib.TURN) + 12
    h.close()
    out: dict = {}
    tags = [("U", False), ("U2", False)] if control else [("U", False), ("P", True)]
    th = [threading.Thread(target=run_b, args=(snap, pat, turns, t0, tag, out, (1, 0.5, 1.0), effects)) for tag, pat in tags]
    for t in th:
        t.start()
        time.sleep(1.0)
    for t in th:
        t.join()
    a, b = out[tags[0][0]], out[tags[1][0]]
    same = sum(x == y for x, y in zip(a["recs"], b["recs"]))
    firstbad = next((x[0] for x, y in zip(a["recs"], b["recs"]) if x != y), None)
    peeps = [x["peeps"] for x in (a, b)]
    res = {"snap": snap, "pair": f"{tags[0][0]} vs {tags[1][0]}", "effects_at": [t0 + d for d, _ in effects],
           "peep_slots_at_checkpoints": peeps, "turns": f"{a['recs'][0][0]}..{a['recs'][-1][0]}",
           "turn_records": len(a["recs"]), "identical_records": same, "first_different_turn": firstbad,
           "hash_ranges": [f"${x:x}-${y - 1:x}" for x, y in HASH_RANGES],
           "rng_seed_first_last": (f"${a['recs'][0][1]:04x}", f"${a['recs'][-1][1]:04x}"),
           "vbl_at_end": (a["vbl_end"], b["vbl_end"]), "sp_at_checkpoints": sorted({f"${x:x}" for x in a["sp"] + b["sp"]}),
           "checkpoints": []}
    ps = patches()
    sp = min(a["sp"] + b["sp"])
    for (t, fa), (_, fb) in zip(a["cps"], b["cps"]):
        da, db = fa.read_bytes(), fb.read_bytes()
        d = diff_ranges(da, db)
        res["checkpoints"].append({"turn": t, "differing_bytes": sum(x[2] for x in d),
                                   "unexplained": sum(explain(x, y, ps, sp) == "UNEXPLAINED" for x, y, c in d),
                                   "ranges": [f"${x:x}-${y - 1:x} ({c}): {explain(x, y, ps, sp)}" for x, y, c in d]})
        fa.unlink()
        fb.unlink()
    return res


# ---- gate (c) ---------------------------------------------------------------------------
def rate(snap: str, names: list[str], vbls: int, t0: int, out: dict, key: str) -> None:
    h = Run(snap)
    try:
        cmds = h.patch_cmds(patches(names)) if names else ["m $18244 8"]
        done = h.R / "applied.bin"
        h.at_turn(t0, cmds + [f"savebin {done} $18244 8"])
        h.wait_file(done, size=8)
        time.sleep(1.0)
        r = h.world_rate(lslib.TURN, vbls)
        rows = h.profile(1000)
        tot = sum(c for _, c in rows)
        tA = h.peekw(lslib.TURN)
        out[key] = {"site_18244": done.read_bytes().hex(), **r, "turns_per_sec": round(r["units_per_sec"], 3),
                    "profile": rows, "profile_cycles": tot, "turn_after": tA}
    finally:
        h.close()


def bucket(rows, lo, hi):
    return sum(c for a, c in rows if lo <= a < hi)


def gate_c(snap: str, vbls: int = 2000) -> list[dict]:
    h = Run(snap)
    t0 = h.peekw(lslib.TURN) + 12
    h.close()
    sets = [("unpatched", []), ("pop_land_score", ["pop_land_score"]), ("pop_land_mul", ["pop_land_mul"]),
            ("both", NAMES)]
    out: dict = {}
    for i in range(0, len(sets), 2):
        th = [threading.Thread(target=rate, args=(snap, n, vbls, t0, out, k)) for k, n in sets[i:i + 2]]
        for t in th:
            t.start()
            time.sleep(1.0)
        for t in th:
            t.join()
    res = []
    for k, _ in sets:
        r = out[k]
        rows = r["profile"]
        tot = r["profile_cycles"]
        res.append({"snap": snap, "set": k, "site_18244": r["site_18244"], "vbls": r["vbls"], "flips": r["flips"],
                    "fps": r["fps"], "turns_per_sec": r["turns_per_sec"],
                    "pct_181d6": round(100 * bucket(rows, 0x181D6, 0x18244) / tot, 2),
                    "pct_18244": round(100 * bucket(rows, 0x18244, 0x18344) / tot, 2),
                    "pct_blob_c0000": round(100 * bucket(rows, 0xC0000, 0xC1000) / tot, 2),
                    "pct_20796": round(100 * bucket(rows, 0x20796, 0x207F0) / tot, 2),
                    "pct_blob_c1000": round(100 * bucket(rows, 0xC1000, 0xC1100) / tot, 2)})
    return res


def main() -> int:
    what = sys.argv[1]
    snaps = sys.argv[2:] or SNAPS
    for s in snaps:
        if what == "trace":
            print(trace(s), flush=True)
        elif what == "a":
            print(gate_a(s), flush=True)
        elif what == "a-mutant":                 # the gate must FAIL: first score 65 -> 64; mulu by the wrong word
            MUTANT[:] = ["w $c0055 $40", "w $c1017 $0c"]
            print(gate_a(s, 30), flush=True)
        elif what in ("b", "bctl", "bfx"):
            r = gate_b(s, control=what == "bctl", effects=EFFECTS if what == "bfx" else ())
            cps = r.pop("checkpoints")
            print(r)
            for c in cps:
                print(f"  checkpoint turn {c['turn']}: {c['differing_bytes']} differing bytes, {c['unexplained']} unexplained ranges")
                for x in c["ranges"]:
                    print("    " + x)
            sys.stdout.flush()
        elif what == "c":
            for r in gate_c(s):
                print(r, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
