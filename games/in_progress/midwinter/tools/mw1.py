#!/usr/bin/env python3
"""Midwinter 1 (PP's HAGA HD build) navigation + state access on top of tools/stharness.Hatari.

    import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, '<gamebench>/games/in_progress/midwinter/tools')
    from mw1 import MW1
    h = MW1(memsize_kb=1024)            # cold boot (autoruns C:\\RUNME.TOS)
    h.boot_to_game('M')                 # 'M'ouse, 'J'oystick or 'K'eyboard -> Skiing 3D view, standing
    print(h.gstate()); h.savemem('x.sav'); h.close()
    h = MW1(snapshot='x.sav')           # restore; the snapshot is retargeted to this run's scratch dir (see below)

Facts (all from RAM dumps of a 1 MB STE TOS 1.62 run; evidence in work/notes/mw1_state.md):
  * triple-buffered 3D view: flip routine $bd9a rotates the 3 buffers $58000/$68000/$78000 via the table at
    $2c376 and writes $ff8201, so the default flip_reg `($ff8201).b` counts presented frames.
  * the ski action mode runs in the loop at $14ac0 (entered by `jsr $1498a` at $125f6). $1efde is 0 while an
    action mode runs and 1 on every menu screen; $14ef6 is the "leave the action mode" flag (X key).
  * player state: X/Z world position longs $12c60/$12c64, speed word $15112, heading word $15114 (a per-frame
    copy of the master heading $12c98 made at $1323a); turning is a per-frame rate (mouse accumulator $24faa).

Snapshots: a Hatari memstate embeds the host path of the emulated hard disk (`/tmp/strun-XXXXXXXX/C`, part of the
saved configuration). Restored into another scratch dir, the game finds no C:\\FILES and shows "Insert graphics
disk" on the first load. MW1(snapshot=...) rewrites that path to the new scratch dir (see `retarget_snapshot`).
"""
from __future__ import annotations

import fcntl
import gzip
import re
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from stharness import Hatari, TOS  # noqa: E402,F401

REF = GAME / "work" / "ref"
SNAP = GAME / "work" / "snapshots"
OPTIONS_BOX = (250, 325, 580, 450)      # exact match of work/ref/options_play.png on the Game Options screen
PLAY_XY = (415, 385)
STARK_XY = (178, 170)                    # Team screen: Stark's portrait -> personality display
DECISIONS_XY = (450, 425)                # personality display: Decisions icon
SKIING_XY = (384, 424)                   # Decisions screen: Skiing icon
MODE_XY = {"M": (160, 258), "J": (264, 258), "K": (368, 258)}     # Game Options control icons
MORTARS_XY, BOMBERS_XY, TRAINING_XY = (470, 258), (572, 258), (673, 258)   # toggle icons

# Game state (addresses in the 1 MB STE TOS 1.62 RAM image; see work/notes/mw1_state.md)
POS_X, POS_Z = 0x12C60, 0x12C64          # long: world position inside the +-0x5000 window around $6400
SPEED = 0x15112                          # word: 0 standing, ~$f8 walking
HEADING = 0x15114                        # word: angle, only bits 0..9 are used (1024 per turn)
ACTION = 0x1EFDE                         # word: 0 while an action mode (skiing...) runs, 1 on menus
EXITFLAG = 0x14EF6                       # word: 1 = leave the action mode (X key sets it)
KEYASCII = 0x12AFC                       # word: last key (ASCII)
FLIP_PC = 0xBD9A
MORTARS_FLAG, BOMBERS_FLAG, TRAINING_FLAG = 0x2C17E, 0x2C17C, 0x2C180   # words; $ffff = option ON
CTRL_FLAGS = 0x24B7E                     # 3 words {mouse, joystick, keyboard}: $ffff for the selected control mode
WORLD_LO, WORLD_HI = 0x1388, 0xB478      # position bounds checked at $1457a/$14584 (outside -> window recentred at $152c0)


def retarget_snapshot(src: str | Path, dst: str | Path, new_workdir: str | Path) -> int:
    """Copy the gzip'd Hatari memstate `src` to `dst`, replacing every `/tmp/strun-<id>` (or `/tmp/mw2run-<id>`) scratch path
    inside it by `new_workdir` (the saved configuration holds the emulated hard-disk directory).
    Strings are NUL-terminated fields: the new string is padded in place. Returns the replacement count."""
    raw = gzip.decompress(Path(src).read_bytes())
    new = str(new_workdir).encode()
    olds = set(re.findall(rb"/tmp/(?:strun|mw2run)-[A-Za-z0-9_]+", raw))
    n = 0
    for old in olds:
        if old == new:
            continue
        pos = 0
        while (i := raw.find(old, pos)) >= 0:
            s = raw.rfind(b"\0", 0, i) + 1
            e = raw.find(b"\0", i)
            f = e
            while f < len(raw) and raw[f] == 0:
                f += 1
            field = raw[s:e].replace(old, new)
            if len(field) >= f - s:
                raise ValueError(f"new path longer than the {f - s}-byte field at {s:#x}")
            raw = raw[:s] + field.ljust(f - s, b"\0") + raw[f:]
            pos = s + len(field)
            n += 1
    Path(dst).write_bytes(gzip.compress(raw, 1))
    return n


