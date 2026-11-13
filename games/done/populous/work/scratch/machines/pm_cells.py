"""PopMachines cold-boot cells (test scaffolding only): TT / Falcon / STE60 / Mega STE, floppy or HD.

    python3 pm_cells.py CELL MEDIUM PATH [--busy] [--turns 300] [--extra "..."] [--shots PREFIX]

CELL  tt | falcon | ste | ste60 | megaste        MEDIUM  floppy | acsi | gemdos
Reaches the Genesis START page by mouse, clicks START GAME, checks the main loop, optionally builds the busy scene and runs
`--turns` world turns, printing raw RAM values.  Game addresses are shifted by D = the payload's RELDLT ($B3104) = the
program's load address minus $AD96.
"""
import argparse, re, struct, subprocess, sys, tempfile, time
from pathlib import Path
from mm import *
from nav import *
import poppatch as pp

SHOTS = GAME / "work" / "shots"
# (shot offset of the picture, home of the pointer in shot coordinates) per cell and phase: the Falcon's window changes
# size with the video mode (menu 680 px wide, picture at x 40; game 726 px wide, picture at x 85).
GEOM = {("tt", "menu"): ((0, 0), (11, 9)), ("tt", "game"): ((0, 0), (11, 9)),
        ("falcon", "menu"): ((40, 0), (51, 9)), ("falcon", "game"): ((85, 0), (96, 9))}
CONQUEST, START_B = (545, 350), (175, 350)          # TT shot coordinates; add the offset for the other machines


def goto_shot(h, cell, phase, sx, sy):
    """Move the game pointer to (sx, sy) given in TT-shot coordinates (picture at 0,0)."""
    (ox, oy), (hx, hy) = GEOM[(cell, phase)]
    h.goto(sx + ox + 96, sy + oy + 58, home_xy=(hx + 96, hy + 58))


def crop_ok(h, ref, box, tol=14):
    p = f"/tmp/_pmc_{id(h)}.png"
    for _ in range(3):
        try:
            h.shot(p)
            return crop_match(p, ref, box, tol)
        except Exception:
            time.sleep(0.7)
    return False

def wait_for_crop(h, ref, box, timeout, tol=14):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(1.5)
        if crop_ok(h, ref, box, tol):
            return time.time() - t0
    return None


NOMENU = False                 # the title program died before its menu (Falcon without pop_fal_ym_demo): the game follows on its own


def to_start_page(h, cell, shots=None):
    (ox, oy), _ = GEOM[(cell, "menu")]
    menu = REF / ("tt_menu_buttons.png" if cell == "tt" else "falcon_menu_buttons.png")
    mbox = (460 + ox, 310 + oy, 640 + ox, 395 + oy)
    t = None if NOMENU else wait_for_crop(h, menu, mbox, 150)
    print("menu after", t)
    if t is None and not NOMENU:
        return False
    if shots:
        h.shot(f"{shots}_menu.png")
    if not NOMENU:
        goto_shot(h, cell, "menu", *CONQUEST)
        h.click(hold=0.4)
    sref = REF / ("tt_start_page.png" if cell == "tt" else "falcon_start_page.png")
    (gx, gy), _ = GEOM[(cell, "game")]
    sbox = (60 + gx, 105 + gy, 340 + gx, 225 + gy)
    if not sref.exists():
        time.sleep(80)
        h.shot(f"/tmp/_pmc_start_{cell}.png")
        print("no start-page reference for", cell, "-> /tmp/_pmc_start_%s.png" % cell)
        return None
    t = wait_for_crop(h, sref, sbox, 180)
    print("start page after", t)
    return t is not None


def delta(h):
    hdr = mem(h, 0xB3000, 4)
    if hdr.replace(" ", "") != "504f5050":
        return None
    return h.peekl(0xB3104)


