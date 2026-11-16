#!/usr/bin/env python3
"""Moonshine Racers (PP's HAGA HD conversion) harness on top of tools/stharness.Hatari.

    import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, '<game>/tools')
    from msr import Moonshine
    h = Moonshine()          # cold boot STE TOS 1.62 1 MB, autorun RUNME.TOS (game_dir = originals/MOONSHR)
"""
from __future__ import annotations
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
from stharness import Hatari   # noqa

ORIG = GAME / "originals" / "MOONSHR"
SNAP = GAME / "work" / "snapshots"
SHOTS = GAME / "work" / "shots"


class Moonshine(Hatari):
    def __init__(self, snapshot=None, game_dir=None, **kw):
        """game_dir: the game folder copied to the scratch drive (default originals/MOONSHR; a patched build: build/<name>)."""
        kw.setdefault("memsize_kb", 1024)
        super().__init__(game_dir=game_dir or ORIG, snapshot=snapshot, **kw)

    # ---- state access --------------------------------------------------------------------------------------------
    def in_race(self) -> bool:
        """True once the race loop runs: the loop counter $100e advances while $1021 (mode byte; 2 = race) is 2."""
        return self.peekb(0x1021) == 2

    def peekb(self, addr: int) -> int:
        out = self.debug(f"m ${addr:x} 1", 0.6)
        return int(re.findall(rf"{addr:08x}:\s+([0-9a-f]{{2}})", out, re.I)[-1], 16)

    def boot_to_race(self, timeout: float = 400, log=print, shots: str | None = None) -> bool:
        """Cold boot -> HW-detect screen -> cover -> intro animation -> (SPACE x N through the text/title/map screens)
        -> the first race (a standing start, timer running; the car does not move until the joystick is pushed).
        Recipe (VBL counts at 8 MHz STE, 1 MB): HW screen at ~VBL 300-900, cover picture ~1000-2500 (PP's slideshow,
        times out by itself), sunrise intro animation ~2700-5000, then each SPACE advances one screen:
        'Welcome partners' text -> title + 'Hi I'm Ike' -> map 'Cactus Creek!' -> race."""
        t0 = time.time(); n = 0
        while time.time() - t0 < timeout:
            time.sleep(4)
            v = self.vbl()
            try:
                st = (self.peekb(0x1021), self.peekw(0x100E))
            except Exception:
                st = None
            log(f"t={time.time() - t0:5.0f}s vbl={v} $1021/$100e={st}")
            if shots:
                self.shot(f"{shots}_{n:02d}.png")
            n += 1
            if v > 5000:
                if st and st[0] == 2 and st[1] > 40:
                    return True
                self.keypress(57)          # SPACE
        return False

    def drive(self, on: bool = True):
        """Hold 'up' (accelerate) by writing the game's joystick-port-1 byte $6105 directly (bit0 up, bit1 down, bit2 left,
        bit3 right, bit7 fire); the IKBD handler $cfb4 stores the last joystick packet there, so a debugger write is a
        deterministic, replayable input (a held host key is not)."""
        self.debug(f"w $6105 ${1 if on else 0:02x}")


# ---- measurement helpers (module level so scripts can share them) ------------------------------------------------
import re

FLIP_PC = 0xD1CA          # page-flip routine ($d1ca: swap $1004/$1008, write $ff8200); one call = one presented frame


def flips_pc(h, vbls=250, pc=FLIP_PC):
    """Count executions of `pc` (default: the game flip routine) over `vbls` VBLs with a trace breakpoint."""
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${pc:x} :trace")
    time.sleep(0.3)
    start = h._arm_vbl(vbls)
    out = h._wait_removed(start)
    h.debug("b all", 0.3)
    n = out.count(f"pc = ${pc:x} :trace")
    return {"vbls": vbls, "flips": n, "fps": n * 50.0 / vbls, "vbl_per_frame": vbls / n if n else None}


WORLD = {"pos5ff8": 0x5FF8, "speed130c": 0x130C, "frame100e": 0x100E, "dist11c2": 0x11C2}


def peeks(h, names=WORLD):
    return {n: h.peekw(a) for n, a in names.items()}


def prof(h, vbls, out):
    """Hatari CPU profile -> `profile save` file `out` (lines: $addr insn pct% (count, cycles, imiss, dhit)). Returns log."""
    end = h.R / "prof_end.txt"
    end.write_text(f"profile stats\nprofile save {out}\n")
    start = h._arm_vbl(vbls + 25, f" :file {end}")
    time.sleep(0.3)
    h.cmd("hatari-debug profile on")
    o = h._wait_removed(start)
    time.sleep(1.5)
    return o
