#!/usr/bin/env python3
"""Pixel-equality gate (and speed measurement) for Populous display patches: patched vs unpatched, same snapshot, same input.

    python3 tools/popabtest.py gate  [--snap busy_castles busy_quake_volcano genesis_start] [--set pop_ptr pop_bgcopy ...]
                                     [--flips 200] [--mutant NAME] [--keep DIR]
    python3 tools/popabtest.py fps   [--snap ...] [--set ...] [--turns 150] [--moving]
    python3 tools/popabtest.py copy  [--snap ...]            # how much of the back buffer the $14a28 copy really changes
    python3 tools/popabtest.py cpytest [--mutant NAME]       # pop_bgcopy vs the original $14a28: registers, CCR, memory, random inputs
    python3 tools/popabtest.py mutants                       # the list of built-in broken patches (--mutant NAME)

`--set A B` is ONE patch set (names for `poppatch.py live --only`); pass `--set` several times for several sets, `--set none` is
the unpatched control (two unpatched runs, to prove the harness itself is deterministic).  Default sets: pop_ptr / pop_bgcopy /
pop_ptr + pop_bgcopy.  Exit status 0 = IDENTICAL everywhere.

How a run works (everything is applied live to a snapshot, which holds unpatched code, at the same instruction of the same pass
in both runs: `pc = $b800` of the turn T0, the main loop's `jsr $12fc2`, never inside a patched routine; T0 = the snapshot's turn
after a short run + 100, the same for every run of that snapshot):
  * Input is injected, not typed: the game polls the IKBD (absolute mode, `$0d`) and the packet handler copies the reply into
    $24786/$24788/$2478a, so a poke would be overwritten within a VBL and a host mouse reaches the game at a wall-clock moment.
    The run (1) turns the three stores of the packet handler ($2003e-$2005b) into nops, (2) replaces the main loop's flip call
    (`jsr $16f16` at $b940) with a stub that waits for the VBL flag as the game does, then, with interrupts masked, writes
    position / buttons / held key from a table (one row per flip), runs the game's own click state machine `$16c96` on them (what
    the next VBL would do, so no VBL phase can change what the pass sees), swaps the buffers exactly as `$16f1a-$16f3a` do, and
    captures; (3) hooks the VBL routine after the pointer code (`tst.w $2195e` at $16d88) for the junk / shape / x injections and
    the mid-frame samples below.  The stub is test scaffolding, in both runs; the patch under test is the only difference.
    Two timing races of the ORIGINAL game had to be removed from the comparison, each found as a handful of differing bytes
    between two runs that differ only in timing (the land patches): (a) a VBL falling between the position write and the buffer
    swap draws the new pointer into the old buffer (cured by masking interrupts from the position write to the capture);
    (b) the first VBL after a flip restores the pointer's saved background into the OLD buffer, which the game is by then
    re-drawing: where that write lands relative to the background copy and the tile draws depends on the CPU speed, and a stale
    rectangle can stay in the new frame.  The stub clears `$16f12` after the swap in both runs (`--keep-stale` leaves it, and then
    even a timing-only change differs in a few flips: work/notes/display.md section 3).
  * Capture (no emulated time passes): three breakpoints on stub addresses run `savebin` into a FIFO this process drains.
      flip   after every flip: both screen buffers (2 x 32,000 B) + the world RAM $21100-$3d7ff (116,480 B) + a header.
      sample the DISPLAYED buffer (+ the other one, not compared) in the 4th and 6th VBL after the flip: the pointer as drawn
             (or skipped) in the middle of a frame, with the injections of that frame in place.
    The world is frame-coupled (one turn per pass), so flip i of one run is turn T0+i of the other whatever the cycle counts.
  * Compared byte for byte per flip: both buffers; the world RAM except $24990-$249a3 (the sample player's state, advanced by a
    timer interrupt in real time: landscore.md, gate b); per sample: the displayed buffer.  The back buffer of a SAMPLE is being
    drawn and depends on VBL timing, so it is not compared.  A sample that exists in only one run (the frame had fewer VBLs) is
    counted, not compared.
  * Scenario (see build_script): pointer standing still on the map / book / panel / minimap / right panel, moving over all of them,
    the screen edges, the right-hand one-column case x > 304 and the bottom clip y > 184; sub-16-pixel moves; icon clicks that change
    the pointer mode (raise/lower, query, papal magnet), clicks on the map (raise, lower, place the magnet), keypad scrolling, the
    pause icon (the game redraws under a still pointer); and injections under a still pointer, in the 3rd VBL after a flip (erased by
    the original in the 4th): JUNK (the stub XORs the pointer's rectangle in the displayed buffer: a game drawing under it),
    SHAPE (the 160 shape bytes the draw reads are XORed), XPOS (x ^ 1: same word column, other shift).
  * `--mutant NAME` assembles a deliberately broken copy of a patch (MUTANTS below) and runs it through the same gate: it must FAIL.
  * `cpytest` runs pop_bgcopy and a verbatim copy of the original `$14a28` on the same random registers, every CCR input and three
    last longwords and compares registers, CCR and a 32,128-byte window with sentinels.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
from populous import Populous  # noqa: E402

SNAP = GAME / "work" / "snapshots"
SCRATCH = GAME / "build" / "PopDisplay"
TURN = 0x3C506
LOOP_PC = 0xB800            # `jsr $12fc2`: once per pass, the instruction before `jsr $db8a`; nothing patched is running there
SNAPS = ["busy_castles", "busy_quake_volcano", "genesis_start"]
SETS = [["pop_ptr"], ["pop_bgcopy"], ["pop_ptr", "pop_bgcopy"]]

BUFA, BUFB, BUFLEN = 0x4F500, 0x57200, 0x7D00
WORLD, WORLD_LEN = 0x21100, 0x1C700            # $21100-$3d7ff: game data + bss, peeps, maps, pointer variables
WORLD_SKIP = (0x24990, 0x249A4)                # the sample player's state
SAMPLE_VCNT = (3, 5)                           # VBL index (0 = the first after the flip hook) of the two mid-frame samples
JUNK_VCNT = 2

# ---- the input script -----------------------------------------------------------------------------------------------
LEFT, RIGHT = 4, 1                             # bits of $2478a ($16c96: left = bit 2, right = bit 0)
JUNK = 1                                       # flags bit 0: junk under the pointer in the 3rd VBL after this flip
MOVING = 2                                     # flags bit 1: the pointer moves every VBL (speed runs only)
SHAPE = 4                                      # flags bit 2: the shape rows the pointer draw reads are XORed for one VBL (3rd..4th)
XPOS = 8                                       # flags bit 3: pointer x ^ 1 for one VBL (3rd..4th): same word column, other shift
KEYS = {"W": 0x67, "N": 0x69, "NE": 0x6C, "E": 0x6F, "S": 0x6D, "SW": 0x6A, "NW": 0x68, "SE": 0x6E}


def build_script() -> list[tuple]:
    """Rows (x, y, buttons, key, flags), one per flip (pass).  Positions are ST pixels 0..319 x 0..199."""
    e: list[tuple] = []

    def hold(x, y, n, btn=0, key=0, fl=0):
        e.extend([(x, y, btn, key, fl)] * n)

    def move(a, b, n, btn=0, key=0, fl=0):
        for i in range(1, n + 1):
            e.append((a[0] + (b[0] - a[0]) * i // n, a[1] + (b[1] - a[1]) * i // n, btn, key, fl))

    hold(200, 100, 8)                                     # 0 the pointer standing still on the map
    move((200, 100), (120, 140), 12)                      # moving over the map
    hold(120, 140, 4)
    move((120, 140), (150, 5), 6)                         # up onto the book
    hold(150, 5, 5)
    move((150, 5), (30, 40), 6)                           # over the minimap
    hold(30, 40, 4)
    move((30, 40), (40, 188), 6)                          # the left panel
    hold(40, 188, 4)
    move((40, 188), (300, 170), 8)                        # across the bottom to the right panel
    hold(300, 170, 4)
    for p in [(0, 0), (319, 0), (319, 199), (0, 199), (304, 184), (305, 185), (310, 190), (300, 150), (15, 1), (16, 0),
              (303, 100), (8, 197), (250, 60), (64, 120)]:  # edges, x > 304 (one column), y > 184 (clipped rows)
        hold(*p, 2)
    # pointer mode changes through the icons (ui.md, $c420): raise/lower (96,184), query (112,176), papal magnet (80,192)
    move((64, 120), (112, 176), 3)
    hold(112, 176, 2, LEFT)                               # query (shield) mode
    hold(112, 176, 3)
    move((112, 176), (200, 110), 4)                       # over the map in query mode
    hold(200, 110, 3)
    move((200, 110), (96, 184), 4)
    hold(96, 184, 2, LEFT)                                # raise / lower mode
    hold(96, 184, 2)
    move((96, 184), (200, 110), 4)
    hold(200, 110, 3)                                     # standing on the map in raise/lower mode
    hold(200, 110, 4, LEFT)                               # raise land under the pointer
    hold(200, 110, 2)
    hold(200, 110, 3, RIGHT)                              # lower
    hold(200, 110, 2)
    move((200, 110), (170, 95), 3, LEFT)                  # raise while moving
    hold(170, 95, 2)
    move((170, 95), (80, 192), 4)
    hold(80, 192, 2, LEFT)                                # papal magnet mode
    hold(80, 192, 2)
    move((80, 192), (180, 100), 4)
    hold(180, 100, 3)
    hold(180, 100, 2, LEFT)                               # place the magnet
    hold(180, 100, 3)
    move((180, 100), (96, 184), 4)
    hold(96, 184, 2, LEFT)                                # back to raise / lower
    hold(96, 184, 2)
    move((96, 184), (170, 100), 4)
    hold(170, 100, 3)
    # scrolling with the keypad, pointer still and moving
    hold(170, 100, 4, key=KEYS["E"])
    hold(170, 100, 3)
    hold(170, 100, 4, key=KEYS["S"])
    move((170, 100), (190, 120), 4, key=KEYS["W"])
    hold(190, 120, 3, key=KEYS["N"])
    hold(190, 120, 4)
    # the game drawing under a still pointer: icon clicks redraw the icon (hide / show around the blit)
    move((190, 120), (273, 191), 4)
    hold(273, 191, 2, LEFT)                               # pause (zzZ): the world stops, the pointer stays on the icon
    hold(273, 191, 4)
    hold(273, 191, 2, LEFT)                               # and resume
    hold(273, 191, 3)
    # JUNK: the stub scribbles under the pointer in the displayed buffer; the original VBL restores it
    hold(200, 100, 3, fl=JUNK)
    hold(200, 100, 2)
    hold(100, 20, 2, fl=JUNK)                             # over the book
    hold(100, 20, 2)
    hold(300, 190, 2, fl=JUNK)                            # bottom right, the clipped one-column case
    hold(300, 190, 2)
    hold(30, 40, 2, fl=JUNK)                              # minimap
    hold(30, 40, 3)
    # the shape data the draw reads changes under a still pointer (stub: XOR in the 3rd VBL, back in the 4th)
    hold(200, 100, 3, fl=SHAPE)
    hold(200, 100, 2)
    hold(40, 188, 2, fl=SHAPE)
    hold(40, 188, 2)
    hold(200, 100, 3, fl=XPOS)                            # the pointer's x changes by one pixel between two VBLs of a frame
    hold(200, 100, 2)
    hold(37, 150, 2, fl=XPOS | SHAPE)
    hold(37, 150, 2)
    # sub-16-pixel moves: same word column, new shift (the address under the pointer does not change)
    move((40, 188), (100, 60), 3)
    move((100, 60), (118, 60), 18)
    hold(118, 60, 3)
    move((118, 60), (118, 70), 10)
    hold(200, 100, 6)
    return e


SCRIPT = build_script()

# ---- the test scaffolding in the emulated machine (assembled with vasm at run time) ------------------------------------
HDR, FLAGS, VCNT, TAB = 0x76400, 0x76410, 0x76412, 0x76500
CAPF, CAPS3, CAPS5 = 0x76300, 0x76320, 0x76340
HOOK1, HOOK2 = 0x76000, 0x76100
STUB_EQU = f"""HDR\tequ\t${HDR:x}
FLAGS\tequ\t${FLAGS:x}
VCNT\tequ\t${VCNT:x}
TAB\tequ\t${TAB:x}
NENT\tequ\t{len(SCRIPT)}
"""
STUB1 = """
        org     $76000