def check_play(h, D):
    sig = mem(h, 0xB6F4 + D, 6)
    ok = sig.replace(" ", "") == "4eb9" + "%08x" % (0x14A28 + D)
    t = h.peekw(0x3C506 + D)
    time.sleep(2.0)
    t2 = h.peekw(0x3C506 + D)
    return ok, t, t2


SCENE_STUB = """
    org $CE000
    movem.l d0-d7/a0-a6,-(sp)
    lea $34c22,a0
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
    jsr $c12c
    jsr $c2b8
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
    jsr $114c4
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
    move.l #$0000da90,$b72a
    movem.l (sp)+,d0-d7/a0-a6
    jmp $da90
tab:
    dc.w TAB,-1
"""


def busy_scene(h, D, life=300, seed=2, view=(44, 32)):
    """Populous.busy_scene with every game address moved by D and the stub put in the payload's free area ($CE000)."""
    import random
    dump = h.R / "scene.bin"
    h.dump(str(dump), 0x34C22 + D, 0x2102)
    time.sleep(1.0)
    alt = dump.read_bytes()

    def hh(x, y):
        return struct.unpack_from(">H", alt, 2 * (x + 65 * y))[0]
    land = [(x, y) for y in range(64) for x in range(64) if all(hh(x + dx, y + dy) > 0 for dx in (0, 1) for dy in (0, 1))]
    rnd = random.Random(seed)
    nw = [c for c in land if c[0] < 18 and c[1] < 22]
    east = [c for c in land if c[0] >= 41 and 28 <= c[1] <= 44]
    se = [c for c in land if c[0] >= 41 and c[1] >= 46]
    sw = [c for c in land if c[0] < 30 and c[1] >= 50]
    tab = []
    for x, y in rnd.sample(nw, 18):
        tab += [0, x, y]
    ee = rnd.sample(east, 36)
    for x, y in ee[:18]:
        tab += [0, x, y]
    for x, y in ee[18:]:
        tab += [1, x, y]
    for x, y in rnd.sample(se, 14) + rnd.sample(sw, 10):
        tab += [1, x, y]
    lines = pp.shift_game_literals(SCENE_STUB.replace("LIFE", str(life)).replace("TAB", ",".join(map(str, tab))).splitlines(),
                                   pp.TNOM, pp.PROG_END[1])
    src = h.R / "scene.s"
    out = h.R / "s.bin"
    src.write_text(f"GD equ {D}\n" + "\n".join(lines) + "\n")
    r = subprocess.run(["vasmm68k_mot", "-Fbin", "-quiet", "-o", str(out), str(src)], capture_output=True, text=True)
    if r.returncode or r.stderr:
        raise RuntimeError(r.stderr)
    h.debug(f"w ${0xEE16 + D:x} $60", 0.4)
    h.debug(f"loadbin {out} $CE000", 0.8)
    h.debug(f"w ${0x37EB8 + D:x} $00 ${view[0]:02x}", 0.3)
    h.debug(f"w ${0x249EC + D:x} $00 ${view[1]:02x}", 0.3)
    h.debug(f"w ${0xB72A + D:x} $00 $0c $e0 $00", 0.5)        # jsr $da90 -> jsr $CE000, once
    time.sleep(2)


def turns(h, D, n, timeout=600):
    """Run until the turn word has advanced by n; returns (turn0, turn1, seconds). Prints samples."""
    t0 = h.peekw(0x3C506 + D)
    start = time.time()
    last = t0
    while True:
        time.sleep(5)
        t = h.peekw(0x3C506 + D)
        print(f"  turn {t}  npeeps {h.peekw(0x3C520 + D)}  armageddon {h.peekw(0x3D562 + D)}  (+{(t - t0) & 0xffff})")
        last = t
        if ((t - t0) & 0xffff) >= n or time.time() - start > timeout:
            return t0, t, time.time() - start


