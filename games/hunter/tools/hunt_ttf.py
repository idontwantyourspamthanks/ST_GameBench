#!/usr/bin/env python3
r"""Hunter on TT (TOS 3.06) and Falcon (TOS 4.04) in Hatari: cold-boot cells.  Results: work/notes/ttfalcon.md.

    python3 tools/hunt_ttf.py CELL --machine tt  [--game build/ttf_hd | --floppy build/ttf_fl/HUNTER_disk1.st]
                              [--tos 3.06] [--mem 4096] [--bus acsi|scsi|ide] [--poke-mch 0x20000]
                              [--hatari-opt OPT ...] [--play SECONDS] [--shots DIR] [--peek ADDR:LEN ...]

Harness facts this file encodes (all observed, see the note):
  * a TT/Falcon CPU "halted: double bus error" dialog blocks Hatari's command fifo for good ("no screenshot");
    `Hatari.alive()` therefore times out instead of waiting.
  * the Falcon shot is 648 x 602 (picture at 2,64); the TT shot is 640 x 436 (picture at 0,0, statusbar below).
  * HD builds: TT = ACSI image + HDDRIVER (TOS 3.06 boots it).  Falcon = IDE image; HDDRIVER 10.15 does not find
    Hatari's IDE drive (work/notes/ttfalcon.md section 3).
  * `--poke-mch`: the UNPATCHED game's own cookie jar says _MCH = Falcon ($00030000); the second HDDRIVER that START
    runs trusts it and skips ACSI on a TT.  The poke writes the real value into the jar just before START runs the
    root sector (debugger breakpoint at START's `jsr (a0)`; START's base is found by scanning RAM for its signature).
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
import hunter  # noqa: E402
from hunter import Hunter, TOS  # noqa: E402
from huntfloppy import HunterFloppy  # noqa: E402

START_SIG = bytes.fromhex("4e907e1c3f3c00254e4e548f51cffff6")    # START text $590: jsr (a0) / moveq #$1c,d7 / Vsync loop
START_SIG_OFF = 0x590
JAR_MCH_VALUE = 0xD0EE8                                           # D15R_F5.FIC cookie jar $d0edc: _CPU,$1e, _MCH,$00030000
MARKER, FLAGS = 0x8BFF8, 0x8BFF0


def find_start_base(h, lo=0, n=0x100000) -> int | None:
    p = h.R / "ramscan.bin"
    h.dump(str(p), lo, n)
    time.sleep(0.5)
    i = p.read_bytes().find(START_SIG)
    return None if i < 0 else lo + i - START_SIG_OFF


def arm_mch_poke(h, mch: int) -> int:
    """Write `mch` into the game's jar the moment START is about to run the root sector.  Returns START's base."""
    base = find_start_base(h)
    if base is None:
        raise RuntimeError("START signature not found in RAM (HW screen not reached?)")
    cf = h.R / "mch.txt"
    cf.write_text(f"w ${JAR_MCH_VALUE:x} " + " ".join(f"${(mch >> s) & 255:02x}" for s in (24, 16, 8, 0)) + "\n")
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${base + START_SIG_OFF:x} :trace :once :file {cf}")
    time.sleep(0.4)
    return base


def alive(h, timeout: float = 8) -> bool:
    """False if Hatari does not answer (e.g. the 'CPU halted' dialog is up)."""
    try:
        h.shot()
        return True
    except RuntimeError:
        t = time.time()
        while time.time() - t < timeout:
            time.sleep(1)
            try:
                h.shot()
                return True
            except RuntimeError:
                pass
        return False


class HD(Hunter):
    """Hunter HD build on TT/Falcon (screenshot origins are handled by stharness.Hatari.screen_matches)."""


def boot_hd(machine: str, tos: str, mem: int, game: Path, bus: str | None, poke_mch: int | None, opts: list[str],
            play: float, shots: Path | None, peeks: list[str], title_wait: float = 150, log=print) -> int:
    orig_build = hunter.build_hd
    hunter.build_hd = lambda img, **k: orig_build(img, game=game, **k)
    h = None
    t0 = time.time()
    try:
        h = HD(machine=machine, tos=TOS[tos], memsize_kb=mem, bus=bus, extra=opts)
        time.sleep(10)
        if poke_mch is not None:
            base = arm_mch_poke(h, poke_mch)
            log(f"START base ${base:x}; _MCH poke ${poke_mch:x} armed")
        h.keypress(57)
        time.sleep(3)
        for stage, wait in (("title2", title_wait),):
            if not h.wait_stage(stage, wait, 2):
                raise RuntimeError(f"screen {stage} not reached")
        log(f"title after {time.time() - t0:.0f} s")
        time.sleep(1.5)
        h.key("space", 0.3)
        if not h.wait_stage("main", 40, 2):
            raise RuntimeError("main not reached")
        h.goto(*h.START_XY, home_xy=h.HOME_XY)
        h.click()
        if not h.wait_stage("games", 30, 2):
            raise RuntimeError("games not reached")
        h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
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
        ok = h.in_game()
        mk, fl = h.peek(MARKER, 4), h.peek(FLAGS, 4)
        log(f"BOOT {'OK' if ok else 'FAILED'} machine={machine} tos={tos} mem={mem}K bus={bus} game={game.name} in_game={ok} "
            f"MARKER={mk!r} FLAGS={fl.hex()} fps={h.fps(250)['fps']:.2f}  ({time.time() - t0:.0f} s)")
        for pk in peeks:
            a, _, n = pk.partition(":")
            aa = int(a.lstrip("$"), 16)
            log(f"  peek ${aa:x}: {h.peek(aa, int(n or 8)).hex()}")
        if play:
            h.hold("Up", "Left")
            time.sleep(play)
            h.release("Up", "Left")
            log(f"  after {play:.0f} s of Up+Left: in_game={h.in_game()}")
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            h.shot(str(shots / f"{machine}_{tos}_{game.name}.png"))
        return 0 if ok else 1
    except Exception as e:  # noqa: BLE001
        log(f"BOOT FAILED machine={machine} tos={tos} mem={mem}K game={game.name}: {e!r}  alive={h is not None and alive(h, 3)}")
        if h is not None and shots:
            shots.mkdir(parents=True, exist_ok=True)
            try:
                h.shot(str(shots / f"{machine}_{tos}_{game.name}_fail.png"))
            except Exception:  # noqa: BLE001
                pass
        return 1
    finally:
        hunter.build_hd = orig_build
        if h is not None:
            h.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--machine", default="tt")
    ap.add_argument("--tos", default="3.06")
    ap.add_argument("--mem", type=int, default=4096)
    ap.add_argument("--game", default=str(GAME), help="HD build dir (default: the original game)")
    ap.add_argument("--bus", default=None)
    ap.add_argument("--poke-mch", default=None)
    ap.add_argument("--hatari-opt", default="", help='extra Hatari options as ONE string, e.g. --hatari-opt="--mmu true"')
    ap.add_argument("--play", type=float, default=0)
    ap.add_argument("--shots", default=None)
    ap.add_argument("--peek", nargs="*", default=[])
    ap.add_argument("--title-wait", type=float, default=150, help="seconds to wait for the animated title (a failing boot never gets there)")
    a = ap.parse_args()
    poke = int(a.poke_mch, 0) if a.poke_mch else None
    return boot_hd(a.machine, a.tos, a.mem, Path(a.game).resolve(), a.bus, poke, a.hatari_opt.split(), a.play,
                   Path(a.shots) if a.shots else None, a.peek, a.title_wait)


if __name__ == "__main__":
    sys.exit(main())
