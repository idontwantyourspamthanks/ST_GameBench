#!/usr/bin/env python3
"""Gates for pop2_noquest (the manual question, work/notes/noquest.md).

    python3 tools/p2noquest.py cold --build DIR --machine M --tos T --mem KB --path conquest|custom|deity|load [--answer] [--tag X] [--extra "--mmu true"]
        cold boot DIR (an HD build, or a floppy .st with --floppy FILE), walk the menu path, record a screenshot at every step
        (work/shots/noquest/<tag>_NN_<step>.png), count the hits of the question routine ($148b2) with a debugger breakpoint, and
        report $39612 (the answered flag), $3960a, the marker and whether the turn counter moves.  --answer: the build still asks
        (the reference): the OK button is clicked when the screen appears.

    python3 tools/p2noquest.py pre  --build DIR [--out work/snapshots/pre_question.sav]
        cold boot the build that still asks, play to PROCEED and FREEZE the game at the instant before the question: the first
        entry of the object-draw handler $20a02 with $39612 = 0 and $3960a = 1 patches `bra.s *` over the bne at $20a08 (a hook at
        $20a02, so the instruction at the PC is not touched), the game spins there, savemem writes the snapshot.

    python3 tools/p2noquest.py replay --mode ask|skip|negctl [--turns N] [--out DIR]
        restore the frozen snapshot, write the 22 bytes of $20a02 (the original: the question is asked, the OK button is clicked;
        or pop2_noquest's: skipped) and `r pc=$20a02`, then record at every pass top ($1254e) the world RAM $39600-$473ff,
        and the whole 2 MB RAM at the first pass top after the question / skip and at turn START+N.
    python3 tools/p2noquest.py compare DIR_A DIR_B      world by turn A vs B (p2tick.mask_world), RAM diff of the full dumps
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(HERE), str(GAME.parent.parent.parent / "tools")]
from populous2 import Populous2  # noqa: E402
from stharness import TOS  # noqa: E402

QUEST = 0x148B2          # the question routine (one caller: $20a12)
FLAG = 0x39612           # "answered": written only by the success path ($14aac)
FADE = 0x3960A           # "last palette fade went to a real palette"
SHOTS = GAME / "work" / "shots" / "noquest"


class Run:
    def __init__(self, h, tag):
        self.h, self.tag, self.n = h, tag, 0
        SHOTS.mkdir(parents=True, exist_ok=True)
        f = h.R / "qhit.txt"
        f.write_text("e VBL\n")
        h.debug("b all", 0.3)
        self.start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${QUEST:x} :trace :file {f}")
        time.sleep(0.5)

    def hits(self):
        return len(re.findall(r"> e VBL", self.h._logtext()[self.start:]))

    def state(self):
        h = self.h
        return f"flag$39612={h.peekw(FLAG):#x} $3960a={h.peekw(FADE):#x} turn={h.peekw(h.TURN):#x} question_hits={self.hits()}"

    def snap(self, step):
        self.n += 1
        p = SHOTS / f"{self.tag}_{self.n:02d}_{step}.png"
        self.h.shot(str(p))
        print(f"  shot {p.name}: {self.state()}", flush=True)


def question_visible(run, timeout):
    t = time.time()
    while time.time() - t < timeout:
        if run.hits():
            return True
        time.sleep(1.0)
    return False


def deity(run, name="zeus"):
    h = run.h
    h._click(384, 241, 3)                # CREATE YOUR DEITY
    run.snap("deity_screen")
    h._click(260, 98, 1.0)
    for ch in name:
        h.key(ch, 0.3)
        time.sleep(0.4)
    h.key("Return", 0.3)
    time.sleep(1.0)
    h._click(424, 418, 3)                # PROCEED -> main menu
    run.snap("back_to_menu")


def finish(run, answer, wait_q):
    """The question screen may appear now: with --answer wait for it, shot it and click OK; without, it must not."""
    h = run.h
    if answer:
        ok = question_visible(run, wait_q)
        time.sleep(3)
        run.snap("question" if ok else "NO_question_seen")
        if ok:
            h._click(400, 420, 15)
    else:
        time.sleep(wait_q)
        run.snap("after_load_wait")
        time.sleep(10)
    run.snap("play")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cold")
    c.add_argument("--build", default="build/nq_hd")
    c.add_argument("--floppy", default=None, help="a bootable .st (instead of --build)")
    c.add_argument("--machine", default="ste")
    c.add_argument("--tos", default=None)
    c.add_argument("--mem", type=int, default=2048)
    c.add_argument("--path", default="conquest", choices=["conquest", "custom", "deity", "load"])
    c.add_argument("--answer", action="store_true")
    c.add_argument("--tag", default=None)
    c.add_argument("--extra", default="")
    pr = sub.add_parser("pre")
    pr.add_argument("--build", default="build/nq_ref")
    pr.add_argument("--out", default=str(GAME / "work" / "snapshots" / "pre_question.sav"))
    rp = sub.add_parser("replay")
    rp.add_argument("--mode", choices=["ask", "skip", "negctl"], required=True)
    rp.add_argument("--turns", type=int, default=130)
    rp.add_argument("--snap", default=str(GAME / "work" / "snapshots" / "pre_question.sav"))
    rp.add_argument("--out", default=None)
    cp = sub.add_parser("compare")
    cp.add_argument("a"); cp.add_argument("b")
    cp.add_argument("--first", type=int, default=0, help="first turn to compare")
    a = ap.parse_args()
    {"cold": cold, "pre": pre, "replay": replay, "compare": compare}[a.cmd](a)


def cold(a):
    tag = a.tag or f"{a.machine}{a.mem}_{a.path}"
    extra = a.extra.split()
    kw = dict(machine=a.machine, memsize_kb=a.mem, extra=extra)
    if a.tos:
        kw["tos"] = TOS[a.tos]
    if a.floppy:
        kw["game_dir"] = GAME / "build" / "nq_empty"
        (GAME / "build" / "nq_empty").mkdir(exist_ok=True)
        kw["files"] = []
        import shutil, tempfile
        d = Path(tempfile.mkdtemp(prefix="nqfl-")) / "pop2_floppy.st"          # a scratch copy: the build's .st stays untouched
        shutil.copy(a.floppy, d)
        kw["extra"] = extra + ["--disk-a", str(d)]
        kw["autorun"] = None
    else:
        kw["game_dir"] = GAME / a.build
    h = Populous2(**kw)
    try:
        t0 = time.time()
        if a.floppy:
            ok = floppy_to_menu(h)
        else:
            ok = h.boot_to_menu()
        run = Run(h, tag)
        print(f"{tag}: menu={ok} after {time.time() - t0:.0f} s marker {h.marker()!r} mem {a.mem} KB {a.machine}", flush=True)
        run.snap("menu")
        if a.path == "deity":
            deity(run)
        elif a.path == "load":
            h._click(384, 289, 8)
            run.snap("load_screen")
            h._click(288, 418, 12)
            run.snap("load_clicked")
        elif a.path == "conquest":
            deity(run)
            h._click(384, 258, 8)
            run.snap("battle_sheet")
            h._click(216, 448, 12)
            run.snap("proceed_loading")
            finish(run, a.answer, 40 if a.answer else 25)
        elif a.path == "custom":
            deity(run)
            h._click(384, 273, 8)
            run.snap("custom_clicked")
            finish(run, a.answer, 40 if a.answer else 25)
        t = h.peekw(h.TURN)
        time.sleep(3)
        t2 = h.peekw(h.TURN)
        print(f"RESULT {tag}: marker {h.marker()!r} {run.state()} turn {t:#x} -> {t2:#x} in_play={h.peekl(0x70) == 0x18FA and t != t2}", flush=True)
    finally:
        h.close()


def floppy_to_menu(h, timeout=300):
    t0 = time.time()
    time.sleep(14)
    while time.time() - t0 < timeout:
        h.key("space", 0.6)
        time.sleep(6)
        if h.peekl(0x70) == 0x18FA:
            time.sleep(3)
            return True
    return False



# ---------------------------------------------------------------------------------------------------------------------------------
# the frozen snapshot and the replay (world state after skipping == after answering)
# ---------------------------------------------------------------------------------------------------------------------------------
ORIG22 = bytes.fromhex("4a7900039612660e4a790003960a67064eb9000148b2")     # $20a02 in the unpatched game
NEW22 = bytes.fromhex("33fc000100039612600c4e714e714e714e714e714e71")      # pop2_noquest (pop2patch.py build output)
TOP, TURNL = 0x1254E, 0x3979A
WORLD = (0x39600, 0xDE00)


def pre(a):
    h = Populous2(game_dir=GAME / a.build)
    try:
        assert h.boot_to_menu()
        h._click(384, 241, 3)
        h._click(260, 98, 1.0)
        for ch in "zeus":
            h.key(ch, 0.3)
            time.sleep(0.4)
        h.key("Return", 0.3)
        time.sleep(1)
        h._click(424, 418, 3)
        h._click(384, 258, 8)
        f = h.R / "freeze.txt"
        f.write_text("w $20a08 $60 $fe\n")
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b pc = $20a02 && ($39612).w = 0 && ($3960a).w = 1 :trace :once :file {f}")
        time.sleep(0.5)
        h._click(216, 448, 3)
        t = time.time()
        while h.peekw(0x20A08) != 0x60FE and time.time() - t < 120:
            time.sleep(1)
        print(f"frozen: $20a08 = {h.peekw(0x20A08):#06x} flag $39612 = {h.peekw(FLAG):#x} turn = {h.peekl(TURNL):#x}")
        print(h.debug("r", 1)[-420:])
        h.savemem(a.out)
        print("snapshot", a.out, Path(a.out).stat().st_size, "bytes")
    finally:
        h.close()


def wbytes(addr, bs):
    return f"w ${addr:x} " + " ".join(f"${b:02x}" for b in bs)


def replay(a):
    import os
    import select
    import threading
    out = Path(a.out or GAME / "work" / "scratch" / f"nq_{a.mode}")
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    h = Populous2(snapshot=a.snap)
    stop = threading.Event()
    buf = bytearray()
    try:
        fifo = h.R / "w.fifo"
        os.mkfifo(fifo)
        fd = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)

        def drain():
            while not stop.is_set():
                r, _, _ = select.select([fd], [], [], 0.05)
                if r:
                    try:
                        d = os.read(fd, 1 << 20)
                    except BlockingIOError:
                        continue
                    if d:
                        buf.extend(d)
                    else:
                        time.sleep(0.002)
        th = threading.Thread(target=drain, daemon=True)
        th.start()
        time.sleep(1.5)
        t_start = h.peekl(TURNL)
        spin = h.peekw(0x20A08)
        print(f"restored: turn {t_start}, $20a08 = {spin:#06x} (0x60fe = the freeze loop), flag {h.peekw(FLAG):#x}", flush=True)
        assert spin == 0x60FE and h.peekw(FLAG) == 0
        cmds = [wbytes(0x20A02, ORIG22 if a.mode == "ask" else NEW22), "r pc=$20a02"]
        (h.R / "qhit.txt").write_text("e $148b2\n")
        cmds.append(f"b pc = ${QUEST:x} :trace :file {h.R / 'qhit.txt'}")
        if a.mode == "negctl":
            cmds.insert(0, "w $3e100 $5a")          # the control: a byte of the world differs (must be reported)
        # world at every pass top
        (h.R / "top.txt").write_text("\n".join([f"e ${TOP:x}", "e VBL", f"e (${TURNL:x}).l", f"savebin {fifo} ${WORLD[0]:x} ${WORLD[1]:x}"]) + "\n")
        # the whole RAM at the first pass top after the question / skip, and at START+N
        (h.R / "ram1.txt").write_text(f"e ${TOP:x}\ne VBL\ne (${TURNL:x}).l\nsavebin {out}/ram_first.bin $0 $200000\n")
        (h.R / "ramN.txt").write_text(f"e ${TOP:x}\ne VBL\ne (${TURNL:x}).l\nsavebin {out}/ram_last.bin $0 $200000\nb all\nsavebin {out}/end.flag $0 2\n")
        cmds += [f"b pc = ${TOP:x} :trace :file {h.R / 'top.txt'}",
                 f"b pc = ${TOP:x} :trace :once :file {h.R / 'ram1.txt'}",
                 f"b pc = ${TOP:x} && (${TURNL:x}).l = {t_start + a.turns} :trace :once :file {h.R / 'ramN.txt'}"]
        (h.R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        # the apply must happen with the CPU in the freeze loop: arm it at pc = $20a08
        h.cmd(f"hatari-debug b pc = $20a08 :trace :once :file {h.R / 'apply.txt'}")
        time.sleep(0.4)
        if a.mode == "ask":
            t = time.time()
            while not _qhit(h, start):
                if time.time() - t > 60:
                    raise TimeoutError("the question never appeared")
                time.sleep(0.5)
            time.sleep(2)
            h.shot(str(SHOTS / "replay_ask_question.png"))
            print("question on screen (shot replay_ask_question.png); clicking OK", flush=True)
            h._click(400, 420, 2)
            time.sleep(1)
        else:
            time.sleep(1)
            h.goto(400, 420, home_xy=(96, 58))      # the pointer where the answered run clicks OK (no click), so the pointer sprite and $393fa/c match
            time.sleep(2)
            h.shot(str(SHOTS / f"replay_{a.mode}_after_skip.png"))
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (out / "end.flag").exists():
            if time.time() - t > 900:
                raise TimeoutError(h._logtext()[-1500:])
            time.sleep(0.5)
        time.sleep(1.5)
        text = h._logtext()[start:]
        (out / "log.txt").write_text(text)
    finally:
        stop.set()
        h.close()
    n = len(buf) // WORLD[1]
    tops = []
    for i in range(n):          # the turn label comes from the dumped world itself ($3979a, long), not from the log (two breakpoints share the pc)
        blob = bytes(buf[i * WORLD[1]:(i + 1) * WORLD[1]])
        turn = int.from_bytes(blob[TURNL - WORLD[0]:TURNL - WORLD[0] + 4], "big")
        (out / f"world_{i:04d}_t{turn}.bin").write_bytes(blob)
        tops.append(turn)
    print(f"{a.mode}: {n} pass tops recorded, turns {tops[0] if tops else '-'}..{tops[-1] if tops else '-'}; out {out}")


NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")


def _qhit(h, start):
    return "> e $148b2" in h._logtext()[start:]



def _worlds(d):
    r = {}
    for f in sorted(Path(d).glob("world_*_t*.bin")):
        r.setdefault(int(f.stem.split("_t")[1]), f.read_bytes())
    return r


def compare(a):
    import p2tick as T
    A, B = _worlds(a.a), _worlds(a.b)
    common = sorted(t for t in A if t in B and t >= a.first)
    bad = [t for t in common if T.mask_world(A[t]) != T.mask_world(B[t])]
    print(f"world by turn: A {len(A)} turns ({min(A)}..{max(A)}), B {len(B)} turns ({min(B)}..{max(B)}), compared {len(common)} turns {common[0]}..{common[-1]} (>= {a.first}), masks {T.MASKS}")
    print("RESULT world by turn:", "IDENTICAL" if not bad else f"DIFFER at {len(bad)} turns, first {bad[:5]}")
    for t in bad[:2]:
        rg = T.diff_ranges(T.mask_world(A[t]), T.mask_world(B[t]), WORLD[0])
        print(f"  turn {t}: {len(rg)} ranges", [(hex(s), hex(e), A[t][s - WORLD[0]:e - WORLD[0]][:8].hex(), B[t][s - WORLD[0]:e - WORLD[0]][:8].hex()) for s, e in rg[:8]])
    for nm in ("ram_first.bin", "ram_last.bin"):
        pa, pb = Path(a.a) / nm, Path(a.b) / nm
        if pa.exists() and pb.exists():
            x, y = pa.read_bytes(), pb.read_bytes()
            rg = T.diff_ranges(x, y, 0, gap=16)
            tot = sum(e - s for s, e in rg)
            print(f"{nm}: {len(x)} B, {len(rg)} differing ranges, {tot} bytes differ")
            for s, e in rg:
                print(f"   ${s:06x}-${e:06x} ({e - s:5d} B)  A {x[s:s + 8].hex()}  B {y[s:s + 8].hex()}")


if __name__ == "__main__":
    main()
