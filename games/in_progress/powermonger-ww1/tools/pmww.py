#!/usr/bin/env python3
"""Powermonger WW1 (floppy, EA original or a patched .st) navigation + state access on top of tools/stharness.Hatari.

Modelled on games/done/powermonger/tools/pm.py.  Every instance gets a private HOME (Hatari config), a private copy of the
floppy and its own work dir; nothing of the real HOME is written.  Hatari binary: $HATARI, default ~/Code/AtariST/hattari/build/src/hatari.
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
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
os.environ.setdefault("HATARI", str(Path.home() / "Code/AtariST/hattari/build/src/hatari"))
from stharness import Hatari, TOS  # noqa: E402,F401

DISK = GAME / "disks" / "ea.st"


class PMW(Hatari):
    def __init__(self, disk: Path = DISK, workdir: str | None = None, cpuclock: int | None = None, **kw):
        R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
        R.mkdir(parents=True, exist_ok=True)
        a = R / "a.st"
        shutil.copy(disk, a)                       # the game may write to its disk
        home = R / "home"
        (home / ".config/hatari").mkdir(parents=True, exist_ok=True)
        txt = (Path(os.environ["HOME"]) / ".config/hatari/hatari.cfg").read_text()
        txt = re.sub(r"(?m)^szMemoryCaptureFileName = .*$", f"szMemoryCaptureFileName = {R}/state.sav", txt)
        (home / ".config/hatari/hatari.cfg").write_text(txt)
        kw.setdefault("files", [])
        kw.setdefault("overlay", Path("/nonexistent"))
        kw.setdefault("autorun", None)
        extra = ["--disk-a", str(a), "--protect-floppy", "off"] + list(kw.pop("extra", []))
        old_home = os.environ["HOME"]
        os.environ["HOME"] = str(home)             # Hatari reads $HOME/.config/hatari/hatari.cfg
        try:
            super().__init__(game_dir=GAME, snapshot=None, workdir=str(R), extra=extra, **kw)
        finally:
            os.environ["HOME"] = old_home
        self.state = R / "state.sav"
        self.disk_copy = a
        if cpuclock:
            self.set_cpuclock(cpuclock)

    def key(self, keysym: str, hold: float = 0.15):
        """Key press through XTEST (plain xdotool keydown/up).  The harness's `--window` variant (XSendEvent) was dropped by the game's
        name prompt in 2 of 3 cold boots tried (once typed, twice nothing); this one needs the window focused and the pointer inside it."""
        self._xdo("windowfocus", self.win)
        self._xdo("mousemove", "--window", self.win, "416", "294")
        time.sleep(0.1)
        self._xdo("keydown", keysym)
        time.sleep(hold)
        self._xdo("keyup", keysym)

    # ---- RAM -------------------------------------------------------------------------------------
    def ram(self, start: int = 0, length: int = 0x100000) -> bytes:
        out = self.R / "ram.bin"
        out.unlink(missing_ok=True)
        self.debug(f"savebin {out} ${start:x} ${length:x}", 0.5)
        for _ in range(100):
            if out.exists() and out.stat().st_size == length:
                break
            time.sleep(0.2)
        return out.read_bytes()

    # ---- pointer (ST low-res pixels; two host px per ST px) ---------------------------------------
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

    # ---- game state through the window text buffer ($7640..: the instance copy of the open window's text) ---------------
    def wtext(self) -> str:
        return "".join(chr(b) if 32 <= b < 127 else " " for b in self.ram(WTEXT, 0xC0))

    def wait_text(self, *subs: str, timeout: float = 60, poll: float = 1.0, act=None) -> bool:
        """Poll the window text until it contains every `subs` (case-insensitive)."""
        t = time.time()
        while time.time() - t < timeout:
            w = self.wtext().upper()
            if all(x.upper() in w for x in subs):
                return True
            if act:
                act()
            time.sleep(poll)
        return False

    def question_open(self) -> bool:
        return self.peekw(WINDOW_OPEN) != 0 and "BETWEEN PAGES" in self.wtext().upper()

    def wait_question(self, timeout: float) -> bool:
        t = time.time()
        while time.time() - t < timeout:
            if self.question_open():
                return True
            time.sleep(2)
        return False

    def swap_disk(self, path: Path):
        """Insert `path` in drive A: (the game asks for the original Powermonger disk and then for its own disk back)."""
        self.cmd(f"hatari-option --disk-a {path}")
        time.sleep(2.5)

    def counter(self) -> int:
        return self.peekl(ITER)

    def ticking(self, gap: float = 1.5) -> bool:
        a = self.counter()
        time.sleep(gap)
        return self.counter() > a

    def boot_to_options(self, name: str = "WWI", log=print, t_name: float = 120) -> bool:
        t0 = time.time()
        stamp = lambda s: log(f"[{time.time() - t0:5.0f}s vbl {self.vbl()}] {s}")
        if not self.wait_text("Powermonger WW1", timeout=t_name, poll=2):
            raise RuntimeError("name prompt not reached")
        stamp("name prompt")
        time.sleep(2.0)
        for attempt in range(6):
            for ch in name:
                self.key(ch)
                time.sleep(0.35)
            self.key("Return")
            if self.wait_text("Welcome to the World", timeout=12, poll=1):
                stamp(f"option screen (typing attempt {attempt + 1})")
                return True
            self.key("BackSpace")                 # nothing accepted: retry
        raise RuntimeError("option screen not reached")

    def boot_to_map(self, name: str = "WWI", log=print, swap: bool = True, noprot: bool = False) -> bool:
        """Cold boot -> name -> options -> map view (see options_to_map)."""
        t0 = time.time()
        self.boot_to_options(name, log)
        return self.options_to_map(log, swap, noprot, t0)

    def options_to_map(self, log=print, swap: bool = True, noprot: bool = False, t0: float | None = None) -> bool:
        """Option screen -> START NEW CONQUEST -> (the game's own disk swap on the first land: original Powermonger disk, then the WW1
        disk back) -> chart -> the small island -> protection question (answered from RAM; with noprot it must NOT appear) -> 3D map view
        with the world counter ticking."""
        t0 = t0 or time.time()
        stamp = lambda s: log(f"[{time.time() - t0:5.0f}s vbl {self.vbl()}] {s}")
        self.click_st(*START_NEW_XY, wait=2.0)
        if swap:
            if not self.wait_text("ORIGINAL", timeout=30):
                raise RuntimeError("disk requester (original Powermonger disk) not shown")
            stamp("requester: insert the original Powermonger disk")
            self.pm_disk_copy = self.R / "pm_orig.st"
            if not self.pm_disk_copy.exists():
                shutil.copy(PM_DISK, self.pm_disk_copy)
            self.swap_disk(self.pm_disk_copy)
            self.click_st(*REQ_OK_XY, wait=2.0)
            if not self.wait_text("DATA DISK", timeout=60):
                raise RuntimeError("requester asking for the WW1 data disk back not shown")
            stamp("requester: insert the WW1 data disk")
            self.swap_disk(self.disk_copy)
            self.click_st(*REQ_OK_XY, wait=2.0)
        time.sleep(8)
        stamp("chart expected")
        return self.chart_to_map(log, noprot, t0)

    def chart_to_map(self, log=print, noprot: bool = False, t0: float | None = None) -> bool:
        """Chart on screen -> the small island -> protection question (answered from RAM) -> 3D map view, world counter ticking."""
        t0 = t0 or time.time()
        stamp = lambda s: log(f"[{time.time() - t0:5.0f}s vbl {self.vbl()}] {s}")
        for attempt in range(8):
            self.goto_st(*ISLAND_XY)
            time.sleep(0.8)
            self.click(hold=0.3)
            if self.wait_question(25) or (self.peekw(WINDOW_OPEN) == 0 and self.ticking(2.0)):
                break
        else:
            raise RuntimeError("island click never started the land generation")
        stamp("island clicked")
        if noprot:
            if self.question_open():
                raise RuntimeError("protection question appeared although noprot is on")
        else:
            time.sleep(2)
            typ = self.peekw(PROT_TYPE)
            ans = self.peekw(PROT_ANS + 2 * typ)
            digits = [(ans // 1000) % 10, (ans // 100) % 10, (ans // 10) % 10, ans % 10]
            for x, n in zip(PROT_DIGIT_X, digits):
                if n:
                    self.goto_st(x, PROT_UP_Y)
                    for _ in range(n):
                        self.click(hold=0.15)
                        time.sleep(0.4)
            stamp(f"protection answer type {typ} value {ans}")
            self.click_st(*PROT_OK_XY, wait=2.0)
        t1 = time.time()
        while not (self.ticking(1.5) and self.peekw(WINDOW_OPEN) == 0):
            if time.time() - t1 > 150:
                raise RuntimeError("3D map view not reached (world counter not ticking)")
            time.sleep(2)
        stamp("3D map view, world counter ticking")
        return True

    def retire(self, win: bool = False, log=print) -> bool:
        """From the idle map view: Option (first command icon) -> GAME -> RETIRE.  win=True forces the 'conquered' balance at the
        check `cmpi.w #4,$5a830` ($d6c8; master $d2d8) from a one-shot breakpoint, so the win picture path (`$1b182`) runs."""
        self.click_st(*OPTION_XY, wait=2.0)
        self.click_st(*GAME_BTN_XY, wait=2.0)
        if win:
            (self.R / "win.txt").write_text(f"w ${RETIRE_STATE:x} $00 $04\n")
            self.debug("b all", 0.3)
            self.cmd(f"hatari-debug b pc = ${RETIRE_CHECK:x} :trace :once :file {self.R / 'win.txt'}")
            time.sleep(0.3)
        self.click_st(*RETIRE_BTN_XY, wait=3.0)
        return True


# ---- RAM map of the EA original (1 MB STE, TOS 1.62); evidence: work/notes/addrmap.md ---------------
MOUSE_X, MOUSE_Y = 0x2EDB2, 0x2EDB4        # words: pointer in ST low-res pixels
ITER = 0x2ED90                             # long: main-loop pass counter (+1 per pass; master $2df70)
WINDOW_OPEN = 0x74C0                       # word: window table slot, non-zero while a window (dialog, menu, question) is open (master $7a36)
WTEXT = 0x7640                             # the open window's text instance buffer
PROT_TYPE, PROT_ANS = 0x5A85C, 0x5B008     # word: 0 = houses / 1 = people; words: the expected answers (master $57ff8 / $5878e)
RETIRE_CHECK = 0xD6C8                      # the `cmpi.w #4,$5a830` that decides win / lose (master $d2d8)
RETIRE_STATE = 0x5A830                     # word: 4 = the land is won (master $57fce)
CACHE_CURSOR = 0x2CFDA                     # long: resource cache bump allocator (master $2c1ba), starts at $80000
PM_DISK = GAME.parent.parent / "done" / "powermonger" / "disks" / "protected.st"   # the original Powermonger floppy (user's copy) the game asks for

# screen coordinates in ST low-res pixels (x, y)
START_NEW_XY = (160, 85)                   # option screen: START NEW CONQUEST
REQ_OK_XY = (120, 118)                     # disk requester: OK
ISLAND_XY = (60, 24)                       # chart: the small island at the top
PROT_UP_Y, PROT_DIGIT_X, PROT_OK_XY = 170, (41, 45, 49, 53), (19, 176)
OPTION_XY, GAME_BTN_XY, RETIRE_BTN_XY = (70, 137), (47, 26), (25, 50)
