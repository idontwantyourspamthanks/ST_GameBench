"""E2: the campaign-disk read cell.  Floppy build (disk_a.st) booted to the title; blob + F10 hook applied through the debugger at the first title loop ($7242);
F10 -> prompt -> campaign disk swapped into the chosen drive -> key A/B -> read -> report -> title -> SPACE -> game's own 'Insert Disk 2' prompt -> swap disk 2 -> race.
usage: e2.py NAME --camp disk/stock720.st [--trk disk/stock.trk] [--key A|B] [--machine ste --mem 2048] [--nob] [--where A|B] [--noride] [--eject]"""
import argparse, re, sys, time, shutil, subprocess
from pathlib import Path
from cf import *

ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("--camp"); ap.add_argument("--trk"); ap.add_argument("--key", default="A"); ap.add_argument("--where", default=None)
ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--tos")
ap.add_argument("--nob", action="store_true"); ap.add_argument("--noride", action="store_true", help="skip the disk-2 / race part")
ap.add_argument("--keyduring", action="store_true"); ap.add_argument("--twice", action="store_true")
ap.add_argument("--build", default=str(BUILD)); ap.add_argument("--startb", help="disk image in drive B from power-on (e.g. disk 2 for the two-drive case)")
a = ap.parse_args()
OUT = HERE / "logs"; log = open(OUT / f"e2_{a.name}.txt", "w")
def L(*x):
    s = " ".join(str(v) for v in x); print(s, flush=True); log.write(s + "\n"); log.flush()

