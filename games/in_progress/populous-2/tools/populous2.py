#!/usr/bin/env python3
"""Populous 2 (PP HAGA) on the Hatari harness. Needs 2 MB. Evidence: work/notes/baseline.md, ui.md.

    from populous2 import Populous2
    h = Populous2(snapshot=Populous2.SNAP / "busy1.sav")
    print(h.world_rate(Populous2.TURN, 500))

boot_to_game() replays the inputs that reached the game once in the study run
(2026-11-11); it has not been re-run since it was written down. Keys must be
HELD (the intro and the game read them once per VBL or per pass).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from stharness import Hatari  # noqa: E402

HOME = (96, 58)     # screenshot pixel of ST (0,0); home() leaves the pointer there


class Populous2(Hatari):
    SNAP = GAME / "work" / "snapshots"
    TURN = 0x3979C              # low word of the turn long $3979a (+1 per pass, $22f9c)
    MOUSE_X, MOUSE_Y = 0x393FA, 0x393FC
    LEFT_CLICK, RIGHT_CLICK = 0x39402, 0x39404
    VIEW_X, VIEW_Y = 0x3E79E, 0x3E7A0
    MODE = 0x47372

    def __init__(self, **kw):
        kw.setdefault("game_dir", GAME / "originals" / "POPUL2")
        kw.setdefault("memsize_kb", 2048)
        kw.setdefault("overlay", Path("/nonexistent"))
        kw.setdefault("flip_reg", "($ff8203).b")    # buffers $2300 / $a000 differ in the middle byte
        if kw.get("snapshot"):
            kw["snapshot"] = str(kw["snapshot"])
        super().__init__(**kw)

    def in_play(self) -> bool:
        """The game's VBL is installed ($70 = $18fa) and the turn counter moves."""
        if self.peekl(0x70) != 0x18FA:
            return False
        t = self.peekw(self.TURN)
        time.sleep(1.5)
        return self.peekw(self.TURN) != t

    def _click(self, x: int, y: int, wait: float = 4.0) -> None:
        self.goto(x, y, home_xy=HOME)
        self.click(hold=0.4)
        time.sleep(wait)

    def boot_to_game(self, name: str = "zeus") -> bool:
        time.sleep(14)
        self.key("space", 0.6)              # PP's hardware screen
        time.sleep(30)                      # cover, Bullfrog logo scroller
        self.key("space", 0.6)              # -> credits
        time.sleep(8)
        self.key("space", 0.6)              # -> main menu
        time.sleep(25)
        self._click(384, 257)               # CONQUEST GAME: first time opens the deity screen
        self._click(260, 98, 1.0)           # name field
        for ch in name:
            self.key(ch, 0.3)
            time.sleep(0.4)
        self.key("Return", 0.3)
        time.sleep(1.0)
        for xy in ((470, 418), (380, 410), (424, 426)):   # PROCEED reacts on its text row
            self._click(*xy, 2.5)
        self._click(384, 258, 8)            # CONQUEST GAME -> battle sheet
        self._click(216, 448, 12)           # PROCEED (ST (60,195)); loads
        self._click(400, 420, 15)           # manual question: OK with 0000 is accepted
        return self.in_play()
