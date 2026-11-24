"""E5: error paths + retry loop + interrupts during the read, all in ONE boot: title -> F10 -> a list of scenarios against the prompt loop.
scenario = (label, what goes into the drive, key).   usage: e5.py NAME [--machine ste --mem 2048] [--nob]"""
import argparse, re, sys, time, shutil
from pathlib import Path
from cf import *
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--nob", action="store_true"); ap.add_argument("--only", default="")
a = ap.parse_args()
OUT = HERE / "logs"; log = open(OUT / f"e5_{a.name}.txt", "w")
def L(*x):
    s = " ".join(str(v) for v in x); print(s, flush=True); log.write(s + "\n"); log.flush()
SYM = build_blob(); V = SYM["vars"]
D = HERE / "disk"
SC = [  # label, drive-letter, image (None = eject), key
 ("game disk 2 in A (wrong disk)",       "A", BUILD / "disk_b.st", "A"),
 ("blank DOS disk in A (no file)",       "A", HERE.parent / "fdb" / "blank_fmt.st", "A"),
 ("random bytes in A",                   "A", HERE.parent / "fdb" / "junk.st", "A"),
 ("truncated campaign disk (200 KB)",    "A", D / "trunc200k.st", "A"),
 ("no disk in drive B (empty drive)",    "B", None, "B"),
 ("no disk in drive A (ejected)",        "A", None, "A"),
 ("campaign disk in A, mid-read key",    "A", D / "stock720.st", "A"),
]
if a.only: SC = [s for s in SC if a.only in s[0]]
h = mk(BUILD / "disk_a.st", machine=a.machine, mem=a.mem, fast=True, nob=a.nob)
try:
    L("cell", a.name, a.machine, a.mem, "nob" if a.nob else "")
    cm = h.scratch / "t.txt"; hook = SYM["hook_title"]
    cm.write_text(f"loadbin {HERE}/campread.bin $100000\nw $7252 $4e $b9 $00 ${hook>>16 & 0xff:02x} ${hook>>8 & 0xff:02x} ${hook & 0xff:02x}\nw $60ff $00\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7242 :trace :once :file {cm}")
    assert wait_log(h, r"Changed back to", n0, 300), "no title"
    L("title + hook applied, VBL", h.vbl()); time.sleep(2)
    h.cmd("hatari-option --fastfdc no"); time.sleep(1)
    h.keypress(68); time.sleep(4)
    L("F10 -> prompt; screenshot", h.shot(str(OUT / f"e5_{a.name}_ask.png")))
    vbl_h = int(rd(h, 0x70, 4).hex(), 16)
    ent = h.scratch / "e.txt"; ent.write_text("e VBL\nm $b8f00 4\nm $611a 1\n"); ex = h.scratch / "x.txt"; ex.write_text("e VBL\nr\nm $b8f00 4\nm $611a 1\n")
    h.cmd(f"hatari-debug b pc = ${SYM['camp_read']:x} :trace :file {ent}"); time.sleep(0.4)
    h.cmd(f"hatari-debug b pc = ${SYM['cr_exit']:x} :trace :file {ex}"); time.sleep(0.4)
    for k, (label, drv, img, key) in enumerate(SC):
        n1 = len(h._logtext())
        if img is None:
            h.cmd(f"hatari-option --disk-{drv.lower()} none")   # eject attempt 1
            time.sleep(1)
            L("  eject log:", [l for l in h._logtext()[n1:].splitlines() if "loppy" in l or "isk" in l][-3:])
        else:
            cp = h.scratch / f"s{k}.st"; shutil.copy(img, cp)
            h.cmd(f"hatari-option --disk-{drv.lower()} {cp}"); time.sleep(2)
        n2 = len(h._logtext())
        h.keypress(30 if key == "A" else 48)
        t0 = time.time(); mid = None
        while time.time() - t0 < 150:
            txt = h._logtext()[n2:]
            if "mid-read" in label and mid is None and txt.count("Changed back to") >= 1 and time.time() - t0 > 2.0:
                h.keypress(57); mid = time.time(); time.sleep(0.8); L("  mid-read: keypress sent; $60ff =", rd(h, 0x60ff, 1).hex())
            if txt.count("Changed back to") >= 2: break
            time.sleep(0.3)
        txt = h._logtext()[n2:]
        vb = [int(m) for m in re.findall(r"#(\d+) \(dec\)", txt)]
        m7 = re.findall(r"D7 ([0-9A-F]{8})", txt)
        dt = (vb[1] - vb[0]) / 50 if len(vb) >= 2 else None
        L(f"[{k}] {label}: drive {drv} key {key}: status d7 = {m7[-1] if m7 else '?'}  camp_read time {dt:.2f} s  (VBL {vb})" if dt is not None else f"[{k}] {label}: NO EXIT within 150 s; VBL {vb}")
        if "mid-read" in label:
            ck = re.findall(r"^000B8F00: ([0-9a-f ]{11})", txt, re.M); vb61 = re.findall(r"^0000611A: ([0-9a-f]{2})", txt, re.M)
            L("  game tick clock $b8f00 (advanced by the game's VBL handler via mt_clock) at entry/exit:", ck, " and $611a:", vb61, f"; VBL delta {vb[1]-vb[0]}")
        time.sleep(1.5)
        L("  screenshot", h.shot(str(OUT / f"e5_{a.name}_{k}.png")))
        h.keypress(57); time.sleep(3)           # the 'press a key' of the error text -> ask prompt again
        if k < len(SC) - 1 and "mid-read" not in label:
            pass
    L("final VBL", h.vbl(), "v_status", rd(h, V + 0x24, 2).hex(), "v_count", rd(h, V + 0x26, 2).hex(), "v_act", rd(h, V + 0x28, 1).hex())
    L("RESULT done")
finally:
    close(h)
