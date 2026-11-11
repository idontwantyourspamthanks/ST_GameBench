#!/usr/bin/env python3
"""Populous (PP HAGA) on the Hatari harness. Evidence: work/notes/boot.md.

    import sys
    sys.path.insert(0, "<gamebench>/tools")
    sys.path.insert(0, "<gamebench>/games/in_progress/populous/tools")
    from populous import Populous
    h = Populous(memsize_kb=1024)
    h.boot_to_game()
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from stharness import Hatari  # noqa: E402

# Screenshot pixels, home_xy (96, 58). Recorded from the run that reached the map.
CONQUEST_XY = (641, 407)
START_XY = (254, 408)
HOME = (96, 58)


class Populous(Hatari):
    def __init__(self, **kw):
        kw.setdefault("game_dir", GAME / "originals" / "POPULOUS")
        kw.setdefault("memsize_kb", 1024)
        kw.setdefault("overlay", Path("/nonexistent"))
        super().__init__(**kw)

    def in_play(self) -> bool:
        """Screen at $40000 and the frame spin at $1d02a (move.w $3d566,d0)."""
        b = self.debug("m $1d02a 2", 0.5)
        return "30 39" in b and (self.peekw(0xFF8200) & 0xFF) == 0x04

    def boot_to_game(self) -> bool:
        time.sleep(16)
        self.keypress(57)          # hardware screen
        time.sleep(20)             # logo and the book; a click during the black load is lost
        self.goto(*CONQUEST_XY, home_xy=HOME)
        self.click()
        time.sleep(8)
        self.goto(*START_XY, home_xy=HOME)
        self.click()
        time.sleep(8)
        return self.in_play()
