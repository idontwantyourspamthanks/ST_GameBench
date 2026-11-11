#!/usr/bin/env python3
"""Populous (PP HAGA) on the Hatari harness. Evidence: work/notes/{boot,baseline,ui}.md.

    import sys
    sys.path.insert(0, "<gamebench>/tools")
    sys.path.insert(0, "<gamebench>/games/in_progress/populous/tools")
    from populous import Populous
    h = Populous(snapshot=Populous.SNAP / "genesis_start.sav")   # 1 MB STE, start of Genesis
    h.busy_scene()                                               # 80 walkers on flat land
    print(h.world_rate(Populous.TURN, 500))

Test scaffolding only: nothing here is a game patch. busy_scene() changes RAM of
the running emulator (one byte of the protection trap, and a one-shot helper).
"""
from __future__ import annotations

import random
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from stharness import Hatari  # noqa: E402

# Screenshot pixels; home() leaves the pointer at ST (0,0) = screenshot (96,58).
HOME = (96, 58)
CONQUEST_XY = (641, 407)
START_XY = (254, 408)

SCENE_STUB = """
    org $70000
    movem.l d0-d7/a0-a6,-(sp)
    lea $34c22,a0               ; vertex heights, 65 x 65 words
    move.w #$1080,d0
.l  tst.w (a0)
    beq.s .n
    move.w #1,(a0)
.n  addq.l #2,a0
    dbra d0,.l
    move.w #63,-(sp)
    move.w #63,-(sp)
    clr.w -(sp)
    clr.w -(sp)
    jsr $c12c                   ; the game's heights -> tiles
    jsr $c2b8                   ; the game's minimap redraw
    addq.l #8,sp
    lea tab(pc),a3
.w  move.w (a3)+,d0
    bmi.s .done
    clr.w -(sp)
    move.w (a3)+,d1
    move.w (a3)+,d2
    move.w d2,-(sp)
    move.w d1,-(sp)
    move.w d0,-(sp)
    jsr $114c4                  ; the game's paint-mode "place a walker"
    addq.l #8,sp
    bra.s .w
.done
    lea $3b2b6,a0
    move.w #$cf,d0
.lf tst.w 4(a0)
    beq.s .nx
    move.w #LIFE,4(a0)
.nx lea 22(a0),a0
    dbra d0,.lf
    move.l #$0000da90,$b72a     ; put the original jsr target back
    movem.l (sp)+,d0-d7/a0-a6
    jmp $da90
tab:
    dc.w TAB,-1
"""


class Populous(Hatari):
    SNAP = GAME / "work" / "snapshots"
    TURN = 0x3C506          # word, +1 per main-loop pass ($db96)
    NPEEPS = 0x3C520        # word, highest used peep slot + 1
    PEEPS = 0x3B2B6         # 22 bytes each
    MOUSE_X, MOUSE_Y = 0x3C556, 0x3C55A   # position latched with a click ($16ccc)
    LEFT, RIGHT = 0x3D566, 0x3C514        # 0 = fresh click, 1 = up, 2 = handled / held
    MODE = 0x21D8E          # 1 shield, 2 raise/lower, +4 magnet, +8 swamp
    CMD = 0x21E4A           # player 0: command, arg, arg
    VIEW_X, VIEW_Y = 0x37EB8, 0x249EC     # 0..56
    PROT_BRANCH = 0xEE16    # beq of the $24 key check; $60 = always pass

    def __init__(self, **kw):
        kw.setdefault("game_dir", GAME / "originals" / "POPULOUS")
        kw.setdefault("memsize_kb", 1024)
        kw.setdefault("overlay", Path("/nonexistent"))
        if kw.get("snapshot"):
            kw["snapshot"] = str(kw["snapshot"])
        super().__init__(**kw)

    def in_play(self) -> bool:
        """The main loop's `jsr $14a28` at $b6f4 is present and the turn word moves."""
        if "4e b9 00 01 4a 28" not in self.debug("m $b6f4 6", 0.5).lower():
            return False
        t = self.peekw(self.TURN)
        time.sleep(1.5)
        return self.peekw(self.TURN) != t

    def boot_to_game(self) -> bool:
        """Cold boot to the first Conquest world. A key must be HELD: the loop reads it once per pass."""
        time.sleep(16)
        self.key("space", 0.5)     # PP's hardware screen
        time.sleep(22)             # logo, then the book menu
        self.goto(*CONQUEST_XY, home_xy=HOME)
        self.click(hold=0.4)
        time.sleep(9)
        self.goto(*START_XY, home_xy=HOME)
        self.click(hold=0.4)
        time.sleep(10)
        return self.in_play()

    def command(self, cmd: int, a: int = 0, b: int = 0) -> None:
        """Queue a player-0 command for the next pass (the bytes the click path writes; ui.md)."""
        self.debug(f"w ${self.CMD:x} ${cmd:02x} ${a:02x} ${b:02x}", 0.5)

    def manna(self, value: int = 300000) -> None:
        self.debug("w $3b270 " + " ".join(f"${x:02x}" for x in struct.pack(">I", value)), 0.3)

    def busy_scene(self, life: int = 300, seed: int = 2, view: tuple[int, int] = (44, 32)) -> None:
        """From genesis_start.sav: flat land and 78 walkers, then the game runs on its own (baseline.md)."""
        dump = self.R / "scene.bin"
        self.dump(str(dump), 0x34C22, 0x2102)
        time.sleep(1.0)
        alt = dump.read_bytes()

        def h(x, y):
            return struct.unpack_from(">H", alt, 2 * (x + 65 * y))[0]

        land = [(x, y) for y in range(64) for x in range(64)
                if all(h(x + dx, y + dy) > 0 for dx in (0, 1) for dy in (0, 1))]
        rnd = random.Random(seed)
        nw = [c for c in land if c[0] < 18 and c[1] < 22]
        east = [c for c in land if c[0] >= 41 and 28 <= c[1] <= 44]
        se = [c for c in land if c[0] >= 41 and c[1] >= 46]
        sw = [c for c in land if c[0] < 30 and c[1] >= 50]
        tab: list[int] = []
        for x, y in rnd.sample(nw, 18):
            tab += [0, x, y]
        ee = rnd.sample(east, 36)
        for x, y in ee[:18]:
            tab += [0, x, y]
        for x, y in ee[18:]:
            tab += [1, x, y]
        for x, y in rnd.sample(se, 14) + rnd.sample(sw, 10):
            tab += [1, x, y]
        src = self.R / "scene.s"
        out = self.R / "s.bin"
        src.write_text(SCENE_STUB.replace("LIFE", str(life)).replace("TAB", ",".join(map(str, tab))))
        r = subprocess.run(["vasmm68k_mot", "-Fbin", "-quiet", "-o", str(out), str(src)],
                           capture_output=True, text=True)
        if r.returncode or r.stderr:
            raise RuntimeError(r.stderr)
        self.debug(f"w ${self.PROT_BRANCH:x} $60", 0.4)
        self.debug(f"loadbin {out} $70000", 0.8)
        self.debug(f"w ${self.VIEW_X:x} $00 ${view[0]:02x}", 0.3)
        self.debug(f"w ${self.VIEW_Y:x} $00 ${view[1]:02x}", 0.3)
        self.debug("w $b72a $00 $07 $00 $00", 0.5)     # jsr $da90 -> jsr $70000, once
        time.sleep(2)