def sound_check(h, D, blob=0xB9040):
    """Earthquake (command 3 at the view) with plenty of mana: the game's effect sample player runs; count hits of the blob."""
    h.debug("w $%x %s" % (0x3B270 + D, " ".join("$%02x" % b for b in struct.pack(">I", 300000))), 0.3)
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${blob:x} :trace")
    time.sleep(0.5)
    h.debug("w $%x $03 $2c $20" % (0x21E4A + D), 0.5)
    time.sleep(25)
    log = h._logtext()[n0:]
    hits = len(re.findall(r"0*%x\b" % blob, log, re.I))
    h.debug("b all", 0.3)
    print(f"sound check: {hits} log line(s) mentioning ${blob:x} after the earthquake command; bus errors in log: "
          f"{len(re.findall('Bus error', h._logtext(), re.I))}")
    print(log[:600])
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cell")
    ap.add_argument("medium")
    ap.add_argument("path")
    ap.add_argument("--busy", action="store_true")
    ap.add_argument("--turns", type=int, default=300)
    ap.add_argument("--extra", default="")
    ap.add_argument("--mem", type=int)
    ap.add_argument("--tos")
    ap.add_argument("--shots", default=None)

    ap.add_argument("--clock", type=int)
    ap.add_argument("--sound", action="store_true", help="after play: earthquake, count hits of the Falcon YM blob")
    ap.add_argument("--dump", default=None, help="write the game's text+data (RAM $AD96..$3E000 + D) here once in play")
    ap.add_argument("--nomenu", action="store_true")
    ap.add_argument("--delta0", action="store_true", help="old payload without the meta words: D = 0")
    a = ap.parse_args()
    global NOMENU
    NOMENU = a.nomenu
    SHOTS.mkdir(parents=True, exist_ok=True)
    pre = str(SHOTS / a.shots) if a.shots else None
    h = start(a.cell, a.medium, a.path, extra=a.extra.split(), mem=a.mem, tos=a.tos)
    try:
        if a.cell in ("tt", "falcon") and NOMENU:
            time.sleep(70)                 # the title program died; the game starts straight into the world
        elif a.cell in ("tt", "falcon"):
            r = to_start_page(h, a.cell, pre)
            if not r:
                print("START page not reached:", r)
                return 1
            goto_shot(h, a.cell, "game", *START_B)
            h.click(hold=0.4)
        else:
            time.sleep(16)
            if a.clock:
                h.set_cpuclock(a.clock)
                if a.cell == "megaste":
                    print("Mega STE $ff8e21 before:", mem(h, 0xFF8E21, 1))
                    h.debug("w $ff8e21 $03", 0.5)            # bit 0 16 MHz, bit 1 cache on
                    print("Mega STE $ff8e21 after:", mem(h, 0xFF8E21, 1))
            h.key("space", 0.5)
            time.sleep(28)
            if pre:
                h.shot(f"{pre}_menu.png")
            h.goto(*CONQUEST_XY, home_xy=HOME)
            h.click(hold=0.4)
            time.sleep(9)
            h.goto(*START_XY, home_xy=HOME)
            h.click(hold=0.4)
        time.sleep(10)
        D = 0 if a.delta0 else delta(h)
        print("payload header:", mem(h, 0xB3000, 16), " D =", D)
        Dg = D or 0
        print("check_play (sig ok, turn, turn+2s):", check_play(h, Dg))
        if pre:
            h.shot(f"{pre}_play.png")
        if a.dump:
            h.dump(a.dump, 0xAD96 + Dg, 0x3E000 - 0xAD96)
            time.sleep(2)
        if a.busy:
            busy_scene(h, Dg)
            print("busy scene set up; turns:")
            t0, t1, secs = turns(h, Dg, a.turns)
            print(f"{(t1 - t0) & 0xffff} turns in {secs:.1f} s wall")
            if pre:
                h.shot(f"{pre}_busy.png")
        if a.sound:
            sound_check(h, Dg)
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
