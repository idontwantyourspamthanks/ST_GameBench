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
    def __init__(self, disk: Path = DISK, workdir: str | None = None, cpuclock: int | None = None, snapshot: str | None = None, **kw):
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
            super().__init__(game_dir=GAME, snapshot=snapshot, workdir=str(R), extra=extra, **kw)
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

    def watch_pcs(self, pcs, tag: str = "watch"):
        """Count executions of code addresses: one `b pc = $x :trace :file` breakpoint each (the file prints `e pc`); see hits()."""
        self.debug("b all", 0.3)
        f = self.R / f"{tag}.txt"
        f.write_text("e pc\n")
        self._wmark = len(self._logtext())
        for pc in pcs:
            self.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}")
            time.sleep(0.1)

    def hits(self) -> dict:
        """{pc: executions} since watch_pcs (parsed from the debugger log)."""
        out, res = self._logtext()[self._wmark:], {}
        for blk in out.split("Reading debugger commands")[1:]:
            if "/tr_" in blk.split("\n", 1)[0]:          # the loader trace's own breakpoints (wwgate --trace) are not pc watches
                continue
            m = re.findall(r"\$([0-9a-f]+) \(hex\)", blk)
            if m:
                res[int(m[0], 16)] = res.get(int(m[0], 16), 0) + 1
        return res

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
        if not swap:                                  # pm_nokeydisk: the game must go straight to the chart without asking for the Powermonger disk
            time.sleep(25)
            if "ORIGINAL" in self.wtext().upper():
                raise RuntimeError("the game asked for the original Powermonger disk although pm_nokeydisk is on")
            stamp("no disk requester")
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
        time.sleep(8 if swap else 2)
        stamp("chart expected")
        return self.chart_to_map(log, noprot, t0)

    def chart_to_map(self, log=print, noprot: bool = False, t0: float | None = None, xy=None) -> bool:
        """Chart on screen -> the small island -> protection question (answered from RAM) -> 3D map view, world counter ticking."""
        t0 = t0 or time.time()
        stamp = lambda s: log(f"[{time.time() - t0:5.0f}s vbl {self.vbl()}] {s}")
        for attempt in range(8):
            self.goto_st(*(xy or ISLAND_XY))
            time.sleep(0.8)
            self.click(hold=0.3)
            if noprot:                            # no question may ever show up: poll for the map view instead of waiting for the question
                t1 = time.time()
                while time.time() - t1 < 40:
                    if self.question_open():
                        raise RuntimeError("protection question appeared although noprot is on")
                    if self.peekw(WINDOW_OPEN) == 0 and self.ticking(2.0):
                        break
                    time.sleep(1)
                else:
                    continue
                break
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

    def saveload(self, log=print) -> dict:
        """Option -> FILE -> SAVE (slot A, onto a blank formatted save disk: the game's own sector 0 + zeros; Hatari .st cannot be formatted by
        the game's write-track), let the world run, Option -> FILE -> LOAD.  The state a slot holds ($44c3e, $c6 sectors) is captured at the
        write call ($1cbc2, buffer = the game's RAM) and right after the read call returns ($1cb2a); the save disk image (flushed by ejecting it)
        is compared with the saved bytes.  Returns the numbers; the data disk is back in drive A afterwards."""
        out = self.R / "sl"
        out.mkdir(exist_ok=True)
        for f in out.glob("*.bin"):
            f.unlink()
        sd = out / "save_a.st"
        sd.write_bytes(save_disk_image())
        n = SAVE_LEN
        (out / "sv.txt").write_text(f"savebin {out}/save.bin ${SAVE_BASE:x} ${n:x}\n")
        (out / "ld.txt").write_text(f"savebin {out}/load.bin ${SAVE_BASE:x} ${n:x}\n")
        self.debug("b all", 0.3)
        self.cmd(f"hatari-debug b pc = ${SAVE_WRITE_CALL:x} :trace :once :file {out / 'sv.txt'}")
        self.click_st(*OPTION_XY, wait=2.0)
        self.click_st(*FILE_BTN_XY, wait=2.0)
        self.click_st(*SAVE_BTN_XY, wait=3.0)
        if not self.wait_text("SAVE GAME DISK", timeout=20):
            raise RuntimeError("save-disk requester not shown (SAVE button inactive: demo mode?)")
        log("requester: insert the save game disk")
        self.swap_disk(sd)
        self.click_st(*REQ_OK_XY, wait=3.0)
        t = time.time()
        while not (out / "save.bin").exists() or (out / "save.bin").stat().st_size < SAVE_LEN:
            if time.time() - t > 120:
                raise RuntimeError("the save never reached the sector driver")
            time.sleep(1)
        while time.time() - t < 240 and not (self.peekw(WINDOW_OPEN) == 0 and self.ticking(1.5)):    # the 198-sector floppy write ends, the map view runs again
            time.sleep(2)
        time.sleep(6)                                                     # the world moves on: the state differs from the saved one
        self.debug(f"savebin {out}/pre.bin ${SAVE_BASE:x} ${n:x}", 3.0)
        self.debug("b all", 0.3)
        self.cmd(f"hatari-debug b pc = ${SAVE_READ_RET:x} :trace :once :file {out / 'ld.txt'}")
        self.click_st(*OPTION_XY, wait=2.0)
        self.click_st(*FILE_BTN_XY, wait=2.0)
        self.click_st(*LOAD_BTN_XY, wait=3.0)
        t = time.time()
        while not (out / "load.bin").exists() or (out / "load.bin").stat().st_size < SAVE_LEN:
            if time.time() - t > 120:
                raise RuntimeError("the load never returned")
            time.sleep(1)
        time.sleep(3)
        ok_run = self.ticking(2.0) and self.peekw(WINDOW_OPEN) == 0
        sv, pre, ld = ((out / f"{k}.bin").read_bytes() for k in ("save", "pre", "load"))
        self.swap_disk(self.disk_copy)                                    # ejects the save disk: Hatari writes the image back
        time.sleep(2)
        disk = sd.read_bytes()
        return dict(n=n, d_saved_loaded=sum(a != b for a, b in zip(sv, ld)), d_saved_pre=sum(a != b for a, b in zip(sv, pre)),
                    disk_eq=disk[512:512 + n] == sv, disk_len=len(disk), slot_flag=disk[SLOT_FLAG_OFF], ticking=ok_run)

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

