#!/usr/bin/env python3
"""Cold boots of a build with the v1.2 visual patches (pal_*, sky_*) on every machine: work/notes/visuals.md.

    python3 tools/huntvis_cold.py hd     --machine ste|st|megaste|tt [--mem 1024] [--game build/vis_hd]
    python3 tools/huntvis_cold.py floppy --machine ste|st|falcon|tt   [--disk1 build/vis_fl/HUNTER_disk1.st] [--blind --pb-at 35]

After the boot (the harness's own navigation to the 3D view): marker, FLAGS, the sky state (SKY_ST: $7f on, $ff off), the six
splice sites, fps; a day and a night screenshot (work/shots/visuals_cold_<build>_<machine>_{day,night}.png); the palette;
where the sky is on, the raster gate of tools/huntvis.py on a paused frame, with and without mouse traffic; then 10 s of
walking and a last state check (no crash).  TT runs with `--mmu true`.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from stharness import TOS, MACHINE_TOS  # noqa: E402
import huntvis as hv  # noqa: E402

SITES = {0xC5F0: 8, 0xC84A: 8, 0xC8C2: 6, 0x6790: 8, 0x61FA: 6, 0xB004: 6, 0xC61C: 6, 0x67FC: 10, 0x6200: 8}


def report(h, tag: str, machine: str, sky_expected: bool):
    v = hv.var(h)
    print(f"BOOT OK {tag} machine={machine} in_game={h.in_game()} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()} "
          f"SKY_ST=${v['st']:02x} cfg={v['cfg']} H={v['H']} fps={h.fps(250)}", flush=True)
    print("  sites:", " ".join(f"${a:x}={h.peek(a, n).hex()}" for a, n in SITES.items()))
    print("  MFP: IERA=%s IMRA=%s TBCR=%s vec$118=%s vec$120=%s" % (h.peek(0xFFFA07, 1).hex(), h.peek(0xFFFA13, 1).hex(), h.peek(0xFFFA1B, 1).hex(),
                                                                 h.peek(0x118, 4).hex(), h.peek(0x120, 4).hex()))
    hv.SHOTS.mkdir(parents=True, exist_ok=True)
    std = machine in ("st", "megast", "ste", "megaste")
    ok = True
    px0 = h.peek(hv.A5 + 0xD8, 4)                       # the pointer follows the mouse in the 3D view (not while paused)
    h.rel(-60, -30)
    time.sleep(0.5)
    print(f"  mouse alive: pointer {px0.hex()} -> {h.peek(hv.A5 + 0xD8, 4).hex()}")
    for nm, hour in (("day", 12), ("night", 2)):
        hv.to_hour(h, hour, settle=9)
        out = hv.SHOTS / f"visuals_cold_{tag}_{machine}_{nm}.png"
        h.shot(str(out))
        v = hv.var(h)
        print(f"  {nm}: palette {hv.fmt(hv.hwpal(h))} level={h.peek(hv.A5 + 0x18c, 2).hex()} SKY H={v['H']} panel-split={v['pneed']} -> {out.name}", flush=True)
        if std and v["st"] == 0x7F:
            idx, rgb = hv.frozen(h, "cold")
            vv = hv.var(h)
            bi = hv.band_info(h)
            r, msgs, t = hv.raster_check(idx, rgb, vv["H"] if vv["cfg"] & 1 else 0, bands=bi)
            print(f"  RASTER {nm} paused frame H={vv['H']}: bands {hv.fmt(bi[0])} top {bi[1]:03x}; colour-15 changes after rows {[x[0] for x in t]}: {'PASS' if r else 'FAIL'}")
            for m in msgs[:5]:
                print("     ", m)
            ok &= r
            # mouse traffic: IKBD packets all over the frame; rows 0..139 judged (the pointer is in the panel rows)
            stop = False

            def mover():
                s = 1
                while not stop:
                    h.rel(24 * s, 0, steps=6)
                    s = -s
            th = threading.Thread(target=mover)
            th.start()
            bad = 0
            try:
                for _ in range(10):
                    rgb2 = hv.shot_rgb(h, str(hv.WORK / "cold2.png"))
                    r2, m2, _ = hv.raster_check(np.vstack([idx[:140], np.zeros((60, 320), np.uint8)]),
                                                np.vstack([rgb2[:140], np.zeros((60, 320, 3), np.uint8)]), vv["H"] if vv["cfg"] & 1 else 0, bands=bi)
                    bad += not r2
            finally:
                stop = True
                th.join()
            print(f"  RASTER {nm} with mouse traffic: {10 - bad} of 10 frames clean: {'PASS' if not bad else 'FAIL'}")
            ok &= not bad
            h.key("p", 0.5)                               # un-pause
            time.sleep(1.5)
    h.hold("Up")
    time.sleep(10)
    h.release("Up")
    time.sleep(1)
    v = hv.var(h)
    alive = h.in_game()
    print(f"  after 10 s of walking: in_game={alive} SKY_ST=${v['st']:02x} H={v['H']} pos={h.peek(0xAB2, 6).hex()} "
          f"expected sky {'on' if sky_expected else 'off'}: {'OK' if (v['st'] == 0x7F) == sky_expected and alive else 'MISMATCH'}")
    print(f"COLD {tag} {machine}: {'PASS' if ok and alive and (v['st'] == 0x7F) == sky_expected else 'FAIL'}", flush=True)


def harden(h):
    """Harness gates on a loaded host: retry a half-written screenshot; looser colour tolerance for the stage crops (they are
    v1.1 STE pictures; with pal_ the same screens are half a palette step brighter); long stage time-outs."""
    sm = h.screen_matches

    def retry(*aa, **kk):
        for i in range(5):
            try:
                return sm(*aa, **kk)
            except Exception:
                time.sleep(0.6)
        return False
    h.screen_matches = retry
    h.TOL = {k: 14.0 for k in h.STAGES}
    stage = h._stage
    h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))


def cmd_hd(a):
    import hunter as hmod
    orig = hmod.build_hd
    hmod.build_hd = lambda img, **k: orig(img, game=GAME / a.game, **k)
    h = hmod.Hunter(machine=a.machine, tos=TOS[a.tos] if a.tos else MACHINE_TOS[a.machine], memsize_kb=a.mem,
                    extra=["--mmu", "true", "--monitor", "vga", "--cpuclock", "32"] if a.machine == "tt" else [])
    try:
        harden(h)
        if a.machine in ("st", "megast"):
            from huntpatch import blind_boot              # the reference crops are STE pictures
            blind_boot(h)
        elif a.machine == "tt":                           # as tools/hunt_ttf.py boot_hd: no HW/title1 crops on a TT
            time.sleep(10)
            h.keypress(57)
            time.sleep(3)
            for st_, w in (("title2", 200),):
                if not h.wait_stage(st_, w, 2):
                    raise RuntimeError(f"screen {st_} not reached")
            time.sleep(1.5)
            h.key("space", 0.3)
            for st_, xy in (("main", h.START_XY), ("games", h.ACTION_XY)):
                if not h.wait_stage(st_, 40, 2):
                    raise RuntimeError(f"screen {st_} not reached")
                h.goto(*xy, home_xy=h.HOME_XY)
                h.click()
            if not h.wait_stage("name", 30, 2):
                raise RuntimeError("name not reached")
            for c in "bench":
                h.key(c, 0.15)
                time.sleep(0.3)
            h.click()
            if not h.wait_stage("mission", 30, 2):
                raise RuntimeError("mission not reached")
            h.click()
            if not h.wait_stage("game", 60, 2):
                raise RuntimeError("game HUD not reached")
            time.sleep(1.0)
        else:
            h.boot_to_game()
        report(h, "hd", a.machine, a.machine in ("st", "megast", "ste", "megaste"))
    finally:
        hmod.build_hd = orig
        h.close()


def cmd_floppy(a):
    from huntfloppy import HunterFloppy
    default_tos = {"ste": "1.62", "st": "1.04", "falcon": "4.04", "tt": "3.06", "megaste": "2.06"}
    h = HunterFloppy(GAME / a.disk1, None, drives=1, machine=a.machine, tos=TOS[a.tos or default_tos[a.machine]], memsize_kb=a.mem,
                     extra=["--mmu", "true", "--monitor", "vga", "--cpuclock", "32"] if a.machine == "tt" else [], fastfdc=a.fastfdc)
    harden(h)
    try:
        ok = h.boot_floppy("none", blind=a.blind, pb_key_at=a.pb_at)
        if not ok:
            print(f"BOOT FAILED floppy machine={a.machine} MARKER={h.peek(0x8BFF8, 4)!r}")
            return
        report(h, "floppy", a.machine, a.machine in ("st", "megast", "ste", "megaste"))
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("hd")
    c.add_argument("--game", default="build/vis_hd")
    f = sub.add_parser("floppy")
    f.add_argument("--disk1", default="build/vis_fl/HUNTER_disk1.st")
    f.add_argument("--blind", action="store_true")
    f.add_argument("--pb-at", type=float, default=12)
    f.add_argument("--fastfdc", default="no")
    for p in (c, f):
        p.add_argument("--machine", default="ste")
        p.add_argument("--tos", default=None)
        p.add_argument("--mem", type=int, default=1024)
    a = ap.parse_args()
    hv.WORK.mkdir(exist_ok=True)
    {"hd": cmd_hd, "floppy": cmd_floppy}[a.cmd](a)


if __name__ == "__main__":
    main()
