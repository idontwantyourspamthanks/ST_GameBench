"""Bus/address error forensics for the HD build: python3 hdbus.py GAMEDIR TAG [stock] [ste|megaste] [mem] [tos]
Cold boot to the race (msr.boot_to_race), hold 'up' 20 s, then print every Bus/Address Error line with context; the full log is copied to
res/hdbus_<TAG>.log BEFORE the emulator is closed (stharness deletes its temp dir on close)."""
import sys, time, re
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build")
from mxlib import *
from msr import Moonshine, GAME
from stharness import TOS
gd, tag = sys.argv[1], sys.argv[2]
machine = sys.argv[3] if len(sys.argv) > 3 else "ste"
mem = int(sys.argv[4]) if len(sys.argv) > 4 else 1024
tos = sys.argv[5] if len(sys.argv) > 5 else "1.62"
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / gd, tos=TOS[tos], extra=["--cpuclock", "8"])
marks = []
mark = lambda lbl: marks.append((len(h._logtext()), lbl))
try:
    ok = h.boot_to_race(log=lambda *a: None)
    mark("boot/loader")
    print(f"{tag}: boot_to_race {ok} vbl {h.vbl()} marker {h.debug('m $b2700 4', 0.6).strip().splitlines()[-1]}")
    h.drive(True); time.sleep(20); mark("20 s drive")
    lg = h._logtext()
finally:
    h.close()
out = GAME / "work/tint2/res" / f"hdbus_{tag}.log"
out.write_text(lg)
lines = lg.splitlines()
hits = [(i, l) for i, l in enumerate(lines) if re.search(r"Bus Error|Address Error", l)]
print(f"{tag}: log {len(lg)} B, {len(hits)} bus/address lines -> {out}")
for i, l in hits:
    off = sum(len(x) + 1 for x in lines[:i])
    ph = next((lbl for m, lbl in reversed(marks) if m <= off), "boot sector / loader")
    print(f"  [phase: {ph}] {l}")
    for j in range(max(0, i - 3), min(len(lines), i + 4)):
        print("      ctx:", lines[j][:200])
