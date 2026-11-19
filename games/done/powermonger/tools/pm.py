#!/usr/bin/env python3
"""Powermonger (floppy, disks/protected.st) navigation + state access on top of tools/stharness.Hatari.

    import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, '<gamebench>/games/in_progress/powermonger/tools')
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
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
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
PROT_FLAG = 0x14E4E                        # long: "protection passed" = $2c (original code `6000 1374` until the answer is right; protection.md)
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

    def protection_removed(self) -> bool:
        """True when the pm_noprot patch has preset the pass flag: the game then never asks the question."""
        return self.peekl(PROT_FLAG) == 0x2C

    def boot_to_game(self, name: str = "Bench", skip_key: str = "space", log=print, t_name: float = 400,
                     check: bool = True) -> bool:
        """Cold boot -> intro (skipped with `skip_key`) -> name prompt -> option screen -> START NEW CONQUEST ->
        territory chart -> the top-left island -> protection question (answer read from RAM; with the pm_noprot patch the
        pass flag is already set, `protection_removed()`, and the question must NOT appear) -> 3D map view.
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
        removed = self.protection_removed()
        self.click_st(*ISLAND_XY, wait=1.0)
        if removed:         # no question (pm_noprot): the 3D view comes up by itself; seeing the question box is a failure
            stamp("protection removed (flag $14e4e = $2c), no question expected")
            t1 = time.time()
            while not self.at("game"):
                if self.at("prot"):
                    raise RuntimeError("protection question appeared although the pass flag is preset")
                if time.time() - t1 > 120:
                    raise RuntimeError("3D map view not reached")
                time.sleep(3.0)
        else:
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

    for f in (at, mpos, goto_st, click_st, wait_gate, iter_count, in_game, protection_answer, protection_removed, boot_to_game):
        setattr(PM, f.__name__, f)


_methods()


def _methods2():
    def ram(self, start: int = 0, length: int = 0x100000) -> bytes:
        """Read `length` bytes of ST RAM at `start` through the debugger `savebin` (fast; `m` is 16 bytes/line)."""
        p = self.R / "ram.bin"
        if p.exists():
            p.unlink()
        self.debug(f"savebin {p} ${start:x} ${length:x}", 0.5)
        t = time.time()
        while not p.exists() or p.stat().st_size < length:
            if time.time() - t > 30:
                raise RuntimeError("savebin did not finish")
            time.sleep(0.2)
        time.sleep(0.2)
        return p.read_bytes()

    def people(self, d: bytes | None = None):
        """List of 512 raw 0x32-byte person records."""
        d = d if d is not None else self.ram(PEOPLE, PEOPLE_N * PEOPLE_STRIDE)
        base = 0 if len(d) == PEOPLE_N * PEOPLE_STRIDE else PEOPLE
        return [d[base + i * PEOPLE_STRIDE: base + (i + 1) * PEOPLE_STRIDE] for i in range(PEOPLE_N)]

    def moving_people(self, gap: float = 0.4) -> int:
        """Number of live person records whose position words (offsets 8, 10) change over `gap` seconds."""
        a = self.people()
        time.sleep(gap)
        b = self.people()
        n = 0
        for x, y in zip(a, b):
            if 0 < x[5] < 0x80 and x[8:12] != y[8:12]:
                n += 1
        return n

    def save_snapshot(self, name: str) -> Path:
        SNAP.mkdir(parents=True, exist_ok=True)
        out = SNAP / f"{name}.sav"
        self.savemem(str(out))
        return out

    def scenario_get_men(self, log=print, want: int = 6, timeout: float = 60) -> int:
        """From the idle 3D view: centre the close-up on the grey village (overview click), choose the 3-sword icon,
        then GET MEN. Waits until `want` people are moving. Returns the number moving."""
        self.click_st(22, 51, wait=1.5)
        self.click_st(*POSTURE3_XY, wait=0.8)
        self.click_st(*GETMEN_XY, wait=1.0)
        t = time.time()
        n = 0
        while time.time() - t < timeout:
            n = self.moving_people()
            log(f"moving people: {n}")
            if n >= want:
                break
        return n

    for f in (ram, people, moving_people, save_snapshot, scenario_get_men):
        setattr(PM, f.__name__, f)


_methods2()


