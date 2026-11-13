#!/usr/bin/env python3
"""PopRelease: repeated in-game LOADs (and LOAD + MOVE TO NEXT MAP) on an HD build; counts bus / address errors and pop_ptrfix packet drops
(test scaffolding).
    python3 loadn.py TAG BUILD MACHINE TOS MEM CPU NLOADS
Per LOAD it prints the turn word before the click and 6 s after (LOAD brings the saved turn back, then it runs on)."""
import re, sys, time
from pathlib import Path

GAME = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(GAME / "tools")]
from populous import Populous, HOME, CONQUEST_XY, START_XY  # noqa: E402
from stharness import TOS  # noqa: E402


def clk(h, x, y, hold=0.4, wait=2.0):
    h.goto(x, y, home_xy=HOME)
    h.click(hold=hold)
    time.sleep(wait)


def turn(h):
    for _ in range(6):
        try:
            return h.peekw(Populous.TURN)
        except Exception:
            time.sleep(0.5)
    return None


def playing(h):
    t = turn(h); time.sleep(1.5)
    return turn(h) != t


def main():
    tag, build, machine, tos, mem, cpu, nloads = sys.argv[1:8]
    mem, cpu, nloads = int(mem), int(cpu), int(nloads)
    h = Populous(game_dir=GAME / build, snapshot=None, memsize_kb=mem, machine=machine, tos=TOS[tos])
    out = {"tag": tag}
    try:
        time.sleep(16)
        if cpu:
            h.set_cpuclock(cpu)
            if machine == "megaste" and cpu >= 16:
                h.debug("w $ff8e21 $03", 0.5)
        h.key("space", 0.5)
        time.sleep(26 if machine in ("ste", "st") else 23)
        h.goto(*CONQUEST_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(9)
        for _ in range(3):
            h.goto(*START_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(12)
            if playing(h):
                break
        out["playing"] = playing(h)
        out["marker"] = hex(h.peekl(0xB3004))
        pk = Path("/tmp/loadn_%s.txt" % tag); pk.write_text("m $20061 6\nm $2478a 6\n")
        h.debug("b all", 0.3)
        for c in ("($20064).w > 199", "($20062).w > 319", "($20061).b > 15"):
            h.debug(f"b pc = $b783c && {c} :trace :file {pk}", 0.5)
        clk(h, 706, 410); clk(h, 350, 308); clk(h, 400, 385)            # GAME SETUP globe, SAVE A GAME, file name field
        for k in "tst":
            h.key(k, 0.4); time.sleep(0.5)
        clk(h, 320, 424, wait=8)                                         # SAVE
        out["turn_saved"] = turn(h)
        n0 = len(h._logtext())
        loads = []
        for i in range(nloads):
            time.sleep(4)
            tb = turn(h)
            clk(h, 706, 410); clk(h, 350, 328); clk(h, 290, 134)         # globe, LOAD A GAME, the file TST
            clk(h, 320, 424, wait=6)                                     # LOAD
            loads.append((tb, turn(h)))
        out["loads (turn before, 6 s after)"] = loads
        clk(h, 706, 410); clk(h, 350, 328); clk(h, 290, 134)
        clk(h, 320, 424, wait=6)
        out["turn_before_nextmap"] = turn(h)
        clk(h, 706, 410); clk(h, 440, 348)                               # globe, MOVE TO NEXT MAP
        time.sleep(10)
        out["turn_after_nextmap"] = turn(h)
        out["playing_end"] = playing(h)
        t = h._logtext()[n0:]
        out["errors"] = [l[:130] for l in t.splitlines() if re.search(r"(Bus|Address) Error|double bus|halted", l) and "ffff8" not in l][:4]
        out["errors_total_incl_boot_probes"] = len(re.findall(r"(Bus|Address) Error", h._logtext()))
        out["dropped_packets"] = [m.group(1) for m in re.finditer(r"> m \$20061 6\n\S+: (.{17})", t)]
        h.shot(str(GAME / "work" / "shots" / f"release_loadn_{tag}.png"))
    finally:
        h.close()
    print(out)


main()
