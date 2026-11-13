#!/usr/bin/env python3
"""Populous 2 free-RAM pattern test and cold-boot check of a pop2patch build.

    python3 tools/p2ptest.py [--build build/hd] [--mem 2048] [--machine ste] [--tos 1.62] [--tag NAME]
                             [--quick]    # boot to play, marker + credit screenshot, no pattern test

What it does (evidence for work/notes/delivery.md):
  1. cold boots the build (drive C: = the build folder);
  2. unless --quick: at the game entry ($1770, a debugger breakpoint) loads a recognisable pattern (long at
     address A = A*2654435761+$1234567) into the candidate free ranges R0-R2 below;
  3. boots to the main menu (screenshot with the credit), plays the first conquest battle, runs it busy with
     Hatari's fast-forward (~15,000 turns), clicks effects (volcano), HAGA's statesave (keypad /), RESTART MAP,
     QUIT MAP, a new conquest and a CUSTOM GAME (random landscape), dumping RAM after each step;
  4. after every step compares the ranges with the pattern and the payload at PB with the build's image.
Exit status 0 = nothing changed anywhere.
"""
from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
from populous2 import Populous2  # noqa: E402
from stharness import TOS  # noqa: E402

PB = 0x80000
# candidate free ranges (zero in the busy dump, work/notes/baseline.md); R0 and R1 are split around the payload
RANGES = [(0x7B380, PB - 8), (PB + 0x8000, 0xF8000), (0x167D00, 0x1D89F8)]


def pat(lo, hi):
    return b"".join(struct.pack(">I", (a * 2654435761 + 0x1234567) & 0xFFFFFFFF) for a in range(lo, hi, 4))


def expect(a):
    return (a * 2654435761 + 0x1234567) & 0xFFFFFFFF


def compare(d: bytes):
    bad_total = 0
    for lo, hi in RANGES:
        bad = [a for a in range(lo, hi, 4) if struct.unpack_from(">I", d, a)[0] != expect(a)]
        groups = []
        for a in bad:
            if groups and a - groups[-1][1] <= 16:
                groups[-1][1] = a + 4
            else:
                groups.append([a, a + 4])
        print(f"    ${lo:x}-${hi:x}: {len(bad)} longs changed" +
              (f"; {[(hex(a), hex(b)) for a, b in groups[:10]]}" if bad else ""))
        bad_total += len(bad)
    return bad_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build/hd")
    ap.add_argument("--mem", type=int, default=2048)
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", nargs="*", default=None, help="patch set (passed to pop2patch build/live)")
    ap.add_argument("--out", default="/tmp/p2pt")
    a = ap.parse_args()
    tag = a.tag or f"{a.machine}_{a.mem // 1024}mb"
    out = Path(a.out) / tag
    out.mkdir(parents=True, exist_ok=True)
    build = GAME / a.build
    only = [] if not a.only else ["--only"] + a.only
    subprocess.run([sys.executable, "tools/pop2patch.py", "build", "--out", str(build)] + only,
                   cwd=GAME, check=True, capture_output=True)
    subprocess.run([sys.executable, "tools/pop2patch.py", "live", "--out", "build/live/patches"] + only,
                   cwd=GAME, check=True, capture_output=True)
    img = (GAME / "build" / "live" / "patches.img").read_bytes()    # the same set as the build picked
    h = Populous2(snapshot=None, game_dir=build, memsize_kb=a.mem, machine=a.machine, tos=TOS[a.tos])
    bad = 0
    try:
        (h.R / "C" / "GAMEX").mkdir(exist_ok=True)
        if not a.quick:
            cmds = ""
            for i, (lo, hi) in enumerate(RANGES):
                f = out / f"r{i}.bin"
                f.write_bytes(pat(lo, hi))
                cmds += f"loadbin {f} ${lo:x}\n"
            (out / "cmds.txt").write_text(cmds)
            h.cmd(f"hatari-debug b pc = $1770 :trace :once :file {out}/cmds.txt")
        if not h.boot_to_menu():
            print("FAIL: never reached the main menu"); return 1
        shot = GAME / "work" / "shots" / f"credit_menu_{tag}.png"
        h.shot(str(shot))
        print(f"[{tag}] main menu reached; marker {h.marker()!r}; credit screenshot {shot}")
        if h.marker() != "P2PO":
            bad += 1

        def check(step):
            nonlocal bad
            p = out / f"d_{step}.bin"
            h.dump(str(p), 0, a.mem * 1024)
            for _ in range(60):
                if p.exists() and p.stat().st_size == a.mem * 1024:
                    break
                time.sleep(1)
            d = p.read_bytes()
            ok = d[PB:PB + len(img)] == img and d[PB - 8:PB - 4] == b"P2PO"
            print(f"[{tag}] {step}: payload {'intact' if ok else 'CHANGED'}")
            bad += not ok
            if not a.quick:
                bad += compare(d)
            p.unlink()

        check("menu")
        h._click(384, 257, 3)
        h._click(260, 98, 1.0)
        for ch in "zeus":
            h.key(ch, 0.3); time.sleep(0.4)
        h.key("Return", 0.3); time.sleep(1.0)
        h._click(424, 418, 3)
        h._click(384, 258, 8); h._click(216, 448, 12); h._click(400, 420, 15)
        if not h.in_play():
            print("FAIL: not in play"); return 1
        print(f"[{tag}] in play, turn {h.peekw(0x3979C)}")
        check("play")
        if a.quick:
            return 1 if bad else 0
        h.cmd("hatari-option --fast-forward on"); time.sleep(95)
        print(f"[{tag}] busy: turn {h.peekl(0x3979A)}")
        h.cmd("hatari-option --fast-forward off"); time.sleep(1)
        check("busy")
        for k in ("F1", "1", "2", "3", "4", "5", "F2", "1", "2", "3", "F3", "1", "2", "F4", "1", "2", "3",
                  "F5", "1", "2", "3", "F6", "1", "2", "3"):
            h.key(k, 0.2); time.sleep(0.4)
            h._click(430, 300, 0.5)
        h.shot(str(GAME / "work" / "shots" / f"p2ptest_effects_{tag}.png"))
        check("effects")
        h.key("KP_Divide", 0.3); time.sleep(8)
        gs = h.R / "C" / "GS00.TOS"
        print(f"[{tag}] HAGA statesave: {'GS00.TOS %d bytes' % gs.stat().st_size if gs.exists() else 'NO FILE'}")
        check("statesave")
        h._click(707, 374, 3); h._click(290, 194, 10)          # game requester -> RESTART MAP
        h._click(216, 448, 12); h._click(400, 420, 15)
        print(f"[{tag}] restart map: in play {h.in_play()}")
        check("restart")
        h._click(707, 374, 3); h._click(560, 194, 10)          # QUIT MAP -> main menu
        h._click(384, 258, 8); h._click(216, 448, 12); h._click(400, 420, 15)
        print(f"[{tag}] new conquest: in play {h.in_play()}")
        check("conquest2")
        h._click(707, 374, 3); h._click(560, 194, 10)
        h._click(384, 274, 10)                                   # CUSTOM GAME (random landscape)
        time.sleep(3)
        print(f"[{tag}] custom game: in play {h.in_play()}")
        h.cmd("hatari-option --fast-forward on"); time.sleep(30); h.cmd("hatari-option --fast-forward off")
        check("custom")
    finally:
        h.close()
    print(f"[{tag}] RESULT: {'ALL INTACT' if not bad else str(bad) + ' PROBLEM(S)'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