SAVE_BASE, SAVE_LEN = 0x44C3E, 0x18C00     # the game state a save slot holds: $c6 sectors (master $3f768)
SAVE_WRITE_CALL, SAVE_READ_RET = 0x1CBC2, 0x1CB2A      # `jsr $ddea` of the write (d3 = $8001) / the address it returns to for the read (d3 = $8000)
SLOT_FLAG_OFF = 0x1C964 - 0x1C860          # byte of save-disk sector 0: used-slot flag of slot A (the game's `$1c964 + k`)


def save_disk_image() -> bytes:
    """A formatted, empty save game disk: 800 sectors, sector 0 = the game's own boot block (resident image $1c860, 'POWERMONGER ... SAVED GAME DISC')."""
    sys.path.insert(0, str(HERE))
    import wwpatch
    blk = wwpatch.resident_bytes(0x1C860, 512)
    assert blk and blk[:4] == b"POWE"
    return blk + bytes(800 * 512 - 512)


# screen coordinates in ST low-res pixels (x, y)
FILE_BTN_XY, LOAD_BTN_XY, SAVE_BTN_XY, FORMAT_BTN_XY = (15, 26), (43, 15), (43, 32), (43, 50)     # Option window: FILE; FILE window: LOAD / SAVE / FORMAT
START_NEW_XY = (160, 85)                   # option screen: START NEW CONQUEST
REQ_OK_XY = (120, 118)                     # disk requester: OK
ISLAND_XY = (60, 24)                       # chart: the small island at the top
PROT_UP_Y, PROT_DIGIT_X, PROT_OK_XY = 170, (41, 45, 49, 53), (19, 176)
OPTION_XY, GAME_BTN_XY, RETIRE_BTN_XY = (70, 137), (47, 26), (25, 50)
