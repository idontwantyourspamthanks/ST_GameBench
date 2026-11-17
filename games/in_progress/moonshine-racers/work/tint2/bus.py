"""Bus/address-error forensics of the floppy build: python3 bus.py DISK_A DISK_B MACHINE MEM TOS NAME
Boots disk A alone, walks the story screens, records the disk-2 prompt, swaps to disk B in drive A, enters the race, drives 20 s steered.
Keeps the FULL Hatari log (res/bus_<name>.log) and prints every 'Bus Error' / 'Address Error' line with 3 lines of context and the phase it belongs to
(phase marks = log length at: after boot sector / at the disk-2 prompt / after the swap / in the race / after the drive)."""
import sys, time, re, shutil, tempfile
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers")
sys.path.insert(0, str(G / "tools"))
import msrfloppy as F
disk_a, disk_b, machine, mem, tos, name = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6]
h = F.mk(disk_a, None, machine, mem, tos)
marks = []
mark = lambda lbl: marks.append((len(h._logtext()), lbl))
try:
    t0 = time.time(); found = False; n = 0
    while time.time() - t0 < 400:
        time.sleep(3); v = h.vbl()
        if v > 900 and n == 2: mark("story screens")
        if v > 1500 and h.screen_matches(F.DISK2_REF, F.DISK2_BOX):
            found = True; break
        if v > 500: h.keypress(57); n += 1
    mark("at the disk-2 prompt")
    if not found: raise SystemExit("no disk-2 prompt")
    d2 = Path(tempfile.mkdtemp(prefix="msr_bus_")) / "disk2.st"
    shutil.copy(disk_b, d2)
    h.cmd(f"hatari-option --disk-a {d2}"); time.sleep(2); h.keypress(57); time.sleep(25)
    mark("race loop")
    print("after swap: vbl", h.vbl(), "$1021/$100e", (F.peekb(h, 0x1021), h.peekw(0x100e)), "marker", h.debug("m $b2700 4", 0.6).strip().splitlines()[-1])
    ZIG = [0x01, 0x05, 0x01, 0x09]
    for k in range(20):
        h.debug(f"w $6105 ${ZIG[(k // 4) % 4]:02x}", 0.1); time.sleep(1)
    mark("end of 20 s drive")
    print("end: vbl", h.vbl(), "$1021", F.peekb(h, 0x1021), "$100e", h.peekw(0x100e), "extras", h.debug("m $b8f38 12", 0.7).strip().splitlines()[-1])
    lg = h._logtext()
finally:
    h.close()
out = G / "work/tint2/res" / f"bus_{name}.log"
out.write_text(lg)
lines = lg.splitlines()
lo = lambda off: sum(1 for m, _ in marks if m <= off)
hits = [(i, l) for i, l in enumerate(lines) if re.search(r"Bus Error|Address Error", l)]
print(f"{name}: log {len(lg)} B, {len(hits)} bus/address error lines -> {out}")
for i, l in hits:
    off = sum(len(x) + 1 for x in lines[:i])
    ph = next((lbl for m, lbl in reversed(marks) if m <= off), "boot sector / loader")
    print(f"  [phase: {ph}] {l}")
    for j in range(max(0, i - 3), min(len(lines), i + 4)):
        print("      ctx:", lines[j][:200])