hook:   movem.l d0-d2/a0,-(sp)
        jsr     $16f48.l                ; the game's own wait for the VBL flag (as $16f16 starts); then nothing may interrupt
        move.w  sr,-(sp)                ; until the buffers are swapped and captured: a VBL between the position write and
        ori.w   #$700,sr                ; the swap would draw the NEW pointer into the OLD buffer, at a wall-clock dependent moment
        move.w  HDR+2.l,d0              ; rows consumed = flip index
        cmpi.w  #NENT-1,d0
        bls.s   .ok
        move.w  #NENT-1,d0
.ok:    lsl.w   #3,d0
        lea     TAB.l,a0
        adda.w  d0,a0
        move.w  (a0)+,$24786.l          ; pointer x / y, buttons: what the IKBD packet would have stored
        move.w  (a0)+,$24788.l
        move.b  (a0)+,$2478a.l
        move.b  (a0)+,$37eec.l          ; the held key the main loop reads at $b94c
        move.w  (a0)+,FLAGS.l
        jsr     $16c96.l                ; the VBL's click state machine on the new inputs (idempotent for later VBLs)
        clr.w   VCNT.l
        addq.w  #1,HDR+2.l
        move.l  $3c510.l,d0             ; $16f1a-$16f3a of the game's flip, verbatim
        move.l  $3c50c.l,d1
        move.l  d1,$3c510.l
        move.l  d0,$3c50c.l
        lsr.w   #8,d0
        move.l  d0,$ffff8200.l
        clr.w   $16d28.l
