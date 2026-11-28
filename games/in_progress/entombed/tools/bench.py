#!/usr/bin/env python3
"""Hatari benchmark & screenshot verification harness for Entombed STe Enhanced."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
BENCH = GAME_DIR.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
from stharness import Hatari, TOS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="run", help="Screenshot filename prefix")
    ap.add_argument("--title", action="store_true", help="Capture title screen with credit")
    ap.add_argument("--profile", action="store_true", help="Also run CPU profile in Tomb 1")
    ap.add_argument("--move", action="store_true", help="Test moving right in Tomb 1")
    ap.add_argument("--flip-reg", default="($ff8203).b", help="Shifter register to count flips")
    args = ap.parse_args()

    shots = GAME_DIR / "work" / "shots"
    shots.mkdir(parents=True, exist_ok=True)

    h = Hatari(
        game_dir=GAME_DIR,
        machine="ste",
        memsize_kb=1024,
        tos=TOS["1.62"],
        autorun="C:\\ENTOMBED.PRG",
        extra=["--joy1", "keys"],
        sound=True,
        flip_reg=args.flip_reg,
    )
    try:
        if args.title:
            # Wait for logo drop + copyright/credit to appear (~14s)
            time.sleep(14.0)
            p = h.shot(str(shots / f"{args.tag}_title.png"))
            print(f"Saved {p}")
        else:
            time.sleep(7.0)

        # Enter Tomb Select
        h.key("Control_R", hold=0.35)
        time.sleep(3.0)
        # Enter Tomb 1
        h.key("Control_R", hold=0.35)
        time.sleep(3.5)
        p1 = h.shot(str(shots / f"{args.tag}_tomb1.png"))
        print(f"Saved {p1}")

        sync50 = [l for l in h.debug("m $ff820a 1", 0.4).splitlines() if "00FF820A" in l]
        print("50Hz sync:", sync50)
        t0 = h.peekw(0x1815e)
        r50 = h.fps(150)
        t1 = h.peekw(0x1815e)
        dt50 = (t1 - t0) & 0xffff
        print(f"50Hz: {r50['flips']} flips / 150 VBLs = {r50['fps']:.2f} fps  |  world ticks={dt50} ({dt50*50.0/150:.2f} Hz)")

        # Toggle to 60Hz with 'H' (scancode 35)
        h.keypress(35)
        time.sleep(0.5)
        sync60 = [l for l in h.debug("m $ff820a 1", 0.4).splitlines() if "00FF820A" in l]
        print("60Hz sync:", sync60)
        t0 = h.peekw(0x1815e)
        r60 = h.fps(180)
        t1 = h.peekw(0x1815e)
        dt60 = (t1 - t0) & 0xffff
        fps60 = r60["flips"] * 60.0 / 180.0
        print(f"60Hz: {r60['flips']} flips / 180 VBLs = {fps60:.2f} fps  |  world ticks={dt60} ({dt60*60.0/180:.2f} Hz)")

        if args.move:
            h._xdo("keydown", "--window", h.win, "Right")
            time.sleep(0.75)
            h._xdo("keyup", "--window", h.win, "Right")
            h.shot(str(shots / f"{args.tag}_tomb1_move.png"))
            r60m = h.fps(120)
            print(f"60Hz post-move: {r60m['flips']} flips / 120 VBLs = {r60m['flips']*60.0/120:.2f} fps")

        if args.profile:
            rows = h.profile(180)
            tot = sum(c for _, c in rows)
            out = GAME_DIR / "work" / "dumps" / f"prof_{args.tag}.txt"
            with open(out, "w") as f:
                for a, c in rows:
                    f.write(f"0x{a:06x} {100*c/tot:6.2f}% {c}\n")
            print(f"Saved profile ({tot:,} cyc) -> {out}")
    finally:
        h.close()


if __name__ == "__main__":
    main()
