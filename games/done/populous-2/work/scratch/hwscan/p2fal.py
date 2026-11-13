"""HwScan scratch: Populous 2 sample IRQ ($2aa4e, YM writes at $2aa74) on a machine: cold boot an HD build to play, inject a sample, report."""
import argparse, re, sys, time
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0] = [str(G / "tools"), "/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
ap = argparse.ArgumentParser()
ap.add_argument("--build", required=True); ap.add_argument("--machine", default="falcon"); ap.add_argument("--tos", default="4.04")
ap.add_argument("--mem", type=int, default=4096); ap.add_argument("--keys", action="store_true"); ap.add_argument("--extra", default=""); ap.add_argument("--force8007", default="")
a = ap.parse_args()
h = Populous2(game_dir=G / a.build, machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=a.extra.split())
try:
    ok = h.boot_to_game()
    print(f"MACHINE {a.machine} TOS {a.tos} {a.mem} KB build {a.build}: in_play={ok} marker={h.marker()!r}")
    print(f"turn {h.peekw(h.TURN)}; $134 = {h.peekl(0x134):#x}; $2aa74 = {h.peekl(0x2aa74):#010x} {h.peekl(0x2aa78):#010x} (original 03c88df1 01888df1); $2aa4e handler first word {h.peekw(0x2aa4e):#06x}")
    print(f"$ff8006/7 = {h.peekw(0xff8006):#06x}")
    if a.force8007:        # a CPU write (the debugger's poke does not reach Hatari's bus-mode state): the handler's first 6 bytes -> jmp $f0000;
        # $f0000: the 3 displaced pushes, move.b #v,$ffff8007, jmp $2aa54
        h.debug("w $f0000 $3f $00 $2f $01 $2f $08 $13 $fc $00 $" + a.force8007 + " $ff $ff $80 $07 $4e $f9 $00 $02 $aa $54", 0.5)
        h.debug("w $2aa4e $4e $f9 $00 $0f $00 $00", 0.5)
        print(f"handler entry now {h.peekl(0x2aa4e):#x} {h.peekw(0x2aa52):#x}: every interrupt does a CPU write $ff8007 := ${a.force8007} first")
    log0 = len(h._logtext())
    # inject a sequence of 8 x (sample 1, timer data $46) ended by $ff at $88400, then start it exactly as $2b4a0 does
    h.debug("w $f0100 " + " ".join(["$01 $46"] * 8) + " $ff $00", 0.5)
    h.debug("b all", 0.3)
    print(f"IERA {h.peekw(0xfffa06) & 0xff:#x} IMRA {h.peekw(0xfffa12) & 0xff:#x} TACR {h.peekw(0xfffa18) & 0xff:#x}  ($fffa07/13/19)")
    mark = len(h._logtext())
    h.cmd("hatari-debug b pc = $2a978 :trace :once"); time.sleep(0.4)
    h.cmd("hatari-debug b pc = $2aa74 :trace :once"); time.sleep(0.4)
    h.cmd("hatari-debug b pc = $2aa4e :trace :once"); time.sleep(0.4)
    for c in ("w $2b60c $00", "w $2b60e $00 $00", "w $2b60d $00", "w $2b81a $00 $0f $01 $00", "w $2b60b $01"):
        h.debug(c, 0.3)
    time.sleep(1.0)
    for _ in range(5):
        try:
            print(f"sequence at $f0100: {h.peekl(0xf0100):#010x}; seq ptr $2b81a = {h.peekl(0x2b81a):#x}"); break
        except IndexError:
            time.sleep(1.0)
    t = time.time(); seen = []; dead = False
    try:
        while time.time() - t < 6:
            seen.append((h.peekw(0x2b60a) & 0xff, h.peekw(0x2b60c) >> 8, h.peekw(0x2b60e))); time.sleep(0.6)
    except IndexError:
        dead = True
    print("(active $2b60b, busy $2b60c, step $2b60e) samples:", seen, "| debugger stopped answering (machine halted):", dead)
    time.sleep(1)
    log = h._logtext()[log0:]
    print("breakpoint lines (matched):", "\n".join(l for l in log.splitlines() if "matched" in l))
    bus = [l for l in log.splitlines() if re.search(r"bus error|address error|exception [23] |halt|double", l, re.I)]
    print("bus-error / halt lines since the injection:", len(bus)); print("\n".join(bus[:6]))
    if not dead:
        print(f"after: $2aa74 = {h.peekl(0x2aa74):#010x} {h.peekl(0x2aa78):#010x}; turn {h.peekw(h.TURN)}; in_play {h.in_play()}")
    if not dead:
        out = f"/tmp/hw/p2_code_{a.machine}_{Path(a.build).name}.bin"
        h.dump(out, 0x2a900, 0x1a0); print("dumped $2a900-$2aa9f to", out)
finally:
    h.close()
