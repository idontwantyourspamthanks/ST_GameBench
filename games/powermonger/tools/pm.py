#!/usr/bin/env python3
"""Powermonger (floppy, disks/protected.st) navigation + state access on top of tools/stharness.Hatari.

    import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, '<gamebench>/games/powermonger/tools')
    from pm import PM
    h = PM(); h.boot_to_game(); h.savemem(...); h.close()
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent / "tools"))
from stharness import Hatari, TOS, retarget_snapshot  # noqa: E402,F401

DISK = GAME / "disks" / "protected.st"
SNAP = GAME / "work" / "snapshots"
REF = GAME / "work" / "ref"


class PM(Hatari):
    def __init__(self, snapshot: str | None = None, workdir: str | None = None, disk: Path = DISK,
                 cpuclock: int | None = None, **kw):
        R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
        R.mkdir(parents=True, exist_ok=True)
        # private floppy copy (the game may write to it) and a private Hatari config whose
        # memstate-capture path is this run's own file (the stock one is the shared /tmp/hatari.sav)
        a = R / "a.st"
        shutil.copy(disk, a)
        home = R / "home"
        (home / ".config/hatari").mkdir(parents=True, exist_ok=True)
        txt = (Path.home() / ".config/hatari/hatari.cfg").read_text()
        txt = re.sub(r"(?m)^szMemoryCaptureFileName = .*$", f"szMemoryCaptureFileName = {R}/state.sav", txt)
        (home / ".config/hatari/hatari.cfg").write_text(txt)
        kw.setdefault("files", [])
        kw.setdefault("overlay", Path("/nonexistent"))
        kw.setdefault("autorun", None)
        extra = ["--disk-a", str(a), "--protect-floppy", "off"] + list(kw.pop("extra", []))
        if snapshot:
            snap_in = R / "snap_in.sav"
            retarget_snapshot(snapshot, snap_in, R)
            snapshot = str(snap_in)
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(home)       # Hatari reads $HOME/.config/hatari/hatari.cfg
        try:
            super().__init__(game_dir=GAME, snapshot=snapshot, workdir=str(R), extra=extra, **kw)
        finally:
            os.environ["HOME"] = old_home
        if not snapshot:
            self.state = R / "state.sav"
        if cpuclock:
            self.set_cpuclock(cpuclock)


# ---- RAM map (1 MB STE, TOS 1.62, protected.st; evidence in work/notes/*.md) ---------------------
MOUSE_X, MOUSE_Y = 0x1C492, 0x1C494        # words: pointer in ST low-res pixels (320x200), 2 host px per ST px
ITER = 0x2DF70                             # long: main-loop iteration counter, cleared at game start ($13baa)
VBLCNT = 0x6F304                           # long: VBL handler tick count ($1286)
SCREENS = (0x2DF7C, 0x2DF78)               # longs: the two screen buffers; $187a swaps them and writes $ff8200
PROT_TYPE = 0x57FF8                        # word: protection question (0 = houses, 1 = people)
PROT_ANS = 0x5878E                         # words: expected answers, [PROT_TYPE] -> houses, people, ...
PEOPLE, PEOPLE_N, PEOPLE_STRIDE = 0x51B66, 512, 0x32
CAPTAINS, CAPTAINS_N, CAPTAINS_STRIDE = 0x4E514, 160, 0x20

# screen coordinates in ST low-res pixels (x, y), measured from screenshots
START_NEW_XY = (160, 85)                   # option screen: START NEW CONQUEST
ISLAND_XY = (20, 18)                       # territory chart: the island in the top-left corner
PROT_UP_Y, PROT_DIGIT_X, PROT_OK_XY = 170, (41, 45, 49, 53), (19, 176)
POSTURE3_XY = (97, 158)                    # command panel: 3-sword icon (aggressive posture)
GETMEN_XY = (229, 173)                     # command panel: get men

# gates: (reference crop in work/ref, box in 832x588 screenshot coordinates)
GATES = {
    "name": ("name_title.png", (330, 233, 532, 248)),
    "options": ("opt_title.png", (336, 148, 496, 172)),
    "chart": ("chart.png", (296, 158, 596, 358)),
    "prot": ("prot_bottom.png", (106, 358, 286, 438)),
    "game": ("game_hud.png", (96, 378, 346, 458)),
}


def _methods():
    def at(self, gate: str, tol: float = 6.0) -> bool:
        ref, box = GATES[gate]
        return self.screen_matches(REF / ref, box, tol)

    def mpos(self):
        return self.peekw(MOUSE_X), self.peekw(MOUSE_Y)

    def goto_st(self, x: int, y: int, tol: int = 1):
        """Move the pointer to ST pixel (x, y): home it, then close the loop on the pointer RAM words."""
        self.home()
        for _ in range(5):
            cx, cy = self.mpos()
            dx, dy = x - cx, y - cy
            if abs(dx) <= tol and abs(dy) <= tol:
                break
            self.rel(dx * 2, dy * 2, max(2, min(10, (abs(dx) + abs(dy)) // 4 + 1)))
            time.sleep(0.3)
        return self.mpos()

    def click_st(self, x: int, y: int, hold: float = 0.2, wait: float = 1.0):
        p = self.goto_st(x, y)
        self.click(hold=hold)
        time.sleep(wait)
        return p

    def wait_gate(self, gate: str, timeout: float, poll: float = 3.0, act=None) -> bool:
        t = time.time()
        while time.time() - t < timeout:
            if self.at(gate):
                return True
            if act:
                act()
            time.sleep(poll)
        return False

    def iter_count(self) -> int:
        return self.peekl(ITER)

    def in_game(self) -> bool:
        """3D map view marker: the game HUD is on screen AND the main loop is iterating ($2df70 grows)."""
        a = self.iter_count()
        time.sleep(1.5)
        return self.at("game") and self.iter_count() > a

    def protection_answer(self) -> tuple[int, int]:
        t = self.peekw(PROT_TYPE)
        return t, self.peekw(PROT_ANS + 2 * t)

    def boot_to_game(self, name: str = "Bench", skip_key: str = "space", log=print, t_name: float = 400,
                     check: bool = True) -> bool:
        """Cold boot -> intro (skipped with `skip_key`) -> name prompt -> option screen -> START NEW CONQUEST ->
        territory chart -> the top-left island -> protection question (answer read from RAM) -> 3D map view.
        Every stage waits for its screenshot gate; nothing depends on a fixed delay."""
        t0 = time.time()
        stamp = lambda s: log(f"[{time.time() - t0:5.0f}s vbl {self.vbl()}] {s}")
        time.sleep(15)
        if not self.wait_gate("name", t_name, 4.0, act=lambda: self.key(skip_key)):
            raise RuntimeError("name prompt not reached")
        stamp("name prompt")
        time.sleep(1.0)
        for ch in name:
            self.key(ch)
            time.sleep(0.25)
        self.key("Return")
        if not self.wait_gate("options", 40, 2.0):
            raise RuntimeError("option screen not reached")
        stamp("option screen")
        self.click_st(*START_NEW_XY, wait=2.0)
        if not self.wait_gate("chart", 60, 2.0):
            raise RuntimeError("territory chart not reached")
        stamp("territory chart")
        self.click_st(*ISLAND_XY, wait=1.0)
        if not self.wait_gate("prot", 120, 3.0):
            raise RuntimeError("protection question not reached")
        stamp("protection question")
        typ, ans = self.protection_answer()
        digits = [(ans // 1000) % 10, (ans // 100) % 10, (ans // 10) % 10, ans % 10]
        for x, n in zip(PROT_DIGIT_X, digits):
            if n:
                self.goto_st(x, PROT_UP_Y)
                for _ in range(n):
                    self.click(hold=0.15)
                    time.sleep(0.4)
        stamp(f"protection answer type {typ} value {ans}")
        self.click_st(*PROT_OK_XY, wait=2.0)
        if not self.wait_gate("game", 90, 3.0):
            raise RuntimeError("3D map view not reached")
        if check and not self.in_game():
            raise RuntimeError("HUD visible but main loop not iterating")
        stamp("3D map view")
        return True

    for f in (at, mpos, goto_st, click_st, wait_gate, iter_count, in_game, protection_answer, boot_to_game):
        setattr(PM, f.__name__, f)


_methods()
