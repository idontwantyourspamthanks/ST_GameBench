"""E7: end-to-end campaign race on the FLOPPY build: campaign loaded from a floppy at the title (F10), redirect sites A-E applied through the debugger at the first title loop, game's own flow
(SPACE -> map -> 'Insert Disk 2' -> swap -> race).  Entry 0 decides what is raced.  usage: e7_race.py NAME --camp disk/edit3_720.st --ring edit1 [--machine ste --mem 2048] [--basecheck LEN]"""
import argparse, re, sys, time, shutil
from pathlib import Path
from cf import *
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--camp", required=True); ap.add_argument("--ring", required=True)
ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--base", type=int, default=0); ap.add_argument("--len", type=int, default=19472)
a = ap.parse_args()
OUT = HERE / "logs"; log = open(OUT / f"e7_{a.name}.txt", "w")
def L(*x):
    s = " ".join(str(v) for v in x); print(s, flush=True); log.write(s + "\n"); log.flush()
SYM = build_blob(); build_hooks(SYM["vars"])
exp = [int(x) for x in (HERE / "disk" / f"ring_{a.ring}.txt").read_text().split()]
h = mk(BUILD / "disk_a.st", machine=a.machine, mem=a.mem, fast=True)
W = lambda b, o=0: int.from_bytes(b[o:o + 2], "big")
try:
    L("cell", a.name, a.machine, a.mem, a.camp)
    cm = h.scratch / "t.txt"; hk = SYM["hook_title"]
    cm.write_text(f"loadbin {HERE}/campread.bin $100000\nloadbin {HERE}/camphooks.bin $100800\n"
                  f"w $7252 $4e $b9 $00 $10 ${hk>>8&0xff:02x} ${hk&0xff:02x}\nw $72c6 $00 $10 $08 $00\n"
                  "w $77da $4e $f9 $00 $10 $09 $00 $4e $71 $4e $71 $4e $71\nw $fda2 $20 $79 $00 $10 $0f $10\nw $731e $4e $f9 $00 $10 $0a $00\nw $60ff $00\n")
    n0 = len(h._logtext()); h.cmd(f"hatari-debug b pc = $7242 :trace :once :file {cm}")
    assert wait_log(h, r"Changed back to", n0, 300), "no title"
    L("title reached; sites + blob + hooks applied, VBL", h.vbl()); time.sleep(2)
    L("sites:", {f"${x:x}": rd(h, x, 6).hex() for x in (0x72c4, 0x77da, 0xfda2, 0x731e, 0x7252)})
    h.keypress(68); time.sleep(4)
    cp = h.scratch / "camp.st"; shutil.copy(a.camp, cp); h.cmd(f"hatari-option --disk-a {cp}"); time.sleep(2)
    h.cmd("hatari-option --fastfdc no"); time.sleep(1)
    h.keypress(30); t0 = time.time()
    V = SYM["vars"]
    while time.time() - t0 < 60:
        time.sleep(1)
        if rd(h, V + 0x28, 1)[0] == 1: break
    L("campaign loaded: v_act", rd(h, V + 0x28, 1).hex(), "v_count", rd(h, V + 0x26, 2).hex(), "store head", rd(h, 0x110000, 8).hex(), f"({int(time.time()-t0)} s wall)")
    time.sleep(1.5); h.keypress(57); time.sleep(3)         # 'Campaign loaded' -> title
    t0 = time.time(); found = False
    while time.time() - t0 < 120:
        h.keypress(57); time.sleep(4)
        if at_prompt(h): found = True; break
    L("game's 'Insert Disk 2' prompt:", found, "VBL", h.vbl())
    dd = h.scratch / "disk2.st"; shutil.copy(BUILD / "disk_b.st", dd)
    h.cmd(f"hatari-option --disk-a {dd}"); time.sleep(2); h.keypress(57)
    t1 = time.time(); ok = False
    while time.time() - t1 < 150:
        time.sleep(3)
        if rd(h, 0x1021, 1)[0] == 2 and int(rd(h, 0x23c0, 4).hex(), 16) != 0 and h.peekw(0x100e) > 20 and h.peekw(0x5ff8) == 0: ok = True; break
    g = lambda ad, n: rd(h, ad, n)
    L("RACE (standing start):", ok, "$102c", g(0x102c, 2).hex(), "V_POS", g(0x100f02, 2).hex(), "$57890.len", W(g(0x57890, 2)), f"(expected base len {a.len})", "$100e", h.peekw(0x100e), "$5ff8", h.peekw(0x5ff8))
    L("stream pointers $23c0 $1bb0 $1bb4 $27da $133a $1342:", [g(x, 4).hex() for x in (0x23c0, 0x1bb0, 0x1bb4, 0x27da, 0x133a, 0x1342)], "PTR", g(0x100f10, 4).hex(), "$58c00", g(0x58c00, 8).hex())
    ring = g(0x1bbc, 2048); got = [W(ring, 2 * i) for i in range(1024)]
    L(f"curve ring $1bbc first 1024 words == decoded curve of '{a.ring}': {got == exp}  (first diff index: {next((i for i in range(1024) if got[i] != exp[i]), None)})")
    L("screenshot", h.shot(str(OUT / f"e7_{a.name}_race.png")))
    h.debug("w $6105 $01"); time.sleep(12); L("driving 12 s: $5ff8", h.peekw(0x5ff8), "$130c", h.peekw(0x130c), "$100e", h.peekw(0x100e)); h.debug("w $6105 $00")
    L("screenshot driving", h.shot(str(OUT / f"e7_{a.name}_drive.png")))
    h.debug("w $1024 $ff", 0.5)
    t2 = time.time(); r = None
    while time.time() - t2 < 60:
        time.sleep(2)
        v = W(g(0x102c, 2))
        if v != int(a.base): r = v; break
    L("after the race ended ($1024 = $ff): $102c =", f"{W(g(0x102c, 2)):#06x}", "V_POS", W(g(0x100f02, 2)), "(position 0 + 1 = 1 expected)")
    L("RESULT done")
finally:
    close(h)