NOSTALE
        move.w  #1,HDR.l
        move.w  VCNT.l,HDR+4.l
        move.w  $16d26.l,HDR+6.l
        move.l  $3c50c.l,HDR+8.l
        move.l  $3c510.l,HDR+12.l
        jsr     $76300.l                ; capture: flip
        move.w  (sp)+,sr
        movem.l (sp)+,d0-d2/a0
        rts

        org     $76300
        nop
        rts
        org     $76320
        nop
        rts
        org     $76340
        nop
        rts
"""
STUB2 = f"""
        org     $76100
vbl:    movem.l d0-d2/a0,-(sp)
        move.w  VCNT.l,d0
        btst.b  #1,FLAGS+1.l            ; speed runs: the pointer moves every VBL
        beq.s   .nm
        move.w  $24786.l,d1
        addq.w  #5,d1
        cmpi.w  #300,d1
        bcs.s   .xm
        moveq   #10,d1
.xm:    move.w  d1,$24786.l
.nm:    cmpi.w  #{JUNK_VCNT},d0
        bne.s   .nj
        btst.b  #0,FLAGS+1.l            ; junk under the pointer, in the displayed buffer
        beq.s   .nj
        move.l  $16f12.l,d1
        beq.s   .nj
        movea.l d1,a0
        move.w  $2498c.l,d2
        cmpi.w  #15,d2
        bhi.s   .nj
.jr:    eori.w  #$a5c3,(a0)+
        eori.w  #$a5c3,(a0)+
        eori.w  #$a5c3,(a0)+
        eori.w  #$a5c3,(a0)+
        lea     152(a0),a0
        dbra    d2,.jr
.nj:    cmpi.w  #{JUNK_VCNT},d0
        bne.s   .ns
        btst.b  #2,FLAGS+1.l            ; shape rows changed under a still pointer (restored in the next VBL)
        beq.s   .nx
        bsr.s   .shape
.nx:    btst.b  #3,FLAGS+1.l            ; pointer x ^ 1 for one VBL: same word column, other shift
        beq.s   .ns
        eori.w  #1,$24786.l
.ns:    cmpi.w  #{SAMPLE_VCNT[0]},d0
        bne.s   .n3
        move.w  #2,HDR.l
        bsr.s   .hdr
        jsr     ${CAPS3:x}.l
        btst.b  #2,FLAGS+1.l
        beq.s   .rx
        bsr.s   .shape
.rx:    btst.b  #3,FLAGS+1.l
        beq.s   .done
        eori.w  #1,$24786.l
        bra.s   .done
.n3:    cmpi.w  #{SAMPLE_VCNT[1]},d0
        bne.s   .done
        move.w  #3,HDR.l
        bsr.s   .hdr
        jsr     ${CAPS5:x}.l
.done:  addq.w  #1,VCNT.l
        movem.l (sp)+,d0-d2/a0
        tst.w   $2195e.l                ; the displaced instruction (the beq after it reads its flags)
        rts
.shape: move.w  $2169a.l,d1             ; the 160 bytes $16e84-$16ea2 address
        add.w   d1,d1
        lea     $22b06.l,a0
        move.w  (a0,d1.w),d1
        ext.l   d1
        movea.l $3d572.l,a0
        mulu.w  #$a0,d1
        adda.l  d1,a0
        moveq   #39,d2
.sx:    eori.l  #$5a5a5a5a,(a0)+
        dbra    d2,.sx
        rts
.hdr:   move.w  VCNT.l,HDR+4.l
        move.w  $16d26.l,HDR+6.l
        move.l  $3c50c.l,HDR+8.l
        move.l  $3c510.l,HDR+12.l
        rts