SYM = build_blob()
vars_ = SYM["vars"]; v = lambda off: vars_ + off
d2 = Path(a.build) / "disk_b.st"
h = mk(Path(a.build) / "disk_a.st", disk_b=a.startb, machine=a.machine, mem=a.mem, tos=a.tos, fast=True, nob=a.nob)
try:
    L("cell", a.name, a.machine, a.mem, "camp", a.camp, "key", a.key, "nob" if a.nob else "", "startB" if a.startb else "")
    # --- apply blob + F10 hook at the first title loop
    cm = h.scratch / "t.txt"
    hook = SYM["hook_title"]
    cm.write_text(f"loadbin {HERE}/campread.bin $100000\nw $7252 $4e $b9 $00 ${hook>>16 & 0xff:02x} ${hook>>8 & 0xff:02x} ${hook & 0xff:02x}\nw $60ff $00\nm $7252 6\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7242 :trace :once :file {cm}")
    ok = wait_log(h, r"Changed back to", n0, 300)
    L("title reached + hook applied:", ok, "VBL", h.vbl())
    if not ok: raise SystemExit("no title")
    time.sleep(2)
    L("site $7252 + blob head:", rd(h, 0x7252, 6).hex(), rd(h, 0x100000, 4).hex())
    L("screenshot title", h.shot(str(OUT / f"e2_{a.name}_1title.png")))
    for rnd in range(2 if a.twice else 1):
        # --- F10
        h.keypress(68)
        time.sleep(4)
        L("F10 pressed; $60ff", rd(h, 0x60ff, 1).hex(), "VBL", h.vbl())
        L("screenshot prompt", h.shot(str(OUT / f"e2_{a.name}_2prompt_{rnd}.png")))
        # --- swap the campaign disk into the chosen drive, real FDC timing from here on
        drv = a.where or a.key
        if a.camp:
            cp = h.scratch / f"camp{rnd}.st"; shutil.copy(a.camp, cp)
            h.cmd(f"hatari-option --disk-{drv.lower()} {cp}")
            time.sleep(2)
        h.cmd("hatari-option --fastfdc no"); time.sleep(1)
        # breakpoints: read entry (VBL), exit (VBL + registers); count the game's VBL handler runs
        vbl_h = rd(h, 0x70, 4).hex()
        L("VBL vector $70 =", vbl_h)
        e = h.scratch / "e.txt"; e.write_text("e VBL\nr\n"); x = h.scratch / "x.txt"; x.write_text("e VBL\nr\nm $100000 2\n")
        n1 = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${SYM['camp_read']:x} :trace :once :file {e}"); time.sleep(0.4)
        h.cmd(f"hatari-debug b pc = ${SYM['cr_exit']:x} :trace :once :file {x}"); time.sleep(0.4)
        if a.keyduring: pass
        h.keypress(30 if a.key == "A" else 48)
        t0 = time.time(); vb0 = None; midkey = False
        while time.time() - t0 < 120:
            txt = h._logtext()[n1:]
            if txt.count("Changed back to") >= 2: break
            if a.keyduring and not midkey and txt.count("Changed back to") >= 1 and time.time() - t0 > 2.5:
                h.keypress(57); midkey = True; time.sleep(0.8)
                L("keypress SPACE (57) sent mid-read; $60ff =", rd(h, 0x60ff, 1).hex(), "(57 = $39 -> the keyboard IRQ was serviced mid-read)")
            time.sleep(0.3)
        txt = h._logtext()[n1:]
        vb = [int(m) for m in re.findall(r"#(\d+) \(dec\)", txt)]
        L("VBL at entry/exit:", vb, "=> read time %.2f s (50 Hz VBL)" % ((vb[1] - vb[0]) / 50) if len(vb) >= 2 else "no exit")
        dm = re.findall(r"^\s+D7 ([0-9A-F]{8})", txt, re.M)
        m7 = re.findall(r"D0 (\w{8})   D1 (\w{8})   D2 (\w{8})   D3 (\w{8})\s*\n\s+D4 (\w{8})   D5 (\w{8})   D6 (\w{8})   D7 (\w{8})", txt)
        L("status d7 at exit:", m7[-1][7] if m7 else "?", "| (0 ok)")
        L("vars after: v_status", rd(h, v(0x24), 2).hex(), "v_count", rd(h, v(0x26), 2).hex(), "v_act", rd(h, v(0x28), 1).hex(), "v_size", rd(h, v(0x10), 4).hex(), "v_spt", rd(h, v(2), 2).hex(), "v_data0", rd(h, v(0x18), 4).hex())
        time.sleep(1.5)
        L("screenshot after read", h.shot(str(OUT / f"e2_{a.name}_3after_{rnd}.png")))
        if a.trk and Path(a.trk).exists():
            want = Path(a.trk).read_bytes()
            dump = h.scratch / "dump.bin"
            h.debug(f"savebin {dump} $110000 ${len(want):x}", 2.0 + len(want) / 60000)
            got = dump.read_bytes() if dump.exists() else b""
            L(f"read-back compare {len(want)} B at $110000: identical={got == want} (md5 want {__import__('hashlib').md5(want).hexdigest()} got {__import__('hashlib').md5(got).hexdigest()})")
        # --- leave the UI: a key at 'Campaign loaded' / the error text
        st = rd(h, v(0x24), 2).hex()
        h.keypress(57); time.sleep(3)
        if st != "0000":
            L("error path: UI is back at the ask prompt? screenshot", h.shot(str(OUT / f"e2_{a.name}_4ask_{rnd}.png")))
            h.keypress(1); time.sleep(3)           # ESC cancels
            L("after ESC: screenshot", h.shot(str(OUT / f"e2_{a.name}_5esc_{rnd}.png")))
        L("title running again? $7242 area:", rd(h, 0x7252, 6).hex())
    if not a.noride and a.startb:
        t0 = time.time(); race = False; seen_prompt = False
        while time.time() - t0 < 150:
            h.keypress(57); time.sleep(4)
            if at_prompt(h): seen_prompt = True
            if rd(h, 0x1021, 1)[0] == 2 and int(rd(h, 0x23c0, 4).hex(), 16) != 0 and h.peekw(0x100e) > 30: race = True; break
        c1 = h.peekw(0x100e); time.sleep(4); c2 = h.peekw(0x100e)
        L(f"two-drive route (disk 2 in B from power-on, campaign disk in {a.where or a.key}): race reached {race} in {int(time.time()-t0)} s, 'Insert Disk 2' prompt ever shown: {seen_prompt}; $100e {c1} -> {c2}; marker {rd(h, 0xb2700, 4)}")
        L("screenshot race", h.shot(str(OUT / f"e2_{a.name}_7race.png")))
    elif not a.noride:
        # --- the game's own flow: SPACE -> map -> 'Insert Disk 2' prompt (the campaign disk is still in the drive: the check must fail and the prompt must show)
        t0 = time.time(); found = False
        while time.time() - t0 < 150:
            h.keypress(57); time.sleep(4)
            if h.vbl() > 0 and at_prompt(h): found = True; break
        L("game's own 'Insert Disk 2' prompt shown:", found, "t", int(time.time() - t0), "VBL", h.vbl())
        L("screenshot", h.shot(str(OUT / f"e2_{a.name}_6disk2prompt.png")))
        if found:
            dd = h.scratch / "disk2.st"
            if not dd.exists(): shutil.copy(d2, dd)
            h.cmd(f"hatari-option --disk-{(a.where or a.key).lower() if not a.startb else 'a'} {dd}"); time.sleep(2)
            h.keypress(57)
            t1 = time.time()
            while time.time() - t1 < 60:
                time.sleep(5)
            c1 = h.peekw(0x100e); time.sleep(4); c2 = h.peekw(0x100e)
            m21 = rd(h, 0x1021, 1).hex()
            L(f"race after disk 2: $1021={m21} $100e {c1} -> {c2}; prompt gone: {not at_prompt(h)}; marker $b2700: {rd(h, 0xb2700, 4)}")
            L("screenshot race", h.shot(str(OUT / f"e2_{a.name}_7race.png")))
    L("RESULT done", a.name)
finally:
    close(h)
