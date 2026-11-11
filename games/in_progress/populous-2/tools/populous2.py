#!/usr/bin/env python3
"""Populous 2 (PP HAGA). Needs 2 MB. Evidence: work/notes/boot.md.

The flyover polls $fffc02 for scancode $39 while TOS still owns the ACIA
vector, so a keypress never arrives. boot_to_game() writes that byte from
the debugger, which is what left the flyover in the study run.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from stharness import Hatari  # noqa: E402


class Populous2(Hatari):
    def __init__(self, **kw):
        kw.setdefault("game_dir", GAME / "originals" / "POPUL2")
        kw.setdefault("memsize_kb", 2048)
        kw.setdefault("overlay", Path("/nonexistent"))
        super().__init__(**kw)

    def in_play(self) -> bool:
        """VBL installed at $2e9b4 (st.b $345bb) and the screen at $f0000."""
        b = self.debug("m $2e9b4 2", 0.5)
        return "50 f9" in b.lower() and (self.peekw(0xFF8200) & 0xFF) == 0x0F

    def _space_byte(self, n: int = 6) -> None:
        for _ in range(n):
            self.debug("w $fffc02 $39", 0.15)
        self.debug("w $fffc02 $00", 0.2)

    def boot_to_game(self) -> bool:
        time.sleep(14)
        self.keypress(57)
        time.sleep(18)
        self._space_byte(10)
        time.sleep(2)
        self._space_byte(30)
        time.sleep(3)
        return self.in_play()