"""
VBL_SITE, VBL_ORIG = 0x16D88, bytes.fromhex("4a790002195e")          # tst.w $2195e.l
FLIP_JSR = 0xB942                                                    # operand of `jsr $16f16.l` at $b940
FLIP_ORIG = bytes.fromhex("00016f16")
ACIA_STORES = (0x2003E, 30)                                          # three `move.? abs.l,abs.l` of the packet handler


def vasm(src: str) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        s, o = Path(td) / "a.s", Path(td) / "a.bin"
        s.write_text(src)
        r = subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(o), str(s)], capture_output=True, text=True)
        if r.returncode or r.stderr.strip():
            raise SystemExit(f"vasm failed:\n{r.stderr}\n{src}")
        return o.read_bytes()


KEEP_STALE = False
NOSTALE_INSN = "        clr.l   $16f12.l                ; scaffold: no stale pointer restore into the old buffer (see the module notes, `stale`)"


def stub_images() -> dict[int, bytes]:
    """{address: bytes} of the scaffolding: hook code, VBL stub, header + script table."""
    # each org assembled alone: vasm's bin output of several orgs is one file from the first org
    segs: dict[int, bytes] = {}
    for src in (STUB1.replace("NOSTALE", "" if KEEP_STALE else NOSTALE_INSN), STUB2):
        parts = re.split(r"(?m)^\s+org\s+\$([0-9a-f]+)\s*$", src)
        for i in range(1, len(parts), 2):
            org = int(parts[i], 16)
            segs[org] = vasm(STUB_EQU + f"\n\torg\t${org:x}\n" + parts[i + 1])
    tab = b"".join(struct.pack(">HHBBH", *row) for row in SCRIPT)
    segs[HDR] = bytes(0x100)                    # header + flags zeroed
    segs[TAB] = tab
    return segs


# ---- patch sets, mutants ----------------------------------------------------------------------------------------------
# name -> (patch file, [(old, new)]) ; every `old` must occur exactly once in the patch source
MUTANTS = {
    "ptr_norect": ("pop_ptr", [("        movea.l d0,a1                   ; the rectangle on screen ...\n", "        rts\n")]),
    "ptr_noshape": ("pop_ptr", [(".shape: move.w  $2169a.l,d2             ; the shape rows", ".shape: rts\n        move.w  $2169a.l,d2             ; the shape rows")]),
    "ptr_nopos": ("pop_ptr", [("        cmp.w   pX(a0),d1\n", "        cmp.w   d1,d1\n")]),
    "ptr_nobuf": ("pop_ptr", [("        cmp.l   pBUF(a0),d1\n        bne.w   full\n        move.w  $24786.l,d1", "        cmp.l   d1,d1\n        bne.w   full\n        move.w  $24786.l,d1")]),
    "cpy_short": ("pop_bgcopy", [("        lea     31980(a0),a2", "        lea     31200(a0),a2")]),
    "cpy_tail": ("pop_bgcopy", [("        move.l  (a1)+,(a0)+             ; the flags the original ends with\n", "")]),
    "cpy_off": ("pop_bgcopy", [("movem.l d0-d7/a2-a6,364(a0)", "movem.l d0-d7/a2-a6,368(a0)")]),
}


def live_image(names: list[str], mutant: str | None, tag: str) -> str:
    """poppatch.py live for `names`; with a mutant, the patch source is edited in a scratch copy of patches/. Returns the prefix."""
    out = SCRATCH / "live" / tag
    out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if not mutant:
        r = subprocess.run([sys.executable, str(HERE / "poppatch.py"), "live", "--only", *names, "--out", str(out.relative_to(GAME))],
                           cwd=GAME, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stdout + r.stderr)
        return str(out)
    fname, edits = MUTANTS[mutant]
    import shutil
    pd = SCRATCH / "mut" / tag
    shutil.rmtree(pd, ignore_errors=True)
    shutil.copytree(GAME / "patches", pd)
    txt = (pd / f"{fname}.s").read_text()
    for old, new in edits:
        if txt.count(old) != 1:
            raise SystemExit(f"mutant {mutant}: `{old.strip()[:50]}` occurs {txt.count(old)} times")
        txt = txt.replace(old, new)
    (pd / f"{fname}.s").write_text(txt)
    import contextlib
    import io
    import poppatch
    poppatch.PATCHDIR = pd
    pats = [p for p in poppatch.load_patches() if p.name in set(names)]
    if len(pats) != len(names):
        raise SystemExit(f"patches {names} not all found")
    with contextlib.redirect_stdout(io.StringIO()):
        poppatch.cmd_live(pats, out)
    return str(out)


# ---- one run -------------------------------------------------------------------------------------------------------------
class Rec:
    __slots__ = ("tag", "idx", "vcnt", "hide", "front", "back", "bufs", "world")


def fifo_reader(fifo: Path, chunks: queue.Queue, stop: threading.Event) -> None:
    """Drain a FIFO.  The FIFO is opened read-write once, so this process is always a writer too: the pipe never reports EOF
    between the emulator's savebin calls (a reader that reopens loses the data of a writer that opens in between)."""
    import select
    fd = os.open(fifo, os.O_RDWR)
    try:
        while not stop.is_set():
            if select.select([fd], [], [], 0.5)[0]:
                chunks.put(os.read(fd, 1 << 16))
    finally:
        os.close(fd)


def zc(b: bytes) -> bytes:
    return zlib.compress(b, 1)


def start_turn(snap: str) -> int:
    """T0 for a snapshot: its turn after a short run, plus 100 (the emulator runs in real time until the breakpoints are armed;
    every run of the snapshot must use the SAME T0)."""
    h = Populous(snapshot=SNAP / f"{snap}.sav")
    try:
        time.sleep(1.0)
        return h.peekw(TURN) + 100
    finally:
        h.close()