# ---- measurement ----------------------------------------------------------------------------------
LOOP_SITES = (0x13040, 0x13046, 0x1304C, 0x13052, 0x13090, 0x13096, 0x130A4, 0x130AA, 0x130B0, 0x130B6, 0x130BC,
              0x130C2, 0x130C8, 0x130CE, 0x130F6, 0x130FC, 0x1386C, 0x13872)      # jsr sites of the main loop body
LOOP_NAMES = {
    0x13040: "$127e6", 0x13046: "$6522", 0x1304C: "$d322 (captain proximity scan)", 0x13052: "$3e06",
    0x13090: "VBL wait $1870", 0x13096: "$12ce0 (screen-window copy)", 0x130A4: "$178ae", 0x130AA: "$f898 (landscape + objects)",
    0x130B0: "$1abaa (season/weather dissolve)", 0x130B6: "$17878", 0x130BC: "$165b2", 0x130C2: "$14b62",
    0x130C8: "$6a3a", 0x130CE: "$7a56", 0x130F6: "$d23a", 0x130FC: "$7202", 0x1386C: "$187a (flip)", 0x13872: "$1a276"}


def _methods3():
    def profile_save(self, vbls: int, path: str, sim_iters: bool = False) -> int:
        """Hatari `profile save` over ~vbls VBLs (instruction counts + cycles per address) into `path`.
        Returns the number of VBL-handler executions inside the window (the exact frame count)."""
        end = self.R / "prof_end.txt"
        end.write_text(f"profile save {Path(path).resolve()}\n")
        start = self._arm_vbl(vbls + 25, f" :file {end}")
        time.sleep(0.3)
        self.cmd("hatari-debug profile on")
        self._wait_removed(start)
        time.sleep(1.0)
        txt = Path(path).read_text()
        m = re.search(r"^\$00001282\s.*?\((\d+),", txt, re.M)
        return int(m.group(1)) if m else 0

    def cyc_trace(self, pcs, vbls: int = 100, tag: str = "ct"):
        """Breakpoint at each pc in `pcs`; at every hit log (pc, CycleCounter, VBL). Cycle counts are the global
        emulated CPU cycle counter (32 bit, wraps), so differences between consecutive hits are exact stage costs
        including the interrupts that ran in between."""
        self.debug("b all", 0.3)
        f = self.R / f"{tag}.txt"
        f.write_text("e pc\ne CycleCounter\ne VBL\n")
        s0 = len(self._logtext())
        v = self.vbl()
        for pc in pcs:
            self.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}")
            time.sleep(0.1)
        self.cmd(f"hatari-debug b VBL > {v + vbls} :trace :once")
        t = time.time()
        while "Removed CPU breakpoint" not in self._logtext()[s0:]:
            if time.time() - t > 600:
                raise TimeoutError("cyc_trace")
            time.sleep(0.5)
        time.sleep(0.3)
        out = self._logtext()[s0:]
        self.debug("b all", 0.3)
        res = []
        for blk in out.split("Reading debugger commands")[1:]:
            m = re.findall(r"\$([0-9a-f]+) \(hex\)", blk)
            if len(m) >= 3:
                res.append((int(m[0], 16), int(m[1], 16), int(m[2], 16)))
        return res

    def ram_at_vbls(self, offsets, prefix: str):
        """Absolute-VBL deterministic RAM dumps: arms one VBL breakpoint per offset (frames from now) that runs
        `e VBL` + `savebin prefix_<n>.bin`. Returns [(vbl_at_hit, bytes)]."""
        self.debug("b all", 0.3)
        v0 = self.vbl()
        vs = [v0 + o for o in offsets]
        s0 = len(self._logtext())
        for v in vs:
            f = self.R / f"dat_{v}.txt"
            f.write_text(f"e VBL\nsavebin {prefix}_{v}.bin $0 $100000\n")
            self.cmd(f"hatari-debug b VBL > {v} :trace :once :file {f}")
            time.sleep(0.15)
        t = time.time()
        while self._logtext()[s0:].count("Removed CPU breakpoint") < len(vs):
            if time.time() - t > 900:
                raise TimeoutError("ram_at_vbls")
            time.sleep(0.5)
        time.sleep(0.6)
        got = [int(x) for x in re.findall(r"#(\d+) \(dec\)", self._logtext()[s0:])]
        return [(g, Path(f"{prefix}_{v}.bin").read_bytes()) for v, g in zip(vs, got)]

    for f in (profile_save, cyc_trace, ram_at_vbls):
        setattr(PM, f.__name__, f)


_methods3()
