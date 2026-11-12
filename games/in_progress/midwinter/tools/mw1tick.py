#!/usr/bin/env python3
"""Gates for the fixed-tick patches (tick_head = option A; p3b_head + p3b_hook/hud/logic/msg/units = partial B).

    python3 tools/mw1tick.py ab  --only p3b_head p3b_hook p3b_hud p3b_logic p3b_msg p3b_units \
            [--snapshot 1mb_ski_walk 1mb_ski_turn] [--mhz 8] [--vbls 700] [--poke 'w $24faa $01 $90']
    python3 tools/mw1tick.py fps --only ... [--snapshot ...] [--mhz 8 16] [--vbls 1000]
    python3 tools/mw1tick.py rate --only ... [--snapshot 1mb_ski_walk] [--mhz 8 16] [--hz 50 60] [--vbls 1500]

ab   Group-end equality. Restores each snapshot twice (unpatched, and patched live at the first flip), logs at
     the loop top ($14ac4, after every pass) the sim state words, and compares every TICK END of the patched run
     (D+4 PH in {0,5}: the end of an A pass or of PH 5 of a B group) with the same tick of the unpatched
     per-frame game (which is option A's step sequence by construction). Ticks are paired by order after the
     first match of (x, z, speed, heading, clock, $15118). Compared (REGIONS): position/cell/heading/clock/
     speed/state-machine words, objects, map units, tilt, timers and the PRNG state $d5d8. Masked: $12c88-$12c8f (scene-build scratch, rewritten by every
     render). Exit status 1 on any difference.
fps  Presented frames ($ff8201 changes) per `--vbls` VBL, unpatched vs patched, at each --mhz.
rate World ticks per EMULATED second at each --mhz and display refresh --hz (50: as the snapshot; 60: `w $ff820a $00` at apply time,
     Hatari then runs 60 frames/s of 133 k cycles at 8 MHz). Tick rows are the loop tops with PH in {0,5}; rate = (n-1) ticks over the VBLs
     between the first and the last row / hz, so no window quantisation. `--only` empty-set is not allowed: use the patches under test.
cold Cold boot of a built game dir (`mw1patch.py build ... --out DIR`) to Skiing with `boot_to_game('M')`, reports the MWPO
     marker at $B2FF8, the head bytes at $14e00, then a walk logged at 8 and at 16 MHz (tick rows: PH in {0,5}):
         python3 tools/mw1tick.py cold --game build/x --mem 1024 --machine ste --tos 1.62
         python3 tools/mw1tick.py cold --game build/x --mem 4096 --machine megaste --tos 2.06

Needs `patches/*.s` built by mw1patch.py live (written to build/tick/live.{img,json}).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from mw1 import MW1  # noqa: E402

SNAP = GAME / "work" / "snapshots"
PH_ADDR = 0xB3704            # D+4 of the p3b_head / tick_head data block ($B3700)
REGIONS = [(0x12C5A, 0x48), (0x130D0, 16), (0x13500, 0x60), (0x152A8, 8), (0x15110, 16), (0x171F0, 0x30),
           (0x1CD7E, 0xB0), (0x2C45A, 2), (0x15118, 2), (0x2C422, 2), (0x12FDE, 4), (0x14320, 16),
           (0x14EE0, 8), (0x13B30, 0x40), (0x24FAA, 8), (0x1F0D6, 4), (0x159A0, 4), (0x12F3C, 4),
           (0x12F5A, 2), (0x14DFC, 4), (0xD5D8, 4), (0x2BAE0, 0x40), (0x2D47E, 0x290)]
MASK = set(range(0x12C88, 0x12C90))
W = lambda b, o=0: int.from_bytes(b[o:o + 2], "big")
L = lambda b, o=0: int.from_bytes(b[o:o + 4], "big")


def live_image(only: list[str]) -> str:
    out = GAME / "build" / "tick" / ("live_" + "_".join(sorted(only))[:60].replace("/", ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(HERE / "mw1patch.py"), "live", "--only", *only,
                    "--out", str(out.relative_to(GAME))], check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    return str(out)


def apply_cmds(live: str) -> list[str]:
    spec = json.loads(Path(live + ".json").read_text())
    c = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
    c += [f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])) for s in spec["sites"]]
    return c


def wait_gone(h, start: int, timeout: float = 600):
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("breakpoint never fired")
        time.sleep(0.4)
    time.sleep(0.4)


def at_flip(h, cmds: list[str]):
    """Run debugger `cmds` at the next call of the flip routine (never apply code while the CPU runs)."""
    f = h.R / "atflip.txt"
    f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $bd9a :trace :once :file {f}")
    wait_gone(h, start, 120)


def log_ticks(h, live: str | None, mhz: int, vbls: int, poke: list[str]) -> list[tuple[int, dict]]:
    if mhz != 8:
        h.set_cpuclock(mhz)
    lf = h.R / "looplog.txt"
    lf.write_text("e CycleCounter\ne VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in REGIONS) + f"m ${PH_ADDR:x} 2\n")
    c = list(poke) + (apply_cmds(live) if live else []) + [f"b pc = $14ac4 :trace :file {lf}"]
    at_flip(h, c)
    s2 = len(h._logtext())
    v0 = h.vbl()
    h.cmd(f"hatari-debug b VBL > {v0 + vbls} :trace :once")
    wait_gone(h, s2)
    out = h._logtext()[s2:]
    h.debug("b all", 0.3)
    rows = []
    for blk in out.split("Reading debugger commands")[1:]:
        v = re.search(r"> e VBL\n= .*?#(\d+) \(dec\)", blk)   # (VBL is the LAST `e` of the file: harness h.vbl() takes the last (dec) in the log)
        if not v:
            continue
        mem = {}
        for m in re.finditer(r"^> m \$([0-9a-f]+) (\d+)\n((?:[0-9A-F]{8}: .*\n?)+)", blk, re.M | re.I):
            bs = bytearray()
            for ln in m.group(3).splitlines():
                mm = re.match(r"[0-9A-Fa-f]{8}:\s(.*)", ln)
                if mm:
                    bs += bytes(int(x, 16) for x in mm.group(1).split("  ")[0].split())
            mem[int(m.group(1), 16)] = bytes(bs[:int(m.group(2))])
        cyc = re.search(r"> e CycleCounter\n= .*?\$([0-9a-fA-F]+) \(hex\)", blk)
        if cyc:
            mem[-1] = int(cyc.group(1), 16)          # CPU cycle counter at this stop (proves the refresh: 8 MHz / hz per VBL)
        if PH_ADDR in mem and 0x12C5A in mem:
            rows.append((int(v.group(1)), mem))
    return rows


def key(m) -> bytes:
    # x z | speed heading | game clock minute | $15118 (passes to the next game minute, 21 per minute): pins the tick
    # even when the player stands still (x, z, heading constant)
    return m[0x12C5A][6:14] + m[0x15110][0:8] + m[0x2C45A] + m[0x15118]


def one(snap: str, live: str | None, mhz: int, vbls: int, poke: list[str]):
    h = MW1(snapshot=str(SNAP / f"{snap}.sav"))
    try:
        return log_ticks(h, live, mhz, vbls, poke)
    finally:
        h.close()


def cmd_ab(a) -> int:
    live = live_image(a.only)
    ok = True
    for snap in a.snapshot:
        for mhz in a.mhz:
            with ThreadPoolExecutor(2) as ex:
                fu = ex.submit(one, snap, None, mhz, a.vbls, a.poke)
                fp = ex.submit(one, snap, live, mhz, a.vbls, a.poke)
                U, P = fu.result(), fp.result()
            T = [(v, m) for v, m in P if W(m[PH_ADDR]) in (0, 5)]
            ku = {key(m): i for i, (v, m) in enumerate(U)}
            j0 = next((j for j, (v, m) in enumerate(T) if key(m) in ku), None)
            if j0 is None:
                print(f"{snap} {mhz} MHz: NO common state"); ok = False; continue
            i0 = ku[key(T[j0][1])]
            n = min(len(U) - i0, len(T) - j0)
            bad: dict[int, list[int]] = {}
            for k in range(n):
                for addr, ub in U[i0 + k][1].items():
                    if addr == PH_ADDR or addr < 0:          # -1: CPU cycle counter stamp of `rate`
                        continue
                    u, x = bytearray(ub), bytearray(T[j0 + k][1][addr])
                    for p in MASK:
                        if addr <= p < addr + len(u):
                            u[p - addr] = x[p - addr] = 0
                    if u != x:
                        bad.setdefault(addr, []).append(k)
            ok &= not bad
            nd = sum(1 for _, m in P if W(m[PH_ADDR]) not in (0, 5))
            print(f"{snap} {mhz:2d} MHz: unpatched {len(U)} passes, patched {len(P)} passes ({nd} view sub-passes), "
                  f"paired U[{i0}]=P[{j0}], {n} ticks compared: "
                  + ("IDENTICAL" if not bad else "DIFFER " + ", ".join(f"${k:x}@{v[:5]}" for k, v in bad.items())))
    return 0 if ok else 1


def fps_one(snap, live, mhz, vbls):
    h = MW1(snapshot=str(SNAP / f"{snap}.sav"))
    try:
        if mhz != 8:
            h.set_cpuclock(mhz)
        if live:
            at_flip(h, apply_cmds(live))
        return h.fps(vbls)["flips"]
    finally:
        h.close()


def cmd_fps(a) -> int:
    live = live_image(a.only)
    print(f"flips per {a.vbls} VBL (fps = flips * 50 / {a.vbls}): snapshot, MHz, unpatched, patched")
    for snap in a.snapshot:
        for mhz in a.mhz:
            with ThreadPoolExecutor(2) as ex:
                fu = ex.submit(fps_one, snap, None, mhz, a.vbls)
                fp = ex.submit(fps_one, snap, live, mhz, a.vbls)
                print(f"{snap:15s} {mhz:2d} MHz  {fu.result():4d}  {fp.result():4d}")
    return 0


def cmd_cold(a) -> int:
    from stharness import TOS
    kw = dict(snapshot=None, memsize_kb=a.mem, game_dir=Path(a.game).resolve(), tos=TOS[a.tos])
    if a.machine != "ste":
        kw["machine"] = a.machine
    h = MW1(**kw)
    try:
        t0 = time.time()
        h.boot_to_game("M")
        print(f"boot {time.time() - t0:.0f} s; marker {h.peek(0xB2FF8, 4).decode('latin1')}; $14e00 {h.peek(0x14E00, 8).hex()}; "
              f"$b3100 {h.peek(0xB3100, 4).hex()}; state {h.gstate()}")
        sync = h.peek(0xFF820A, 1)[0]
        print(f"sync mode $ff820a = ${sync:02x} -> boot refresh {50 if sync & 2 else 60} Hz")
        if a.hz == 60 and sync & 2:
            h.debug("w $ff820a $00", 0.5)
            time.sleep(1.0)
        hz = a.hz or (50 if sync & 2 else 60)
        sync = h.peek(0xFF820A, 1)[0]
        print(f"measuring at {hz} Hz (sync byte now ${sync:02x})")
        lf = h.R / "coldlog.txt"
        lf.write_text("e VBL\nm $12c60 8\nm $15110 8\nm $2c45a 2\n" + f"m ${PH_ADDR:x} 2\n")
        h.walk()
        for mhz in (8, 16):
            if mhz == 16:
                h.set_cpuclock(16)
            at_flip(h, [f"b pc = $14ac4 :trace :file {lf}"])
            s2 = len(h._logtext())
            h.cmd(f"hatari-debug b VBL > {h.vbl() + a.vbls} :trace :once")
            wait_gone(h, s2)
            out = h._logtext()[s2:]
            h.debug("b all", 0.3)
            T = []
            for blk in out.split("Reading debugger commands")[1:]:
                v = re.search(r"#(\d+) \(dec\)", blk)
                ms = re.findall(r"^[0-9A-F]{8}: ((?:[0-9a-f]{2} ?)+?)\s{2}", blk, re.M)
                if v and len(ms) >= 4:
                    b = [bytes.fromhex(x.replace(" ", "")) for x in ms[:4]]
                    if W(b[3]) in (0, 5):
                        T.append((int(v.group(1)), L(b[0]), L(b[0], 4), W(b[1], 2), W(b[2])))
            (v0, x0, z0, s0, c0), (v1, x1, z1, s1, c1) = T[0], T[-1]
            sec = (v1 - v0) / hz
            print(f"  {mhz:2d} MHz: {len(T) - 1} ticks in {sec:.2f} s = {(len(T) - 1) / sec:.3f} ticks/s; x {x0}->{x1} z {z0}->{z1} "
                  f"speed {s0}->{s1}; clock {c0}->{c1}")
    finally:
        h.close()
    return 0


def cmd_rate(a) -> int:
    live = live_image(a.only)
    print("RESULT lines: snapshot, MHz, Hz, cycles per VBL (8 MHz / hz = 160 k / 133 k), ticks, VBL span, ticks per emulated second")
    for snap in a.snapshot:
        for hz in a.hz:
            for mhz in a.mhz:
                poke = ["w $ff820a $00"] if hz == 60 else []
                rows = one(snap, live, mhz, a.vbls, poke)
                T = [(v, m) for v, m in rows if W(m[PH_ADDR]) in (0, 5)]
                (v0, m0), (v1, m1) = T[0], T[-1]
                cyc = ((m1[-1] - m0[-1]) & 0xFFFFFFFF) / (v1 - v0)
                print(f"RESULT {snap} {mhz} MHz {hz} Hz: {cyc:.0f} cycles/VBL, {len(T) - 1} ticks in {v1 - v0} VBL = {(v1 - v0) / hz:.2f} s: "
                      f"{(len(T) - 1) * hz / (v1 - v0):.3f} ticks/s")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cold")
    c.add_argument("--game", required=True)
    c.add_argument("--mem", type=int, default=1024)
    c.add_argument("--machine", default="ste")
    c.add_argument("--tos", default="1.62")
    c.add_argument("--vbls", type=int, default=600)
    c.add_argument("--hz", type=int, choices=[50, 60], default=None, help="force this refresh (poke $ff820a) and measure at it; default: the booted one")
    r = sub.add_parser("rate")
    r.add_argument("--only", nargs="+", required=True)
    r.add_argument("--snapshot", nargs="+", default=["1mb_ski_walk"])
    r.add_argument("--mhz", nargs="+", type=int, default=[8, 16])
    r.add_argument("--hz", nargs="+", type=int, choices=[50, 60], default=[50, 60])
    r.add_argument("--vbls", type=int, default=1500)
    for name in ("ab", "fps"):
        p = sub.add_parser(name)
        p.add_argument("--only", nargs="+", required=True)
        p.add_argument("--snapshot", nargs="+", default=["1mb_ski_walk", "1mb_ski_turn"])
        p.add_argument("--mhz", nargs="+", type=int, default=[8])
        p.add_argument("--vbls", type=int, default=700 if name == "ab" else 1000)
        if name == "ab":
            p.add_argument("--poke", nargs="*", default=[], help="debugger commands run at apply time, e.g. 'w $24faa $01 $90'")
    a = ap.parse_args()
    sys.exit(cmd_ab(a) if a.cmd == "ab" else cmd_fps(a) if a.cmd == "fps" else cmd_rate(a) if a.cmd == "rate" else cmd_cold(a))


if __name__ == "__main__":
    main()