def run_capture(snap: str, live: str | None, flips: int, label: str, t0: int, fast: bool = True) -> dict:
    """Restore `snap`, apply the scaffolding (+ the live patch set) at turn `t0`, capture `flips` flips and the mid-frame samples."""
    h = Populous(snapshot=SNAP / f"{snap}.sav")
    try:
        time.sleep(0.5)
        fifo = h.R / "pipe"
        os.mkfifo(fifo)
        chunks: queue.Queue = queue.Queue()
        stop = threading.Event()

        threading.Thread(target=fifo_reader, args=(fifo, chunks, stop), daemon=True).start()

        segs = stub_images()
        cmds = []
        for a, b in sorted(segs.items()):
            p = h.R / f"seg_{a:x}.bin"
            p.write_bytes(b)
            cmds.append(f"loadbin {p} ${a:x}")
        cmds.append(f"w ${ACIA_STORES[0]:x} " + " ".join(["$4e $71"] * (ACIA_STORES[1] // 2)))
        if live:
            spec = json.loads(Path(live + ".json").read_text())
            cmds.append(f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}")
        cmds.append(f"w ${VBL_SITE:x} $4e $b9 $00 $07 $61 $00")                 # jsr $76100.l
        cmds.append(f"w ${FLIP_JSR:x} $00 $07 $60 $00")                          # jsr $16f16 -> jsr $76000
        if live:
            for s in spec["sites"]:
                cmds.append(f"w ${s['addr']:x} " + " ".join(f"${x:02x}" for x in bytes.fromhex(s["new"])))
        apply_f = h.R / "apply.txt"
        apply_f.write_text("\n".join(cmds) + "\n")
        f_flip, f_s3, f_s5 = h.R / "cf.txt", h.R / "c3.txt", h.R / "c5.txt"
        f_flip.write_text(f"savebin {fifo} ${HDR:x} $10\nsavebin {fifo} ${BUFA:x} ${BUFLEN:x}\nsavebin {fifo} ${BUFB:x} ${BUFLEN:x}\n"
                          f"savebin {fifo} ${WORLD:x} ${WORLD_LEN:x}\n")
        for f in (f_s3, f_s5):
            f.write_text(f"savebin {fifo} ${HDR:x} $10\nsavebin {fifo} ${BUFA:x} ${BUFLEN:x}\nsavebin {fifo} ${BUFB:x} ${BUFLEN:x}\n")
        h.debug("b all", 0.3)
        for pc, f in ((CAPF, f_flip), (CAPS3, f_s3), (CAPS5, f_s5)):
            h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}")
            time.sleep(0.2)
        h.cmd(f"hatari-debug b pc = ${LOOP_PC:x} && (${TURN:x}).w = {t0} :trace :once :file {apply_f}")
        time.sleep(0.3)
        if fast:
            h.cmd("hatari-option --fast-forward on")

        recs: list[Rec] = []
        buf = bytearray()
        need = 0

        def take(n: int, timeout: float = 40.0) -> bytes | None:
            nonlocal buf
            t = time.time()
            while len(buf) < n:
                try:
                    buf += chunks.get(timeout=1.0)
                except queue.Empty:
                    if time.time() - t > timeout:
                        return None
            out = bytes(buf[:n])
            del buf[:n]
            return out

        nflip = 0
        done = False
        while not done:
            hd = take(16)
            if hd is None:
                raise TimeoutError(f"no capture data ({label}); log tail:\n{h._logtext()[-1200:]}")
            tag, idx, vcnt, hide, front, back = struct.unpack(">HHHHII", hd)
            if tag not in (1, 2, 3):
                raise RuntimeError(f"capture stream out of step ({label}): header {hd.hex()}")
            a, b = take(BUFLEN), take(BUFLEN)
            if a is None or b is None:
                raise TimeoutError(f"capture stalled after header {hd.hex()} ({label}); buffered {len(buf)}; log tail:\n{h._logtext()[-1500:]}")
            r = Rec()
            r.tag, r.idx, r.vcnt, r.hide, r.front, r.back = tag, idx, vcnt, hide, front, back
            r.bufs = (zc(a), zc(b))
            w = take(WORLD_LEN) if tag == 1 else b""
            if w is None:
                raise TimeoutError(f"capture stalled in the world block ({label}); log tail:\n{h._logtext()[-1500:]}")
            r.world = zc(w) if tag == 1 else None
            recs.append(r)
            if tag == 1:
                nflip += 1
                if nflip >= flips:
                    done = True
        h.cmd("hatari-debug b all")
        h.cmd("hatari-option --fast-forward off")
        stop.set()
        return {"label": label, "snap": snap, "t0": t0, "recs": recs, "vbl": h.vbl() if False else None}
    finally:
        h.close()


# ---- comparison -------------------------------------------------------------------------------------------------------
def ranges(a: bytes, b: bytes, base: int = 0, gap: int = 16) -> list[tuple[int, int, int]]:
    """Differing byte ranges (lo, hi, count) merged when closer than `gap`."""
    out = []
    n = len(a)
    if a == b:
        return out
    lo = hi = None
    cnt = 0
    i = 0
    # fast path: walk 64-byte blocks first
    while i < n:
        if a[i:i + 64] == b[i:i + 64]:
            i += 64
            continue
        for j in range(i, min(i + 64, n)):
            if a[j] != b[j]:
                if lo is None:
                    lo = hi = j
                    cnt = 1
                elif j - hi > gap:
                    out.append((base + lo, base + hi, cnt))
                    lo = hi = j
                    cnt = 1
                else:
                    hi = j
                    cnt += 1
        i += 64
    if lo is not None:
        out.append((base + lo, base + hi, cnt))
    return out


def buf_desc(rs: list) -> str:
    rows = sorted({lo // 160 for lo, hi, _ in rs} | {hi // 160 for lo, hi, _ in rs})
    return f"{sum(c for _, _, c in rs)} bytes in {len(rs)} range(s), rows {rows[0]}..{rows[-1]}, first at row {rs[0][0] // 160} byte {rs[0][0] % 160}"


def world_mask(w: bytes) -> bytes:
    lo, hi = WORLD_SKIP[0] - WORLD, WORLD_SKIP[1] - WORLD
    return w[:lo] + bytes(hi - lo) + w[hi:]


def key_of(r: Rec):
    return (r.tag, r.idx if r.tag == 1 else r.idx, r.vcnt if r.tag != 1 else 0)


def compare(A: dict, B: dict, verbose: bool = True) -> dict:
    """A = reference (unpatched), B = patched."""
    ra = {key_of(r): r for r in A["recs"]}
    rb = {key_of(r): r for r in B["recs"]}
    res = {"flips": 0, "flip_bad": [], "world_bad": [], "samples": 0, "sample_bad": [], "only_ref": 0, "only_new": 0, "notes": []}
    first_detail: list[str] = []
    for k in sorted(set(ra) | set(rb)):
        if k not in ra:
            res["only_new"] += 1
            continue
        if k not in rb:
            res["only_ref"] += 1
            continue
        x, y = ra[k], rb[k]
        if k[0] == 1:
            res["flips"] += 1
            if (x.front, x.back) != (y.front, y.back):
                res["flip_bad"].append((k[1], "buffer roles differ"))
            for n in (0, 1):
                da, db = zlib.decompress(x.bufs[n]), zlib.decompress(y.bufs[n])
                if da != db:
                    role = "front(new frame)" if (x.front == (BUFA, BUFB)[n]) else "back(old frame + pointer)"
                    rs = ranges(da, db)
                    res["flip_bad"].append((k[1], f"{role} {buf_desc(rs)}"))
                    if len(first_detail) < 6:
                        first_detail.append(f"flip {k[1]} {role}: {buf_desc(rs)}; pointer words at this flip: "
                                            f"{struct.unpack_from('>HH', zlib.decompress(x.world), 0x24786 - WORLD)}")
            wa, wb = world_mask(zlib.decompress(x.world)), world_mask(zlib.decompress(y.world))
            if wa != wb:
                rs = ranges(wa, wb, WORLD, 4)
                res["world_bad"].append((k[1], ", ".join(f"${lo:x}-${hi:x}({c})" for lo, hi, c in rs[:6])))
        else:
            res["samples"] += 1
            if x.front != y.front:
                res["sample_bad"].append((k, "front differs"))
                continue
            n = 0 if x.front == BUFA else 1
            da, db = zlib.decompress(x.bufs[n]), zlib.decompress(y.bufs[n])
            if da != db:
                rs = ranges(da, db)
                res["sample_bad"].append((k[1:], buf_desc(rs)))
    res["detail"] = first_detail
    res["identical"] = not (res["flip_bad"] or res["world_bad"] or res["sample_bad"]) and res["flips"] > 0
    return res


def coverage(A: dict) -> dict:
    """What the scenario really did, from the reference run's world RAM: pointer positions, shapes, modes, holds."""
    pos, shp, mode, pause, btn, hts, views = [], [], [], [], [], [], []
    for r in A["recs"]:
        if r.tag != 1:
            continue
        w = zlib.decompress(r.world)
        hts.append(w[0x34C22 - WORLD:0x34C22 - WORLD + 0x2102])
        views.append(struct.unpack_from(">HH", w, 0x37EB8 - WORLD)[0:1] + struct.unpack_from(">H", w, 0x249EC - WORLD))
        pos.append(struct.unpack_from(">HH", w, 0x24786 - WORLD))
        btn.append(w[0x2478A - WORLD])
        shp.append(struct.unpack_from(">H", w, 0x2169A - WORLD)[0])
        mode.append(struct.unpack_from(">H", w, 0x21D8E - WORLD)[0])
        pause.append(struct.unpack_from(">H", w, 0x3B2B2 - WORLD)[0])
    still = sum(1 for a, b in zip(pos, pos[1:]) if a == b)
    hides = sum(1 for r in A["recs"] if r.tag == 1 and r.hide)
    return {"flips": len(pos), "pointer_still_flips": still, "pointer_moved_flips": len(pos) - 1 - still,
            "shapes": sorted(set(shp)), "shape_changes": sum(1 for a, b in zip(shp, shp[1:]) if a != b),
            "modes": sorted(set(mode)), "mode_changes": sum(1 for a, b in zip(mode, mode[1:]) if a != b),
            "paused_flips": sum(1 for p in pause if p), "button_flips": sum(1 for b in btn if b),
            "junk_flips": sum(1 for r in SCRIPT[:len(pos)] if r[4] & JUNK), "shape_flips": sum(1 for r in SCRIPT[:len(pos)] if r[4] & SHAPE),
            "xpos_flips": sum(1 for r in SCRIPT[:len(pos)] if r[4] & XPOS), "hidden_at_flip": hides,
            "flips_with_terrain_change": sum(1 for a, b in zip(hts, hts[1:]) if a != b),
            "distinct_views": len(set(views))}


# ---- gate ---------------------------------------------------------------------------------------------------------------------
def cmd_gate(a) -> int:
    snaps = a.snap or SNAPS
    sets = [s if s != ["none"] else [] for s in (a.set or SETS)]
    flips = a.flips or len(SCRIPT)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    jobs = []
    for sn in snaps:
        jobs.append((sn, None, "ref"))
        for ns in sets:
            tag = "+".join(ns) or "none"
            if a.mutant:
                tag += "@" + a.mutant
            jobs.append((sn, ns, tag))

    t0s = {sn: start_turn(sn) for sn in snaps}
    print("T0 per snapshot:", t0s, flush=True)
    lives = {}
    for sn, ns, tag in jobs:                        # built one after the other (the mutant path edits a module global)
        if ns:
            lives[(sn, tag)] = live_image(ns, a.mutant, f"{sn}_{tag}".replace("+", "_").replace("@", "_"))

    def do(job):
        sn, ns, tag = job
        live = lives.get((sn, tag))
        t = time.time()
        d = run_capture(sn, live, flips, f"{sn}/{tag}", t0s[sn])
        d["secs"] = round(time.time() - t, 1)
        return job, d

    results: dict = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        for job, d in ex.map(do, jobs):
            results[(job[0], job[2])] = d
            print(f"  ran {d['label']}: {sum(1 for r in d['recs'] if r.tag == 1)} flips, {sum(1 for r in d['recs'] if r.tag != 1)} samples, "
                  f"T0={d['t0']}, {d['secs']} s", flush=True)
    rc = 0
    for sn in snaps:
        ref = results[(sn, "ref")]
        cov = coverage(ref)
        print(f"\n== {sn}: scenario (reference run) {json.dumps(cov)}")
        for ns in sets:
            tag = "+".join(ns) or "none"
            if a.mutant:
                tag += "@" + a.mutant
            r = compare(ref, results[(sn, tag)])
            verdict = "IDENTICAL" if r["identical"] else "DIFFERENT"
            print(f"{sn:20s} {tag:34s} {verdict}: flips compared {r['flips']} (both buffers + world each), "
                  f"bad flips {len(r['flip_bad'])} (world only {len(r['world_bad'])}), mid-frame samples {r['samples']} bad {len(r['sample_bad'])}"
                  f" (only in one run: ref {r['only_ref']}, new {r['only_new']})")
            for i, m in r["flip_bad"][:8]:
                print(f"    flip {i}: {m}")
            for i, m in r["world_bad"][:8]:
                print(f"    flip {i} world: {m}")
            for i, m in r["sample_bad"][:8]:
                print(f"    sample {i}: {m}")
            for m in r["detail"][:3]:
                print("   ", m)
            rc |= 0 if r["identical"] else 1
    print("\nGATE", "IDENTICAL (exit 0)" if rc == 0 else "FAILED (exit 1)")
    if a.keep:
        import pickle
        Path(a.keep).write_bytes(pickle.dumps({f"{k[0]}/{k[1]}": v for k, v in results.items()}))
    return rc


# ---- speed ---------------------------------------------------------------------------------------------------------------------
def bucket(rows, lo, hi):
    return sum(c for a, c in rows if lo <= a < hi)


def rate(snap: str, names: list[str], turns: int, moving: bool, t0: int, out: dict, key: str, prof: bool = True) -> None:
    """Apply `names` live at turn t0 (the same T0 for every set), then fps / turns per second over `vbls` VBLs and a 1000-VBL profile."""
    h = Populous(snapshot=SNAP / f"{snap}.sav")
    try:
        time.sleep(0.5)
        live = live_image(names, None, f"rate_{snap}_{'_'.join(names) or 'none'}") if names else None
        cmds = []
        if live:
            spec = json.loads(Path(live + ".json").read_text())
            cmds.append(f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}")
        if moving:                                         # the VBL stub only: pointer moves every VBL, no flip hook, no table
            src = STUB_EQU + STUB2.replace("jsr     $%x.l" % CAPS3, "nop\n        nop\n        nop").replace("jsr     $%x.l" % CAPS5, "nop\n        nop\n        nop")
            p = h.R / "vbl.bin"
            p.write_bytes(vasm(src))
            cmds.append(f"loadbin {p} ${HOOK2:x}")
            cmds.append(f"w ${FLAGS:x} $00 $02")
            cmds.append(f"w ${ACIA_STORES[0]:x} " + " ".join(["$4e $71"] * (ACIA_STORES[1] // 2)))
            cmds.append(f"w ${VBL_SITE:x} $4e $b9 $00 $07 $61 $00")
        if live:
            for s in spec["sites"]:
                cmds.append(f"w ${s['addr']:x} " + " ".join(f"${x:02x}" for x in bytes.fromhex(s["new"])))
        done = h.R / "applied.bin"
        cmds.append(f"savebin {done} $14a28 8")
        f = h.R / "apply.txt"
        f.write_text("\n".join(cmds) + "\n")
        h.cmd(f"hatari-debug b pc = ${LOOP_PC:x} && (${TURN:x}).w = {t0} :trace :once :file {f}")
        ta, tb = t0 + 20, t0 + 20 + turns            # the same turn range in every run: VBLs for `turns` world turns
        for i, tt in enumerate((ta, tb)):
            ff = h.R / f"e{i}.txt"
            ff.write_text("e VBL\n")
            h.cmd(f"hatari-debug b pc = ${LOOP_PC:x} && (${TURN:x}).w = {tt} :trace :once :file {ff}")
            time.sleep(0.2)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (done.exists() and done.stat().st_size >= 8):
            if time.time() - t > 300:
                raise TimeoutError("apply breakpoint never fired")
            time.sleep(0.25)
        t = time.time()
        while len(re.findall(r"#(\d+) \(dec\)", h._logtext())) < 2:
            if time.time() - t > 600:
                raise TimeoutError("turn breakpoints never fired")
            time.sleep(0.5)
        va, vb = [int(x) for x in re.findall(r"#(\d+) \(dec\)", h._logtext())[-2:]]
        tps = turns * 50.0 / (vb - va)
        rec = {"turns": turns, "vbls": vb - va, "vbl_per_turn": round((vb - va) / turns, 3), "turns_per_sec": round(tps, 3),
               "site_14a28": done.read_bytes().hex()}
        r = {"vbls_per_frame": (vb - va) / turns}
        h.cmd("hatari-option --fast-forward off")
        time.sleep(1.0)
        if prof:
            rows = h.profile(1000)
            tot = sum(c for _, c in rows)
            vpf = r["vbls_per_frame"] or 1
            fl = 1000 / vpf
            rec.update({"profile_cycles": tot,
                        "ptr_cycles_per_vbl": round((bucket(rows, 0x16DEA, 0x16F12) + bucket(rows, 0xC2000, 0xC2400)) / 1000),
                        "copy_cycles_per_frame": round((bucket(rows, 0x14A28, 0x14A4E) + bucket(rows, 0xC2600, 0xC2700)) / fl)})
        out[key] = rec
    finally:
        h.close()


def cmd_fps(a) -> int:
    snaps = a.snap or ["busy_castles", "busy_quake_volcano"]
    base = [s for s in (a.set or [["none"]])]
    sets = [[] if s == ["none"] else s for s in base]
    out: dict = {}
    jobs = [(sn, ns) for sn in snaps for ns in sets]

    t0s = {sn: start_turn(sn) for sn in snaps}

    def do(j):
        sn, ns = j
        key = (sn, "+".join(ns) or "none")
        for attempt in range(2):
            try:
                rate(sn, ns, a.turns, a.moving, t0s[sn], out, key, not a.no_profile)
                return
            except Exception as ex:   # noqa: BLE001
                print("retry", key, repr(ex)[:200], flush=True)
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(do, jobs))
    for sn in snaps:
        for ns in sets:
            key = (sn, "+".join(ns) or "none")
            r = out.get(key)
            if r:
                print({"snap": sn, "set": key[1], "moving": a.moving, **{k: v for k, v in r.items()}})
    return 0


# ---- how much does the background copy really change? ----------------------------------------------------------------
def cmd_copy(a) -> int:
    """At every call of $14a28 from the main loop: the back buffer ($3c510) against the clean background ($3b016 = $78000)."""
    for sn in (a.snap or SNAPS):
        h = Populous(snapshot=SNAP / f"{sn}.sav")
        try:
            time.sleep(1.0)
            fifo = h.R / "pipe"
            os.mkfifo(fifo)
            chunks: queue.Queue = queue.Queue()
            stop = threading.Event()

            threading.Thread(target=fifo_reader, args=(fifo, chunks, stop), daemon=True).start()
            f = h.R / "c.txt"
            f.write_text(f"savebin {fifo} $3c510 $4\nsavebin {fifo} $3b016 $4\nsavebin {fifo} $3c506 $2\nsavebin {fifo} $4f500 $7d00\n"
                         f"savebin {fifo} $57200 $7d00\nsavebin {fifo} $78000 $7d00\n")
            h.cmd("hatari-debug b all")
            time.sleep(0.3)
            h.cmd(f"hatari-debug b pc = $b6f4 :trace :file {f}")        # the main loop's `jsr $14a28`
            h.cmd("hatari-option --fast-forward on")
            buf = bytearray()
            recs = []
            t = time.time()
            n = 4 + 4 + 2 + 3 * BUFLEN
            while len(recs) < a.flips and time.time() - t < 300:
                try:
                    buf += chunks.get(timeout=1.0)
                except queue.Empty:
                    continue
                while len(buf) >= n:
                    recs.append(bytes(buf[:n]))
                    del buf[:n]
            h.cmd("hatari-debug b all")
            h.cmd("hatari-option --fast-forward off")
            stop.set()
            rows_total, diff_total, diffrows, srcchg = [], [], [], 0
            prev_bg = None
            union = set()
            for r in recs:
                dst, src, turn = struct.unpack_from(">IIH", r, 0)
                bufs = {BUFA: r[10:10 + BUFLEN], BUFB: r[10 + BUFLEN:10 + 2 * BUFLEN]}
                bg = r[10 + 2 * BUFLEN:]
                cur = bufs[dst]
                if prev_bg is not None and bg != prev_bg:
                    srcchg += 1
                prev_bg = bg
                gl = [i for i in range(0, BUFLEN, 8) if cur[i:i + 8] != bg[i:i + 8]]
                union.update(gl)
                nd = len(gl)
                rows = sum(1 for y in range(200) if cur[y * 160:y * 160 + 160] != bg[y * 160:y * 160 + 160])
                diff_total.append(nd * 8)
                diffrows.append(rows)
            print({"snap": sn, "copies": len(recs), "bg_changed_between_copies": srcchg,
                   "dst_bytes_differing_from_bg_(8-byte granularity)": [min(diff_total), sum(diff_total) // len(diff_total), max(diff_total)],
                   "dst_rows_differing_(of_200)": [min(diffrows), sum(diffrows) // len(diffrows), max(diffrows)],
                   "union_over_frames_bytes": len(union) * 8,
                   "union_bounding_box_(rows, byte columns)": (min(u // 160 for u in union), max(u // 160 for u in union),
                                                               min(u % 160 for u in union), max(u % 160 for u in union) + 7),
                   })
        finally:
            h.close()
    return 0


# ---- registers / flags / memory of the new copy against the original, same inputs ---------------------------------------
def cpytest_source(n: int) -> str:
    """A test stub (runs in place of `jsr $db8a`, once): for every trial the ORIGINAL $14a28 (a verbatim copy at $77000) and the new
    one ($c2600) run on the same random registers, a chosen CCR and a chosen last longword of the background; registers + SR are
    stored after each, and the 32,128-byte window around the back buffer (64 sentinel bytes before / after, the buffer pre-filled with a pattern) is compared."""
    src = ["WIN\tequ\t$60000", "RES\tequ\t$68000", "TAB\tequ\t$75000", "\torg\t$72000",
           "test:\tmovem.l d0-d7/a0-a6,-(sp)"]
    for i in range(n):
        ccr = i % 32
        last = (0x00000000, 0x80000001, 0x7FFFFFFF)[i % 3]
        for which, entry in (("o", 0x76A00), ("n", 0xC2600)):
            src += [f"\tmove.l\t#${last:08x},d0", "\tbsr\tprep",
                    f"\tmovem.l TAB+{64 * i}.l,d0-d7/a0-a6", f"\tmove.w\t#{ccr},ccr", f"\tjsr\t${entry:x}.l",
                    f"\tmovem.l d0-d7/a0-a6,RES+{128 * i + (0 if which == 'o' else 64)}.l",
                    f"\tmove.w\tsr,RES+{128 * i + (60 if which == 'o' else 124)}.l"]
            src += ["\tbsr\tsnap"] if which == "o" else [f"\tbsr\tcmpw", f"\tmove.w\td0,RES+{128 * i + 62}.l"]
    src += ["\tmovem.l (sp)+,d0-d7/a0-a6", "\tmove.l\t#$0000db8a,$b808.l", "\tmove.w\t#$600d,RES+$3100.l", "\tjmp\t$db8a.l",
            # prep: d0 = last longword of the background; sentinels around the back buffer
            "prep:\tmovea.l $3b016.l,a0", "\tmove.l\td0,31996(a0)", "\tmovea.l $3c510.l,a0", "\tmove.l\t#$a5a5a5a5,d0",
            "\tmove.w\t#8031,d1", "\tlea\t-64(a0),a1", ".s1:\tmove.l\td0,(a1)+", "\tdbra\td1,.s1", "\trts",
            # snap: copy the window to WIN;  cmpw: d0 = 0 when the window equals WIN
            "snap:\tmovea.l $3c510.l,a0", "\tlea\t-64(a0),a0", "\tlea\tWIN.l,a1", "\tmove.w\t#8031,d1",
            ".c1:\tmove.l\t(a0)+,(a1)+", "\tdbra\td1,.c1", "\trts",
            "cmpw:\tmovea.l $3c510.l,a0", "\tlea\t-64(a0),a0", "\tlea\tWIN.l,a1", "\tmove.w\t#8031,d1", "\tmoveq\t#0,d0",
            ".c2:\tcmpm.l\t(a1)+,(a0)+", "\tbeq.s\t.c3", "\tmoveq\t#1,d0", ".c3:\tdbra\td1,.c2", "\trts"]
    return "\n".join(src) + "\n"


def cmd_cpytest(a) -> int:
    """pop_bgcopy against the original $14a28: random registers, all 32 CCR inputs, three last longwords, memory window."""
    import random
    import poppatch
    n = a.trials
    live = live_image(["pop_bgcopy"], a.mutant, "cpytest" + (a.mutant or ""))
    spec = json.loads(Path(live + ".json").read_text())
    rnd = random.Random(5)
    regs = [[rnd.getrandbits(32) for _ in range(15)] for _ in range(n)]
    tab = b"".join(struct.pack(">15I", *r) + b"\0\0\0\0" for r in regs)
    code = vasm(cpytest_source(n))
    orig = poppatch.expected_ram(0x14A28, 38, 1)
    h = Populous(snapshot=SNAP / "busy_castles.sav")
    try:
        time.sleep(0.5)
        t0 = h.peekw(TURN) + 100
        files = {0x72000: code, 0x75000: tab, 0x76A00: orig}
        cmds = []
        for addr, b in files.items():
            pth = h.R / f"f{addr:x}.bin"
            pth.write_bytes(b)
            cmds.append(f"loadbin {pth} ${addr:x}")
        cmds.append(f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}")      # blob only: the site is NOT patched
        cmds.append("w $b808 $00 $07 $20 $00")                                              # jsr $db8a -> jsr $72000
        f = h.R / "apply.txt"
        f.write_text("\n".join(cmds) + "\n")
        out = h.R / "res.bin"
        fs = h.R / "save.txt"
        fs.write_text(f"savebin {out} $68000 $3200\n")
        h.cmd(f"hatari-debug b pc = ${LOOP_PC:x} && (${TURN:x}).w = {t0} :trace :once :file {f}")
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while True:                                   # the stub writes $600d to RES+$7ff0 when done: poll with a breakpoint on the next pass
            time.sleep(1.0)
            if time.time() - t > 240:
                raise TimeoutError("cpytest did not finish")
            if h.peekw(0x68000 + 0x3100) == 0x600D:
                break
        h.cmd("hatari-debug b all")
        h.debug(f"savebin {out} $68000 $3200", 2.0)
        time.sleep(2.0)
        res = out.read_bytes()
        bad = 0
        for i in range(n):
            ro = res[128 * i:128 * i + 64]
            rn = res[128 * i + 64:128 * i + 128]
            memok = struct.unpack_from(">H", res, 128 * i + 62)[0]
            so, sn = struct.unpack_from(">H", res, 128 * i + 60)[0] & 0x1F, struct.unpack_from(">H", res, 128 * i + 124)[0] & 0x1F
            if ro[:60] != rn[:60] or so != sn or memok:
                bad += 1
                if bad <= 5:
                    print(f"trial {i}: regs equal {ro[:60] == rn[:60]} ccr orig {so:05b} new {sn:05b} window differs {memok}; "
                          f"first differing reg {[k for k in range(15) if ro[4 * k:4 * k + 4] != rn[4 * k:4 * k + 4]][:3]}")
        print(f"cpytest: {n} trials (random d0-d7/a0-a6, CCR 0..31 each three times, last longword 0 / negative / positive), "
              f"registers + CCR + the 32,128-byte window incl. sentinels compared: {n - bad} identical, {bad} different")
        return 1 if bad else 0
    finally:
        h.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--snap", nargs="*")
    g.add_argument("--set", nargs="+", action="append")
    g.add_argument("--flips", type=int)
    g.add_argument("--mutant", choices=sorted(MUTANTS))
    g.add_argument("--keep")
    g.add_argument("--keep-stale", action="store_true", help="do not remove the stale pointer restore race (default: removed in both runs)")
    f = sub.add_parser("fps")
    f.add_argument("--snap", nargs="*")
    f.add_argument("--set", nargs="+", action="append")
    f.add_argument("--turns", type=int, default=150, help="world turns timed (VBLs elapsed between two fixed turns)")
    f.add_argument("--moving", action="store_true")
    f.add_argument("--no-profile", action="store_true")
    c = sub.add_parser("copy")
    c.add_argument("--snap", nargs="*")
    c.add_argument("--flips", type=int, default=40)
    ct = sub.add_parser("cpytest")
    ct.add_argument("--trials", type=int, default=96)
    ct.add_argument("--mutant", choices=[k for k, v in MUTANTS.items() if v[0] == "pop_bgcopy"])
    sub.add_parser("mutants")
    a = ap.parse_args()
    if a.cmd == "gate":
        global KEEP_STALE
        KEEP_STALE = a.keep_stale
        return cmd_gate(a)
    if a.cmd == "fps":
        return cmd_fps(a)
    if a.cmd == "copy":
        return cmd_copy(a)
    if a.cmd == "cpytest":
        return cmd_cpytest(a)
    for k, (f_, ed) in MUTANTS.items():
        print(f"{k:12s} {f_}: " + " | ".join(o.strip()[:40] + " -> " + n.strip()[:30] for o, n in ed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
