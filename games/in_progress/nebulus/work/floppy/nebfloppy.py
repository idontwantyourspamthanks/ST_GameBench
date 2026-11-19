#!/usr/bin/env python3
"""Nebulus floppy harness: Hatari booted from a LONE floppy image (--disk-a), real FDC timing (--fastfdc no),
no GEMDOS hard drive. Subclasses stharness.Hatari; tools/nebulus.py is not touched.

    from nebfloppy import NebFloppy
    h = NebFloppy("disk.st"); h.boot_to_title(); h.close()
"""
from __future__ import annotations
import sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
from stharness import Hatari, TOS  # noqa: E402

TOSNAME = {"ste": "1.62", "st": "1.04", "megaste": "2.06"}


class NebFloppy(Hatari):
    TIMER = 0x3AD74                  # floppy address (PP's HD build: $3ad98); same game, -36 bytes after text offset $4c46
    VBLV = 0x70
    TOWER = 0x3390C

    def __init__(self, disk, machine="ste", mem=1024, tos=None, workdir=None, extra=None, trace=None, fastfdc=False):
        ex = ["--disk-a", str(Path(disk).resolve()), "--fastfdc", "yes" if fastfdc else "no", "--joy1", "keys"]
        if trace:
            ex += ["--trace", trace]
        ex += extra or []
        super().__init__(game_dir=GAME / "alt/floppy", machine=machine, memsize_kb=mem,
                         tos=TOS[tos or TOSNAME[machine]], autorun=None, files=[], overlay=Path("/nonexistent"),
                         workdir=workdir, extra=ex)

    def peekb(self, a):
        import re
        out = self.debug(f"m ${a:x} 1", 0.5)
        return int(re.findall(rf"{a:08x}:\s+([0-9a-f]{{2}})", out, re.I)[-1], 16)

    def vbl_vec(self):
        import re
        out = self.debug("m $70 4", 0.4)
        m = re.findall(r"00000070:\s+([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2})", out, re.I)
        return int("".join(m[-1]), 16) if m else 0

    def boot_to_title(self, timeout=200.0, space_at=20.0, settle=3.0):
        """The Atari Legend intro waits for a key (one space at `space_at` s); the game is up when the VBL vector is the game's ($382d8)."""
        t0 = time.time(); pressed = False
        while time.time() - t0 < timeout:
            time.sleep(2)
            if not pressed and time.time() - t0 >= space_at:
                self.key("space", hold=0.6); pressed = True
            if pressed and self.vbl_vec() == 0x382D8:
                time.sleep(settle)
                return time.time() - t0
        return False

    def boot_to_game(self, timeout=200.0, settle=2.0):
        t = self.boot_to_title(timeout)
        if not t:
            return False
        time.sleep(settle)
        self.key("Right", hold=0.5); time.sleep(0.5)
        self.key("Control_R", hold=1.0); time.sleep(4.0)
        return bool(self.peekw(self.TIMER))
