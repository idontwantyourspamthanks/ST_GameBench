#!/usr/bin/env python3
"""World-tick rate gate for the MW2 timing patches (p3b_head set or tick_head, with tick_vbl), at 50 and 60 Hz.

    python3 tools/mw2tick.py rate --only tick_vbl p3b_head p3b_render p3b_pos p3b_hdg p3b_alt p3b_bank p3b_save p3b_probe \
            [--snapshot work/snapshots/1mb_ingame_walking.sav] [--mhz 8 16] [--hz 50 60] [--vbls 1500]
    python3 tools/mw2tick.py cold --game build/x [--mem 1024] [--machine ste] [--tos 1.62] [--hz 50|60] [--vbls 1500]

A world tick = one arrival at `$3148e`, the instruction after the head of the in-game frame loop (`$31486`: `lea $770e.w,a6 ; jsr $4f5a`, which
tick_head and p3b_head replace by a call into the blob that tail-calls `$4f5a`; p3b sub-tick passes drop their return and never reach `$3148e`).
(`$4f5a` itself is NOT once per tick: it is a shared subroutine, 2 hits per tick measured.) The tool logs `e VBL` at every call and reports
(n - 1) ticks per (VBL span / hz) seconds of EMULATED time, so there is no window quantisation. The display refresh is read back from
`$ff820a` and proved with the CPU cycles per VBL (8 MHz / 50 = 160 k, 8 MHz / 60 = 133 k).
rate  restores the snapshot, and at the first flip after an absolute VBL applies the live patch set (mw2patch.py live) and, for --hz 60,
      `w $ff820a $00` (Hatari switches the monitor to 60 Hz at the next frame).
cold  boots a built game dir to the Lobos 3D view (boot_to_game), then measures at 8 and 16 MHz; --hz forces the refresh by poking
      `$ff820a`, without it the booted refresh is reported and used (a Mega STE with TOS 2.06 boots at the TOS image's own refresh).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
from mw2harness import Hatari  # noqa: E402

TICK_PC = 0x3148E       # first instruction after the loop head's displaced `jsr $4f5a` (reached once per world tick; p3b sub-tick passes jump away)
SYNC = 0xFF820A


def live_image(only: list[str]) -> str:
    out = GAME / "build" / "tick" / ("live_" + "_".join(sorted(only))[:60])
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(HERE / "mw2patch.py"), "live", "--only", *only, "--out", str(out.relative_to(GAME))],
                   check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    return str(out)


def apply_cmds(live: str) -> list[str]:
    spec = json.loads(Path(live + ".json").read_text())
    c = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
    c += [f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])) for s in spec["sites"]]
    return c


def wait_gone(h, start: int, timeout: float = 900):
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("breakpoint never fired")
        time.sleep(0.4)
    time.sleep(0.4)


def at_flip(h, cmds: list[str], after_vbl: int):
    """Run debugger `cmds` at the first flip after absolute VBL `after_vbl` (code is never patched while the CPU is mid-frame)."""
    f = h.R / "atflip.txt"
    f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {after_vbl} && pc = ${h.FLIP:x} :trace :once :file {f}")
    wait_gone(h, start, 300)


def measure(h, vbls: int, hz_expect: int | None = None) -> dict:
    """Log `e VBL` (+ CycleCounter at the first/last stop) at every world tick for `vbls` VBL."""
    lf = h.R / "tick.txt"
    lf.write_text("e VBL\ne CycleCounter\n")
    h.debug("b all", 0.3)
    s2 = len(h._logtext())
    v0 = h.vbl()
    h.cmd(f"hatari-debug b pc = ${TICK_PC:x} :trace :file {lf}")
    time.sleep(0.2)
    h.cmd(f"hatari-debug b VBL > {v0 + vbls} :trace :once")
    wait_gone(h, s2)
    out = h._logtext()[s2:]
    h.debug("b all", 0.3)
    rows = [(int(v), int(c, 16)) for v, c in re.findall(r"> e VBL\n= .*?#(\d+) \(dec\).*\n> e CycleCounter\n= .*?\$([0-9a-fA-F]+) \(hex\)", out)]
    if len(rows) < 3:
        raise RuntimeError(f"only {len(rows)} tick rows; log tail:\n{out[-800:]}")
    return {"rows": rows, "sync": h.peekw(SYNC) >> 8}


def report(tag: str, hz: int, m: dict) -> str:
    rows = m["rows"]
    (v0, c0), (v1, c1) = rows[0], rows[-1]
    n = len(rows) - 1
    cyc = ((c1 - c0) & 0xFFFFFFFF) / (v1 - v0)
    gp = [(a[0], b[0] - a[0]) for a, b in zip(rows, rows[1:])]
    big = [(t - v0, g) for t, g in gp if g > 30]      # stalls > 30 VBL: the game's own local-map rebuild (sub_031dee, ~92 Mcycles: 5.7 s at 16 MHz, 11.5 s at 8 MHz, once per 40 cells walked; work/notes/timing.md), not the tick rate
    steady = [g for _, g in gp if g <= 30]
    return (f"RESULT {tag}: sync ${m['sync']:02x}, {cyc:.0f} cycles/VBL, {n} ticks in {v1 - v0} VBL = {(v1 - v0) / hz:.2f} s: "
            f"{n * hz / (v1 - v0):.3f} ticks/s; without stalls > 30 VBL {big}: {len(steady)} ticks in {sum(steady)} VBL = "
            f"{len(steady) * hz / sum(steady):.3f} ticks/s")


def cmd_rate(a) -> int:
    live = a.live or live_image(a.only)
    for hz in a.hz:
        for mhz in a.mhz:
            h = Hatari(snapshot=str(GAME / a.snapshot), memsize_kb=1024)
            try:
                if mhz != 8:
                    h.set_cpuclock(mhz)
                at = h.vbl() + 100
                at_flip(h, apply_cmds(live) + (["w $ff820a $00"] if hz == 60 else []), at)
                time.sleep(1.0)
                print(report(f"{Path(a.snapshot).stem} {mhz} MHz {hz} Hz", hz, measure(h, a.vbls)), flush=True)
            finally:
                h.close()
    return 0


def cmd_cold(a) -> int:
    sys.path.insert(0, str(GAME.parent.parent / "tools"))
    from stharness import TOS
    kw = dict(snapshot=None, memsize_kb=a.mem, game_dir=Path(a.game).resolve(), tos=TOS[a.tos], machine=a.machine)
    h = Hatari(**kw)
    try:
        t0 = time.time()
        h.boot_to_game("M")
        sync = h.peekw(SYNC) >> 8
        print(f"boot {time.time() - t0:.0f} s; marker {h.peekw(0xB2FF8):04x}{h.peekw(0xB2FFA):04x}; $31486 {h.peekw(0x31486):04x}{h.peekw(0x31488):04x}; "
              f"sync $ff820a = ${sync:02x} -> booted at {50 if sync & 2 else 60} Hz", flush=True)
        if a.hz == 60 and sync & 2:
            h.debug("w $ff820a $00", 0.5)
            time.sleep(1.0)
        hz = a.hz or (50 if sync & 2 else 60)
        for mhz in (8, 16):
            h.set_cpuclock(mhz)          # explicit for both: Hatari's Mega STE starts at 16 MHz
            print(report(f"cold {a.machine} TOS {a.tos} {a.mem} KB {mhz} MHz {hz} Hz", hz, measure(h, a.vbls)), flush=True)
    finally:
        h.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rate")
    r.add_argument("--only", nargs="+", default=[])
    r.add_argument("--live", help="a prebuilt `mw2patch.py live --out PREFIX` image instead of --only")
    r.add_argument("--snapshot", default="work/snapshots/1mb_ingame_walking.sav")
    r.add_argument("--mhz", nargs="+", type=int, default=[8, 16])
    r.add_argument("--hz", nargs="+", type=int, choices=[50, 60], default=[50, 60])
    r.add_argument("--vbls", type=int, default=1500)
    c = sub.add_parser("cold")
    c.add_argument("--game", required=True)
    c.add_argument("--mem", type=int, default=1024)
    c.add_argument("--machine", default="ste")
    c.add_argument("--tos", default="1.62")
    c.add_argument("--hz", type=int, choices=[50, 60], default=None)
    c.add_argument("--vbls", type=int, default=1500)
    a = ap.parse_args()
    sys.exit(cmd_rate(a) if a.cmd == "rate" else cmd_cold(a))


if __name__ == "__main__":
    main()
