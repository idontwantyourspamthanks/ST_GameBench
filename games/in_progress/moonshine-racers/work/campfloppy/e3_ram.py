"""E3: free RAM in a real FLOPPY race: boot disk A, SPACE to the disk-2 prompt, swap disk 2 into A, race; dump all RAM at the standing start and after driving, zero-map it.
usage: e3_ram.py NAME [--machine ste --mem 2048 --tos T]"""
import argparse, re, sys, time, shutil
from pathlib import Path
from cf import *
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--tos")
a = ap.parse_args()
OUT = HERE / "logs"; log = open(OUT / f"e3_{a.name}.txt", "w")
def L(*x):
    s = " ".join(str(v) for v in x); print(s, flush=True); log.write(s + "\n"); log.flush()
h = mk(BUILD / "disk_a.st", machine=a.machine, mem=a.mem, tos=a.tos, fast=True)
try:
    t0 = time.time(); found = False
    while time.time() - t0 < 400:
        h.keypress(57); time.sleep(4)
        if h.vbl() > 1500 and at_prompt(h): found = True; break
    L("disk-2 prompt", found, "VBL", h.vbl())
    dd = h.scratch / "disk2.st"; shutil.copy(BUILD / "disk_b.st", dd)
    h.cmd(f"hatari-option --disk-a {dd}"); time.sleep(2); h.keypress(57)
    t1 = time.time(); ok = False
    while time.time() - t1 < 120:
        time.sleep(4)
        if rd(h, 0x1021, 1)[0] == 2 and int(rd(h, 0x23c0, 4).hex(), 16) != 0 and h.peekw(0x100e) > 30: ok = True; break
    L("race reached:", ok, "$1021", rd(h, 0x1021, 1).hex(), "$23c0", rd(h, 0x23c0, 4).hex(), "$100e", h.peekw(0x100e), "$b2700", rd(h, 0xb2700, 4))
    size = a.mem * 1024
    f1 = HERE / "snap" / f"{a.name}_start.bin"; f1.parent.mkdir(exist_ok=True)
    h.debug(f"savebin {f1} 0 ${size:x}", 4 + size / 400000)
    L("dump 1", f1, f1.stat().st_size if f1.exists() else None)
    h.debug("w $6105 $01"); time.sleep(25)
    L("driving: $5ff8", h.peekw(0x5ff8), "$130c", h.peekw(0x130c))
    f2 = HERE / "snap" / f"{a.name}_drive.bin"
    h.debug(f"savebin {f2} 0 ${size:x}", 4 + size / 400000)
    L("dump 2", f2, f2.stat().st_size if f2.exists() else None)
    L("RESULT done")
finally:
    close(h)