class MW1(Hatari):
    def __init__(self, snapshot: str | None = None, workdir: str | None = None, **kw):
        kw.setdefault("overlay", Path("/nonexistent"))   # MW1 has no work/disk_overlay
        kw.setdefault("game_dir", GAME)
        if snapshot:
            # Pre-create the scratch dir so the snapshot can be retargeted at it.
            R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
            R.mkdir(parents=True, exist_ok=True)
            snap_in = R / "snap_in.sav"
            retarget_snapshot(snapshot, snap_in, R)
            snapshot, workdir = str(snap_in), str(R)
        super().__init__(snapshot=snapshot, workdir=workdir, **kw)

    def savemem(self, out: str):
        """Hatari writes every memstate save to the shared /tmp/hatari.sav (the cold-boot default), so
        serialise concurrent savers with a lock. The saved file embeds this scratch dir; MW1(snapshot=)
        retargets it on restore."""
        with open("/tmp/hatari-savemem.lock", "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            super().savemem(out)

    # ---- RAM access -------------------------------------------------------
    def peek(self, addr: int, n: int) -> bytes:
        """n bytes at addr via the debugger `m` command (16 per output line)."""
        out = self.debug(f"m ${addr:x} {n}", 0.7)
        bs: list[int] = []
        for ln in out.splitlines():
            m = re.match(r"[0-9A-Fa-f]{8}:\s(.*)", ln)
            if m:
                bs += [int(x, 16) for x in m.group(1).split("  ")[0].split()]
        if len(bs) < n:
            raise RuntimeError(f"short read at {addr:#x}: {out!r}")
        return bytes(bs[:n])

    def gstate(self) -> dict:
        """The ski-view state words, read in one go ($12c60.. and $15112.. are close together)."""
        a = self.peek(POS_X, 8)
        b = self.peek(SPEED, 4)
        c = self.peek(ACTION, 2)
        d = self.peek(EXITFLAG, 2)
        w = lambda x, i: int.from_bytes(x[i:i + 2], "big")
        return {"x": int.from_bytes(a[:4], "big"), "z": int.from_bytes(a[4:], "big"),
                "speed": w(b, 0), "heading": w(b, 2) & 0x3FF,
                "action": w(c, 0), "exit": w(d, 0)}

    def control_mode(self) -> str | None:
        """'M', 'J' or 'K' from the three flag words at $24b7e (set when a Game Options icon is clicked)."""
        b = self.peek(CTRL_FLAGS, 6)
        on = [k for k, i in (("M", 0), ("J", 2), ("K", 4)) if b[i:i + 2] == b"\xff\xff"]
        return on[0] if len(on) == 1 else None

    def in_ski(self) -> bool:
        """RAM check for 'the Skiing 3D loop is running': action mode active ($1efde==0), not leaving
        ($14ef6==0), position inside the world window, and the screen flips (fps over 100 VBL)."""
        s = self.gstate()
        if s["action"] != 0 or s["exit"] != 0:
            return False
        if not (WORLD_LO < s["x"] < WORLD_HI and WORLD_LO < s["z"] < WORLD_HI):
            return False
        return self.fps(100)["flips"] > 0

    def flip_trace(self, vbls: int = 300) -> list[tuple[int, int, int, int, int]]:
        """Run `vbls` VBLs and, at every call of the flip routine ($bd9a), log
        (vbl, x, z, speed, heading). One row per presented frame, so a trace shows what the world did per
        frame and per emulated second. Clears all breakpoints first."""
        cf = self.R / "ftrace.txt"
        cf.write_text(f"e VBL\nm ${POS_X:x} 8\nm ${SPEED:x} 4\n")
        self.debug("b all", 0.3)
        self.cmd(f"hatari-debug b pc = ${FLIP_PC:x} :trace :file {cf}")
        time.sleep(0.3)
        start = self._arm_vbl(vbls)
        out = self._wait_removed(start)
        self.debug("b all", 0.3)
        rows = []
        for blk in out.split("Reading debugger commands")[1:]:
            v = re.search(r"#(\d+) \(dec\)", blk)
            m = re.findall(r"^[0-9A-F]{8}: ((?:[0-9a-f]{2} ?)+?)\s{2}", blk, re.M)
            if not v or len(m) < 2:
                continue
            a = bytes.fromhex(m[0].replace(" ", ""))
            b = bytes.fromhex(m[1].replace(" ", ""))
            rows.append((int(v.group(1)), int.from_bytes(a[:4], "big"), int.from_bytes(a[4:8], "big"),
                         int.from_bytes(b[:2], "big"), int.from_bytes(b[2:4], "big") & 0x3FF))
        return rows

    def heading(self) -> int:
        return int.from_bytes(self.peek(HEADING, 2), "big") & 0x3FF

    def turn_to(self, target: int, dx: int = 250, tol: int = 8, timeout: float = 150) -> int:
        """Standing turn: the mouse X offset sets a turn RATE that persists while the pointer stays displaced
        (about 6-14 heading units/s for 150 px); undo the offset to stop. Heading 0 = +Z, 256 = +X,
        512 = -Z, 768 = -X (observed). Needs a few seconds per 100 units; retries if the game ignores the move."""
        t0 = time.time()
        while True:
            cur = self.heading()
            d = (target - cur + 512) % 1024 - 512
            if abs(d) <= tol:
                return cur
            if time.time() - t0 > timeout:
                raise TimeoutError(f"turn_to({target}) stuck at {cur}")
            s = dx if d > 0 else -dx
            self.center()
            time.sleep(0.3)
            self.rel(s, 0)
            t1, prev = time.time(), cur
            while time.time() - t1 < 60:
                time.sleep(0.4)
                cur = self.heading()
                d = (target - cur + 512) % 1024 - 512
                if abs(d) <= tol or (s > 0 and d < 0) or (s < 0 and d > 0):
                    break
                if time.time() - t1 > 4 and abs((cur - prev + 512) % 1024 - 512) < 2:
                    break                     # no response: re-centre and retry
            self.rel(-s, 0)
            time.sleep(1.0)

    # ---- navigation -------------------------------------------------------
    def at_options(self) -> bool:
        return self.screen_matches(REF / "options_play.png", OPTIONS_BOX)

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

    def click_at(self, xy, wait: float = 1.0):
        self.goto(*xy)
        self.click()
        time.sleep(wait)

    def options_flags(self) -> dict:
        """{'mortars','bombers','training'}: True when the Game Options toggle is ON ($ffff)."""
        return {k: self.peek(a, 2) == b"\xff\xff" for k, a in
                (("mortars", MORTARS_FLAG), ("bombers", BOMBERS_FLAG), ("training", TRAINING_FLAG))}

    def boot_to_game(self, mode: str = "M", bombers: bool = False, mortars: bool = False,
                     training: bool = True, check: bool = True) -> bool:
        """Cold boot -> Game Options -> chosen control mode ('M'/'J'/'K') -> PLAY -> Team -> Stark ->
        Decisions -> Skiing. Leaves Stark standing in the 3D view.
        The Game Options defaults (Mortars ON, Bombers ON, Training OFF) spawn enemy attack objects
        that kill Stark after a while and drop the game back to the Decisions screen (see
        work/notes/mw1_state.md). So by default Mortars/Bombers are switched OFF and Training ON."""
        mode = mode.upper()
        if not self.boot_to_options():
            raise RuntimeError("Game Options screen not reached")
        self.click_at(MODE_XY[mode])
        if self.control_mode() != mode:
            raise RuntimeError(f"control mode {mode} not selected (RAM says {self.control_mode()})")
        for want, xy in ((mortars, MORTARS_XY), (bombers, BOMBERS_XY)):
            if not want:
                self.click_at(xy)
        if training:
            self.click_at(TRAINING_XY)
        flags = self.options_flags()
        if flags != {"mortars": mortars, "bombers": bombers, "training": training}:
            raise RuntimeError(f"Game Options toggles wrong: {flags}")
        self.click_at(PLAY_XY, 12)
        self.click_at(STARK_XY, 6)
        self.click_at(DECISIONS_XY, 6)
        self.click_at(SKIING_XY, 10)
        self.center()
        if check and not self.in_ski():
            raise RuntimeError(f"not in the ski view: {self.gstate()}")
        return True

    # ---- controls in the ski view ----------------------------------------
    def walk(self):
        """Left click: start walking (speed ramps to walking speed; skiing takes over on a downslope)."""
        self.click("1")

    def stop(self):
        self.click("3")

    def exit_action(self):
        """X key: back to the Decisions screen."""
        self.key("x")
