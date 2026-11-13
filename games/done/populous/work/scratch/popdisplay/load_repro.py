#!/usr/bin/env python3
"""In-game SAVE, LOAD and MOVE TO NEXT MAP on an HD build (test scaffolding for work/notes/display.md section 9).
    python3 load_repro.py TAG BUILD [ste|megaste] [1.62|2.06] [cpuclock] [--nextmap]
Prints the result dict; breakpoints: bad y ($24788 > 199 after the handler), and with a fix build the dropped packets."""
import re
import sys
import time
from pathlib import Path

GAME = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(GAME / "tools")]
from populous import Populous, HOME, CONQUEST_XY, START_XY  # noqa: E402
from stharness import TOS  # noqa: E402

SH = GAME / "work" / "shots" / "pdfix"
SH.mkdir(parents=True, exist_ok=True)


def clk(h, x, y, hold=0.4, wait=2.0):
    h.goto(x, y, home_xy=HOME)
    h.click(hold=hold)
    time.sleep(wait)


def boot_play(build, machine, tos, mem, cpu):
    h = Populous(game_dir=GAME / build, snapshot=None, memsize_kb=mem, machine=machine, tos=TOS[tos])
    time.sleep(16)
    if cpu:
        h.set_cpuclock(cpu)
    h.key("space", 0.5)
    time.sleep(26 if machine == "ste" else 23)
    h.goto(*CONQUEST_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(9)
    h.goto(*START_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(12)
    for _ in range(6):
        if h.in_play():
            break
        time.sleep(5)
    return h


def run(tag, build, machine="ste", tos="1.62", cpu=None, nextmap=False, mem=1024):
    h = boot_play(build, machine, tos, mem, cpu)
    out = {"tag": tag, "in_play": h.in_play()}
    try:
        Path("/tmp/pdfix_m.txt").write_text("m $20061 6\nm $2478a 6\nr\n")
        h.debug("b all", 0.3)
        h.debug("b pc = $2005c && ($24788).w > 199 :trace :file /tmp/pdfix_m.txt", 0.5)         # a bad y was stored (no fix)
        if "fix" in build:                                                                         # a packet dropped by pop_ptrfix
            for c in ("($20064).w > 199", "($20062).w > 319", "($20061).b > 15"):
                h.debug(f"b pc = $c283c && {c} :trace :file /tmp/pdfix_m.txt", 0.5)
        clk(h, 706, 410); clk(h, 350, 308); clk(h, 400, 385)            # GAME SETUP globe, SAVE A GAME, file name field
        for k in "tst":
            h.key(k, 0.4); time.sleep(0.5)
        clk(h, 320, 424, wait=8)                                         # SAVE
        n0 = len(h._logtext())
        clk(h, 706, 410); clk(h, 350, 328); clk(h, 290, 134)             # globe, LOAD A GAME, the file TST
        clk(h, 320, 424, wait=1)                                         # LOAD
        for _ in range(10):
            time.sleep(2)
            t = h._logtext()[n0:]
            if "Bus Error reading" in t or "Address Error" in t:
                break
        t = h._logtext()[n0:]
        out["errors"] = [l[:120] for l in t.splitlines() if re.search(r"(Bus|Address) Error", l) and "ffff8" not in l][:3]
        out["packets"] = [m.group(1) for m in re.finditer(r"> m \$20061 6\n\S+: (.{17})", t)]
        if nextmap and not out["errors"]:
            clk(h, 706, 410); clk(h, 440, 348)                           # globe, MOVE TO NEXT MAP
            time.sleep(10)
            t = h._logtext()[n0:]
            out["errors_after_nextmap"] = [l[:120] for l in t.splitlines() if re.search(r"(Bus|Address) Error", l) and "ffff8" not in l][:3]
            out["turn_after_nextmap"] = h.peekw(Populous.TURN)
    finally:
        h.close()
    return out


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    print(run(a[0], a[1], *(a[2:4] if len(a) > 3 else ("ste", "1.62")), cpu=int(a[4]) if len(a) > 4 else None,
              nextmap="--nextmap" in sys.argv))
