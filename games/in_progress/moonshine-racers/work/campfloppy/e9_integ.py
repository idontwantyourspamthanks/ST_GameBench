"""E9: INTEGRATED floppy build (priv build: core_floppy two-list gate + ported cp_* patches + floppy reader).  Real F10 menu on the title, campaign loaded from a floppy in drive A,
'Play from track N', game's own flow (map -> 'Insert Disk 2' -> swap), race with the campaign entry.  usage: e9_integ.py NAME --camp disk/camp5_720.st --track 0 --ring lev5 --base 5 --len 18000"""
import argparse, re, sys, time, shutil
from pathlib import Path
from cf import *
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--camp", required=True); ap.add_argument("--track", type=int, default=0); ap.add_argument("--ring", required=True)
ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--base", type=int, required=True); ap.add_argument("--len", type=int, required=True)
ap.add_argument("--build", default=str(HERE / "buildcamp"))
a = ap.parse_args()
OUT = HERE / "logs"; log = open(OUT / f"e9_{a.name}.txt", "w")
def L(*x):
    s = " ".join(str(v) for v in x); print(s, flush=True); log.write(s + "\n"); log.flush()
exp = [int(x) for x in (HERE / "disk" / f"ring_{a.ring}.txt").read_text().split()]
h = mk(Path(a.build) / "disk_a.st", machine=a.machine, mem=a.mem, fast=True)
W = lambda b, o=0: int.from_bytes(b[o:o + 2], "big")
def key(sc, wait=1.5): h.keypress(sc); time.sleep(wait)
try:
    L("cell", a.name, a.machine, a.mem, a.camp, "track", a.track)
    cm = h.scratch / "t.txt"; cm.write_text("w $60ff $00\nm $b2700 8\nm $b2704 4\n")
    n0 = len(h._logtext()); h.cmd(f"hatari-debug b pc = $7242 :trace :once :file {cm}")
    assert wait_log(h, r"Changed back to", n0, 300), "no title"
    time.sleep(2); L("title; marker/flag:", [l.strip()[:40] for l in h._logtext()[n0:].splitlines() if l.startswith(("000B2700", "000B2704"))], "VBL", h.vbl())
    key(68, 4)
    L("F10 -> menu", h.shot(str(OUT / f"e9_{a.name}_1menu.png")))
    cp = h.scratch / "camp.st"; shutil.copy(a.camp, cp); h.cmd(f"hatari-option --disk-a {cp}"); time.sleep(2)
    h.cmd("hatari-option --fastfdc no"); time.sleep(1)
    key(80, 1)                                  # Down: LOAD CAMPAIGN FROM DRIVE A
    L("selected item 1", h.shot(str(OUT / f"e9_{a.name}_2sel.png")))
    t0 = time.time(); key(28, 1)                # Return
    L("loading", h.shot(str(OUT / f"e9_{a.name}_3loading.png")))
    while time.time() - t0 < 60:
        time.sleep(1)
        if rd(h, 0xb8e01, 1)[0] == 1: break
    L(f"loaded (wall {int(time.time()-t0)} s): V_ACT {rd(h,0xb8e00,1).hex()} V_LOADED {rd(h,0xb8e01,1).hex()} V_COUNT {rd(h,0xb8e02,2).hex()} store head {rd(h,0x110000,8).hex()}")
    time.sleep(2); L("track list", h.shot(str(OUT / f"e9_{a.name}_4list.png")))
    for _ in range(a.track): key(80, 0.8)
    L("play from track", a.track + 1, h.shot(str(OUT / f"e9_{a.name}_5pick.png")))
    key(28, 3)
    L("after Return: V_ACT", rd(h, 0xb8e00, 1).hex(), "V_START", rd(h, 0xb8e06, 2).hex(), "$102c", rd(h, 0x102c, 2).hex())
    t0 = time.time(); found = False
    while time.time() - t0 < 150:
        h.keypress(57); time.sleep(4)
        if at_prompt(h): found = True; break
    L("game's 'Insert Disk 2' prompt:", found, "VBL", h.vbl(), "$102c", rd(h, 0x102c, 2).hex())
    dd = h.scratch / "disk2.st"; shutil.copy(Path(a.build) / "disk_b.st", dd)
    h.cmd(f"hatari-option --disk-a {dd}"); time.sleep(2); h.keypress(57)
    t1 = time.time(); ok = False
    while time.time() - t1 < 150:
        time.sleep(3)
        if rd(h, 0x1021, 1)[0] == 2 and int(rd(h, 0x23c0, 4).hex(), 16) != 0 and h.peekw(0x100e) > 20 and h.peekw(0x5ff8) == 0: ok = True; break
    g = rd
    L("RACE (standing start):", ok, "$102c", g(h, 0x102c, 2).hex(), "POS", g(h, 0xb8e04, 2).hex(), "$57890.len", W(g(h, 0x57890, 2)), f"(expected {a.len})", "$100e", h.peekw(0x100e), "$5ff8", h.peekw(0x5ff8))
    L("stream ptrs $23c0 $1bb0 $1bb4 $27da $133a $1342:", [g(h, x, 4).hex() for x in (0x23c0, 0x1bb0, 0x1bb4, 0x27da, 0x133a, 0x1342)], "PTR", g(h, 0xb8e08, 4).hex(), "$58c00", g(h, 0x58c00, 8).hex())
    ring = g(h, 0x1bbc, 2048); got = [W(ring, 2 * i) for i in range(1024)]
    L(f"curve ring $1bbc first 1024 words == decoded curve of '{a.ring}': {got == exp} (first diff {next((i for i in range(1024) if got[i] != exp[i]), None)})")
    L("race screenshot", h.shot(str(OUT / f"e9_{a.name}_6race.png")))
    h.debug("w $6105 $01"); time.sleep(12); L("driving 12 s: $5ff8", h.peekw(0x5ff8), "$130c", h.peekw(0x130c), "$100e", h.peekw(0x100e)); h.debug("w $6105 $00")
    h.debug("w $1024 $ff", 0.5); time.sleep(25)
    L("after race end ($1024=$ff): $102c", g(h, 0x102c, 2).hex(), "POS", g(h, 0xb8e04, 2).hex(), "$1021", g(h, 0x1021, 1).hex(), "marker", g(h, 0xb2700, 4))
    L("screenshot after", h.shot(str(OUT / f"e9_{a.name}_7after.png")))
    L("RESULT done")
finally:
    close(h)
