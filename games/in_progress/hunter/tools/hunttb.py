#!/usr/bin/env python3
"""Hunter free-RAM proof and triple-buffer experiment helpers (HunterTriple; notes: work/notes/triple.md).

    from hunttb import *
    h = boot_hd(game='build/tb_hd', mem=1024, regions=[(0x81000, 0x8BA00)])   # pattern loaded when START jumps to the game
    ...play...
    check(h, regions)                                                          # dump RAM and compare against the pattern

The pattern is `huntpatch.fill_byte(a)` (never 0).  Handover = `pc = $800` (the game entry): the patched START stub jumps there directly, so `$80154` is skipped.  Everything is read-only for the game folder: the harness copies it.
"""
from __future__ import annotations

import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
import hunter  # noqa: E402
import huntpatch  # noqa: E402
from hunter import Hunter, TOS  # noqa: E402

HD_START, FL_START = 0x800, 0x800   # the game entry: reached by both the unpatched tail ($80154) and our stub (which jumps straight to $800)


def pattern(lo: int, hi: int) -> bytes:
    return bytes(huntpatch.fill_byte(a) for a in range(lo, hi))


def arm_pattern(h, regions, pc):
    """Debugger script run once at `pc`: loadbin the pattern of every region."""
    lines = []
    for i, (lo, hi) in enumerate(regions):
        p = h.R / f"pat{i}.bin"
        p.write_bytes(pattern(lo, hi))
        lines.append(f"loadbin {p} ${lo:x}")
    cf = h.R / "start.txt"
    cf.write_text("\n".join(lines) + "\n")
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${pc:x} :trace :once :file {cf}")
    time.sleep(0.3)


def boot_hd(game="build/tb_hd", mem=1024, machine="ste", tos="1.62", regions=(), extra=None, bus=None, blind=False, boot=True):
    """Cold boot the HD build into the 3D view (Hunter.boot_to_game with long stage timeouts); regions get the pattern at the handover."""
    g = (GAME / game).resolve()
    orig = hunter.build_hd
    hunter.build_hd = lambda img, **k: orig(img, game=g, **k)
    h = Hunter(machine=machine, tos=hunter.TOS[tos], memsize_kb=mem, extra=extra, bus=bus)
    hunter.build_hd = orig
    stage = h._stage
    h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
    if regions:
        arm_pattern(h, regions, HD_START)
    if boot:
        if blind:
            huntpatch.blind_boot(h)
        else:
            h.boot_to_game()
    return h


def changed(d: bytes, regions):
    """Pattern bytes that differ in the dump: list of runs [lo, hi]."""
    runs = []
    for lo, hi in regions:
        for a in range(lo, hi):
            if a < len(d) and d[a] != huntpatch.fill_byte(a):
                if runs and a - runs[-1][1] <= 1:
                    runs[-1][1] = a
                else:
                    runs.append([a, a])
    return runs


def check(h, regions, size=0x100000, tag="", show=12):
    out = h.R / "dump.bin"
    h.dump(str(out), 0, size)
    d = out.read_bytes()
    runs = changed(d, regions)
    n = sum(b - a + 1 for a, b in runs)
    tot = sum(hi - lo for lo, hi in regions)
    print(f"[{tag}] {tot} pattern bytes in {', '.join(f'${lo:x}-${hi - 1:x}' for lo, hi in regions)}: {n} changed, {len(runs)} runs")
    for lo, hi in regions:
        k = sum(max(0, min(b, hi - 1) - max(a, lo) + 1) for a, b in runs)
        print(f"    ${lo:06x}-${hi - 1:06x}: {k} of {hi - lo} changed")
    for a, b in runs[:show]:
        print(f"    ${a:06x}..${b:06x} ({b - a + 1} B)")
    return d, runs


def trace_loads(h, log=None):
    """Arm a persistent breakpoint at the game's file hook `$150`: every call logs d0 (file digit) and a0 (destination)."""
    cf = h.R / "ld.txt"
    cf.write_text("r\n")
    h.cmd(f"hatari-debug b pc = $150 :trace :file {cf}")


def loads_from_log(h):
    txt = h._logtext()
    out = []
    for blk in txt.split("CPU breakpoint condition(s) matched")[1:]:
        if "pc = $150" not in blk and "$150" not in blk[:200]:
            continue
        m0 = re.search(r"D0[: ]+\s*([0-9A-Fa-f]{8})", blk)
        ma = re.search(r"A0[: ]+\s*([0-9A-Fa-f]{8})", blk)
        if m0 and ma:
            out.append((int(m0.group(1), 16), int(ma.group(1), 16)))
    return out


# ---- CLI ------------------------------------------------------------------------------------------------------------
def parse_regions(args):
    out = []
    for r in args:
        lo, _, hi = r.partition(":")
        out.append((int(lo, 16), int(hi, 16)))
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["hd", "fl"])
    ap.add_argument("--region", nargs="*", default=["81000:8BA00"], help="LO:HI hex pairs filled with the pattern at pc=$800")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--game", default="build/tb_hd")
    ap.add_argument("--disk1", default="build/tb_fl/HUNTER_disk1.st")
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--play", type=float, default=25)
    ap.add_argument("--keys", default="", help="extra in-game keys to tap, comma separated")
    ap.add_argument("--dump", default=None)
    ap.add_argument("--size", type=lambda x: int(x, 16), default=0x100000, help="RAM bytes to dump for the check (hex)")
    ap.add_argument("--hatari-opt", default="")
    a = ap.parse_args()
    REG = parse_regions(a.region)
    extra = a.hatari_opt.split()
    t = time.time()
    h = None
    try:
        if a.cmd == "hd":
            h = boot_hd(game=a.game, mem=a.mem, machine=a.machine, tos=a.tos, regions=REG, extra=extra or None, blind=a.blind)
        else:
            import huntfloppy
            h = huntfloppy.HunterFloppy(GAME / a.disk1, None, drives=1, machine=a.machine, tos=TOS[a.tos],
                                        memsize_kb=a.mem, extra=extra or None)
            stage = h._stage
            h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
            arm_pattern(h, REG, FL_START)
            h.boot_floppy("none", blind=a.blind)
        ok = h.in_game()
        print(f"BOOT {'OK' if ok else 'FAILED'} in {time.time() - t:.0f} s  region={["$%x-$%x" % (lo, hi - 1) for lo, hi in REG]}")
        if a.play:
            h.hold("Up", "Left")
            time.sleep(a.play)
            h.release("Up", "Left")
            time.sleep(1)
            print(f"  after {a.play} s Up+Left: in_game={h.in_game()}")
        for k in filter(None, a.keys.split(",")):
            h.key(k, 0.2)
            time.sleep(3)
        d, runs = check(h, REG, size=a.size, tag=f"{a.cmd}/{a.machine}/{a.tos}/{a.mem}K")
        if a.dump:
            Path(a.dump).write_bytes(d)
            print(f"  dump {a.dump}")
        return 0 if not runs else 1
    finally:
        if h is not None:
            h.close()


if __name__ == "__main__":
    sys.exit(main())
