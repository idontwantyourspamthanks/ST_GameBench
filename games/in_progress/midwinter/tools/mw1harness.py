#!/usr/bin/env python3
"""Midwinter 1 (HAGA HD version) navigation on top of tools/stharness.Hatari.

    import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, '<gamebench>/games/in_progress/midwinter/tools')
    from mw1harness import MW1
    h = MW1(game_dir=..., memsize_kb=1024)      # cold boot (autoruns C:\\RUNME.TOS)
    h.boot_to_options(); h.options_to_team()
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from stharness import Hatari, TOS  # noqa: E402,F401  (TOS re-exported to the cell scripts)

REF = GAME / "work" / "ref"
OPTIONS_BOX = (250, 325, 580, 450)      # exact match of work/ref/options_play.png on the Game Options screen
PLAY_XY = (415, 385)


class MW1(Hatari):
    def __init__(self, game_dir=GAME, **kw):
        super().__init__(game_dir=game_dir, **kw)

    def matches(self, ref: Path, box) -> bool:
        """screen_matches with a retry: Hatari can still be writing the screenshot PNG."""
        for _ in range(4):
            try:
                return self.screen_matches(ref, box)
            except Exception:
                time.sleep(1)
        return False

    def at_options(self) -> bool:
        return self.matches(REF / "options_play.png", OPTIONS_BOX)

    def boot_to_options(self, timeout: float = 150, first_wait: float = 25) -> bool:
        """Cold boot: HW screen, intro picture, logo, 'identification' page, Game Options.
        Space is pressed between polls (the HW screen and the intro pictures take it)."""
        time.sleep(first_wait)
        t = time.time()
        while time.time() - t < timeout:
            if self.at_options():
                return True
            self.keypress(57)
            time.sleep(4)
        return False

    def options_to_team(self, ref: Path | None = None, box=(0, 0, 0, 0), timeout: float = 60) -> bool:
        """Click PLAY on the Game Options screen. With `ref`/`box` poll for the Team screen,
        else just wait 12 s."""
        self.goto(*PLAY_XY)
        self.click()
        if ref is None:
            time.sleep(12)
            return True
        t = time.time()
        while time.time() - t < timeout:
            if self.matches(ref, box):
                return True
            time.sleep(2)
        return False

    def apply_live(self, prefix: str | Path):
        """Apply a `mw1patch.py live` patch set to a running (snapshot-restored) game: the payload image
        at $B3000 (loadbin) and every site's new bytes (debugger `w`).  Returns the site list."""
        prefix = str(prefix)
        spec = json.loads(Path(prefix + ".json").read_text())
        img = self.R / "p.img"                       # short path: long debugger command lines are truncated
        shutil.copy(prefix + ".img", img)
        self.debug(f"loadbin {img} ${spec['img_base']:x}", wait=1.5)
        for s in spec["sites"]:
            b = bytes.fromhex(s["new"])
            self.debug("w $%x %s" % (s["addr"], " ".join("$%02x" % x for x in b)))
        return spec["sites"]
