#!/usr/bin/env python3
"""Populous 2 (PP HAGA) on the Hatari harness. Needs 2 MB. Evidence: work/notes/baseline.md, ui.md.

    from populous2 import Populous2
    h = Populous2(snapshot=Populous2.SNAP / "busy1.sav")
    print(h.world_rate(Populous2.TURN, 500))

boot_to_game() cold boots to the first conquest battle (re-run on the patched build, 2 MB STE, 2026-11-11).
Keys must be HELD (the intro and the game read them once per VBL or per pass).
Populous2(game_dir=<build/hd>) runs a patched build; marker() reads pop2patch's marker.
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

    def marker(self) -> str:
        """pop2patch's marker at $7fff8: 'P2PO' = every patch applied, 'P2PF' = a site mismatched, else not delivered."""
        w = self.peekl(0x7FFF8)
        return w.to_bytes(4, "big").decode("latin1") if w else ""

    def boot_to_menu(self, timeout: float = 240) -> bool:
        """Cold boot to the stone-framed main menu: hold Space once per screen (PP's hardware screen, the cover
        picture, the Bullfrog logo, the credits - each reads the key once per VBL, so it must be HELD) until the
        game's VBL ($70 = $18fa) is installed.  State-driven: no fixed waits except the first 14 s."""
        t0 = time.time()
        time.sleep(14)
        while time.time() - t0 < timeout:
            self.key("space", 0.6)
            time.sleep(6)
            if self.peekl(0x70) == 0x18FA:
                time.sleep(3)
                return True
        return False

    def boot_to_game(self, name: str = "zeus", timeout: float = 240) -> bool:
        """boot_to_menu(), then the first conquest battle (re-run 2026-11-11 on the patched build, 2 MB STE):
        CONQUEST opens the deity screen, name + Return, PROCEED (back to the menu), CONQUEST, PROCEED on the
        battle sheet, the manual question's OK (any answer is accepted, PP's $14a88 patch)."""
        if not self.boot_to_menu(timeout):
            return False
        self._click(384, 257, 3)            # CONQUEST GAME: first time opens the deity screen
        self._click(260, 98, 1.0)           # name field
        for ch in name:
            self.key(ch, 0.3)
            time.sleep(0.4)
        self.key("Return", 0.3)
        time.sleep(1.0)
        self._click(424, 418, 3)            # PROCEED (reacts on its text row) -> main menu
        self._click(384, 258, 8)            # CONQUEST GAME -> battle sheet
        self._click(216, 448, 12)           # PROCEED (ST (60,195)); loads
        self._click(400, 420, 15)           # manual question: OK with 0000 is accepted
        return self.in_play()
