"""HwScan scratch: does Powermonger's YM sample IRQ ($1af3e) run on a machine?  Read-only use of the Powermonger tools."""
import argparse, os, re, struct, sys, time
from pathlib import Path
PM = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger")
sys.path[:0] = [str(PM / "tools"), "/home/ryan/Code/AtariST/gamebench/tools"]
import pmpatch, pmsnd
from pm import TOS
ap = argparse.ArgumentParser()
ap.add_argument("--disk", required=True); ap.add_argument("--machine", default="falcon"); ap.add_argument("--tos", default="4.04")
ap.add_argument("--mem", type=int, default=4096); ap.add_argument("--hopts", default="")
ap.add_argument("--effects", type=int, nargs="*", default=[3, 7, 12])
a = ap.parse_args()
pmsnd.setup_home(); os.environ["HOME"] = str(pmsnd.HOME); os.environ["SDL_AUDIODRIVER"] = "dummy"
import shlex
h = pmpatch.make_pm(Path(a.disk), None, machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=shlex.split(a.hopts))
try:
    h.boot_to_game()
    print(f"MACHINE {a.machine} TOS {a.tos} {a.mem} KB; MARKER={h.peekl(pmpatch.MARKER).to_bytes(4,'big')!r} FLAGS={h.peekl(pmpatch.FLAGS):#x} (bit0 = DMA-sound hardware answered)")
    print(f"timer A vector $134 = {h.peekl(0x134):#x} (original player = 0x1af32), VBL vector $70 = {h.peekl(0x70):#x}")
    print(f"timer A control $fffa19 = {h.peekw(0xFA18) & 0xFF:#x}, IERA $fffa07 = {h.peekw(0xFA06) & 0xFF:#x} (bit5 = timer A enabled), IMRA $fffa13 = {h.peekw(0xFA12) & 0xFF:#x}")
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    h.cmd("hatari-debug b pc = $1af3e :trace"); time.sleep(0.5)
    h.cmd("hatari-debug b pc = $1af58 :trace"); time.sleep(0.5)
    for eff in a.effects:
        ptr = h.peekl(0x2C9A0 + 4 * (eff - 1))
        for c in pmsnd.trigger_cmds(ptr):
            h.debug(c, 0.25)
        t = time.time(); seen = []
        while time.time() - t < 8:
            seen.append((h.peekw(0xFF8900) >> 8 & 1, h.peekw(0x2C992) >> 8, h.peekw(0x2C993) >> 8)); time.sleep(0.5)
        print(f"effect {eff}: seq ptr {ptr:#x}; samples of (DMA ctrl bit0, seq active, timer-IRQ busy $2c993) = {seen}")
    time.sleep(5)
    log = h._logtext()[n0:]
    hits = [l for l in log.splitlines() if re.search(r"1af3e|1af58|pc = \$1af", l, re.I)]
    print("timer A control after effects:", hex(h.peekw(0xFA18) & 0xFF))
    print("breakpoint lines mentioning $1af3e/$1af58:", len(hits)); print("\n".join(hits[:6]))
    bus = [l for l in h._logtext().splitlines() if re.search(r"bus error|address error|Bus Error", l)]
    print("bus-error lines in the whole Hatari log:", len(bus)); print("\n".join(bus[:6]))
    print("main loop still iterating:", h.in_game())
finally:
    h.close()
