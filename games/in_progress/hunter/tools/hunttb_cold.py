#!/usr/bin/env python3
"""Cold boots with triple buffering in the build (HunterTB2; notes work/notes/triple.md section 6).

    python3 tools/hunttb_cold.py hd     --machine st|ste|megaste|tt [--game build/tb2_hd] [--mem 1024]
    python3 tools/hunttb_cold.py floppy --machine st|ste|megaste|falcon|tt [--disk1 build/tb2_fl/HUNTER_disk1.st] [--blind --pb-at 35]

After the harness's own navigation to the 3D view: marker, FLAGS, the tb state block ($8c1b2: VBL counter, VBL at the last flip,
mode word 1 = on / 2 = off), the three tb sites, fps, and 60 samples of the draw/shown page pointers ($144/$148(a5) = $94a/$94e):
with triple buffering on all of $23000, $2ad00 and $81000 must appear, with it off only $23000/$2ad00 (the original flip).
TT = `--mmu true --monitor vga --cpuclock 32` (dist/run_tt.sh), Falcon = `--cpuclock 16 --monitor vga` (dist/run_falcon.sh).
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from stharness import TOS, MACHINE_TOS  # noqa: E402
import huntvis_cold as vc  # noqa: E402

EXTRA = {"tt": ["--mmu", "true", "--monitor", "vga", "--cpuclock", "32"],
         "falcon": ["--cpuclock", "16"]}
SITES = {0x5FD2: 6, 0x5FC2: 6, 0xC600: 6}
NAMES = {0x23000: "A", 0x2AD00: "B", 0x81000: "C"}


def report(h, tag, machine):
    st = h.peek(0x8C1B2, 8)
    cnt = lambda b: int.from_bytes(b, "big")  # noqa: E731
    in3d = h.in_game()
    print(f"BOOT {tag} machine={machine} in_game={in3d} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()}", flush=True)
    print(f"  tb state $8c1b2: {st.hex()}  (VBL {cnt(st[0:2])}, last flip {cnt(st[2:4])}, mode {cnt(st[4:6])}: 1 = on, 2 = off)")
    print("  sites:", " ".join(f"${a:x}={h.peek(a, n).hex()}" for a, n in SITES.items()))
    seen = Counter()
    for _ in range(60):
        b = h.peek(0x94A, 8)
        seen[(NAMES.get(cnt(b[0:4]), hex(cnt(b[0:4]))), NAMES.get(cnt(b[4:8]), hex(cnt(b[4:8]))))] += 1
        time.sleep(0.05)
    draw = {k[0] for k in seen}
    shown = {k[1] for k in seen}
    print(f"  (draw $144, shown $148) samples: {dict(seen)}")
    print(f"  pages drawn into: {sorted(draw)}  shown: {sorted(shown)}")
    st2 = h.peek(0x8C1B2, 8)
    print(f"  tb state later:  {st2.hex()} (VBL counter advancing: {cnt(st2[0:2]) != cnt(st[0:2])})  fps={h.fps(250)}", flush=True)
    return {"mode": cnt(st[4:6]), "in_game": in3d, "pages": sorted(draw | shown)}


def hd(a):
    import hunter as hmod
    orig = hmod.build_hd
    hmod.build_hd = lambda img, **k: orig(img, game=GAME / a.game, **k)
    mem = a.mem
    h = hmod.Hunter(machine=a.machine, tos=TOS[a.tos] if a.tos else MACHINE_TOS[a.machine], memsize_kb=mem, extra=EXTRA.get(a.machine, []))
    try:
        vc.harden(h)
        if a.machine in ("st", "megast"):
            from huntpatch import blind_boot
            blind_boot(h)
        elif a.machine == "tt":
            time.sleep(10)
            h.keypress(57)
            time.sleep(3)
            if not h.wait_stage("title2", 200, 2):
                raise RuntimeError("screen title2 not reached")
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
        report(h, "hd", a.machine)
    finally:
        hmod.build_hd = orig
        h.close()


def floppy(a):
    from huntfloppy import HunterFloppy
    dt = {"ste": "1.62", "st": "1.04", "falcon": "4.04", "tt": "3.06", "megaste": "2.06"}
    h = HunterFloppy(GAME / a.disk1, None, drives=1, machine=a.machine, tos=TOS[a.tos or dt[a.machine]], memsize_kb=a.mem,
                     extra=EXTRA.get(a.machine, []), fastfdc="no")
    vc.harden(h)
    import huntfloppy
    real_sleep = time.sleep
    if a.blind:       # the single 82x11 disk with the sample bank loads longer than the 81x10 lean disk the blind waits were sized for
        huntfloppy.time = type("T", (), {"sleep": staticmethod(lambda x: real_sleep(a.title_wait if x == 30 else x)),
                                          "time": staticmethod(time.time)})
    try:
        ok = h.boot_floppy("none", blind=a.blind, pb_key_at=a.pb_at)
        for _ in range(4):               # a blind click on the mission page is sometimes lost on the slower machines: click again
            if ok:
                break
            h.click()
            time.sleep(12)
            ok = h.in_game()
            print(f"  retry click: in_game={ok}", flush=True)
        if not ok:
            print(f"BOOT FAILED floppy machine={a.machine} MARKER={h.peek(0x8BFF8, 4)!r} mode$899={h.peek(0x899, 1).hex()} "
                  f"tb={h.peek(0x8C1B2, 8).hex()} fps={h.fps(100)}")
            h.shot(f"/tmp/tb2_fail_{a.machine}.png")
            for _ in range(3):
                print("  $1a8(a5)=$9ae:", h.peek(0x9AE, 2).hex(), "$95(a5)=$89b:", h.peek(0x89B, 1).hex(), "$cc(a5)=$8d2:", h.peek(0x8D2, 2).hex(),
                      "$7f5c:", h.peek(0x7F5C, 4).hex(), "VBL", h.vbl(), "tb", h.peek(0x8C1B2, 6).hex())
                time.sleep(1)
            prof = sorted(h.profile(30), key=lambda x: -x[1])[:25]
            print("  profile top (addr, cycles):", [(hex(x), c) for x, c in prof])
            print("  regs/flags $1a6..$1a7(a5) $9ac..$9af:", h.peek(0x9AC, 4).hex(), "$8f(a5)=", h.peek(0x895, 1).hex(),
                  "$7f6c/$7f74:", h.peek(0x7F6C, 12).hex(), "$144/$148:", h.peek(0x94A, 8).hex())
            return
        report(h, "floppy", a.machine)
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("hd")
    c.add_argument("--game", default="build/tb2_hd")
    f = sub.add_parser("floppy")
    f.add_argument("--disk1", default="build/tb2_fl/HUNTER_disk1.st")
    f.add_argument("--blind", action="store_true")
    f.add_argument("--pb-at", type=float, default=12)
    f.add_argument("--title-wait", type=float, default=30, help="blind: seconds to wait for the game to load before the title key presses")
    for p in (c, f):
        p.add_argument("--machine", default="ste")
        p.add_argument("--tos", default=None)
        p.add_argument("--mem", type=int, default=1024)
    a = ap.parse_args()
    {"hd": hd, "floppy": floppy}[a.cmd](a)


if __name__ == "__main__":
    main()
