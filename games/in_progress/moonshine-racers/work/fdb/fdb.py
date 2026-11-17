#!/usr/bin/env python3
"""Drive-B cells for the Moonshine floppy release (work/notes/floppy_driveb.md); private copy of the msrfloppy.py gate with drive-B modes.

    python3 work/fdb/fdb.py NAME DISK_A.st DISK_B.st MODE [--machine ste --mem 1024 --tos 1.62] [--nob] [--fast] [--tail 30] [--timeout 600]

MODE (disk 2 = DISK_B; Hatari real FDC timing = --fastfdc no unless --fast):
  swapA   disk 1 in A only; at the game's "Insert Disk 2" prompt disk 2 replaces disk 1 in drive A (the one-drive route, as msrfloppy.py gate)
  insB    disk 1 in A only; at the prompt disk 2 is inserted into drive B (A keeps disk 1)
  startB  disk 2 in drive B from power-on, disk 1 in A
  wrongB  a copy of disk 1 sits in drive B from power-on; at the prompt disk 2 replaces disk 1 in A (B must be rejected, A used)
  none    disk 1 in A only, nothing is inserted: the prompt must stay up and answer, no hang
Prints raw lines; the FDC trace (--trace fdc) is counted per drive from the moment of the key press that follows the insert."""
import argparse, re, shutil, sys, tempfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
sys.path.insert(0, str(GAME / "tools"))
from msrfloppy import parse_question, answer_for   # noqa: E402  (the original floppy asks the manual question)
from stharness import Hatari, TOS   # noqa: E402

REF = GAME / "work" / "ref" / "floppy_insert_disk2.png"
BOX = (170, 250, 660, 282)
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)


def last_mem(out):
    m = [l for l in out.splitlines() if re.match(r"^[0-9A-Fa-f]{8}: ", l)]
    return m[-1].strip() if m else out.strip()[-120:]


def peekb(h, a):
    out = h.debug(f"m ${a:x} 1", 0.6)
    return int(re.findall(rf"{a:08x}:\s+([0-9a-f]{{2}})", out, re.I)[-1], 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name"); ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("mode", choices=("swapA", "insB", "startB", "none", "wrongB"))
    ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--tos")
    ap.add_argument("--nob", action="store_true", help="--drive-b false (a machine with ONE drive)")
    ap.add_argument("--fast", action="store_true"); ap.add_argument("--tail", type=float, default=30)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--answer", action="store_true", help="original disk A: type the manual answer (read out of RAM) when the question shows")
    ap.add_argument("--vars", default="", help="hex address of the fl_driveb variables (unit, pref[2]): printed at the end")
    ap.add_argument("--drive", action="store_true", help="after the race is up: hold 'up' ($6105 = 1, as msrfloppy.py gate --cpu) for 30 s and shoot the HUD (a short drive)")
    ap.add_argument("--bp", default="", help="comma list of PCs: breakpoint + register dump at each hit")
    a = ap.parse_args()
    log = open(OUT / f"{a.name}.log", "w")

    def L(*x):
        s = " ".join(str(v) for v in x)
        print(s, flush=True)
        log.write(s + "\n"); log.flush()

    scratch = Path(tempfile.mkdtemp(prefix="msr_fdb_"))
    da, db = scratch / "disk1.st", scratch / "disk2.st"
    shutil.copy(a.a, da); shutil.copy(a.b, db)
    extra = ["--disk-a", str(da), "--fastfdc", "yes" if a.fast else "no", "--trace", "fdc"]
    if a.mode == "startB":
        extra += ["--disk-b", str(db)]
    if a.mode == "wrongB":                       # drive B holds a COPY OF DISK 1 (wrong disk for the check); disk 2 is swapped into A at the prompt
        d1b = scratch / "disk1_inB.st"
        shutil.copy(a.a, d1b)
        extra += ["--disk-b", str(d1b)]
    if a.nob:
        extra += ["--drive-b", "false"]
    h = Hatari(game_dir=GAME / "originals" / "floppy", machine=a.machine, memsize_kb=a.mem, tos=TOS[a.tos] if a.tos else None,
               autorun=None, files=[], extra=extra)
    L("cell", a.name, a.mode, a.machine, a.mem, a.tos, "disks", a.a, a.b, "nob" if a.nob else "", "fast" if a.fast else "realfdc")
    ok = False
    try:
        for i, pc in enumerate(x for x in a.bp.split(",") if x):
            cf = scratch / f"bp{i}.txt"
            cf.write_text("r\n")
            h.cmd(f"hatari-debug b pc = ${pc} :trace :file {cf}")
            time.sleep(0.4)
        t0 = time.time(); found = False; race_np = False; last = None
        while time.time() - t0 < a.timeout:
            time.sleep(3)
            v = h.vbl()
            if a.mode == "startB" and v > 2000:       # disk 2 already in B: the game may never ask; the race itself is the proof
                c = h.peekw(0x100E)
                if last is not None and c > 100 and c > last + 20 and not h.screen_matches(REF, BOX):
                    race_np = True
                    L("startB: race reached WITHOUT the disk-2 prompt: $100e", last, "->", c, "vbl", v, "t", int(time.time() - t0))
                    break
                last = c
            if v > 1500 and h.screen_matches(REF, BOX):
                found = True
                break
            if a.answer and v > 700 and h.screen_matches(HERE / "prompt_ref.png", (96, 250, 736, 343), tol=8.0):
                dumpf = scratch / "ram.bin"
                h.debug(f"savebin {dumpf} 0 $100000", 2.5)
                ram = dumpf.read_bytes()
                q = parse_question(ram); word = answer_for(ram, q) if q else None
                L("question", q, "answer", word, "vbl", v)
                if word:
                    SC = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44]))
                    for ch in word:
                        h.keypress(SC[ch]); time.sleep(0.3)
                    h.keypress(28)
                    time.sleep(2)
                continue
            h.keypress(57)
        L("disk-2 prompt", found, "t", int(time.time() - t0), "vbl", h.vbl())
        L("prompt shot", h.shot(str(OUT / f"{a.name}_prompt.png")))
        L("marker $b2700:", last_mem(h.debug("m $b2700 8", 0.8)))
        if not found and not race_np:
            raise SystemExit("no disk-2 prompt")
        mark = 0 if race_np else len(h._logtext())
        n0 = h.vbl()
        if a.mode in ("swapA", "wrongB"):
            h.cmd(f"hatari-option --disk-a {db}")
        elif a.mode == "insB":
            h.cmd(f"hatari-option --disk-b {db}")
        L("mode action done:", a.mode)
        time.sleep(2)
        if a.mode == "none":
            for k in range(int(a.tail // 6) + 1):
                h.keypress(57)
                time.sleep(6)
                L("none: vbl", h.vbl(), "prompt still shown", h.screen_matches(REF, BOX))
        else:
            if not race_np:
                h.keypress(57)
            t1 = time.time()
            race = False
            while time.time() - t1 < a.tail:
                time.sleep(5)
                st = (peekb(h, 0x1021), h.peekw(0x100E))
                L(f"t+{time.time() - t1:4.0f}s vbl {h.vbl()} $1021/$100e {st}")
            st1 = h.peekw(0x100E); time.sleep(5); st2 = h.peekw(0x100E)
            ok = peekb(h, 0x1021) == 2 and st2 != st1 and not h.screen_matches(REF, BOX)
            L("race advancing ($100e %d -> %d, mode %d, prompt gone %s): %s" % (st1, st2, peekb(h, 0x1021), not h.screen_matches(REF, BOX), ok))
            L("race shot", h.shot(str(OUT / f"{a.name}_race.png")))
            if a.drive and ok:
                h.debug("w $6105 $01"); time.sleep(30)
                L("drive: up held 30 s, $100e", h.peekw(0x100E), "shot", h.shot(str(OUT / f"{a.name}_drive.png")))
                h.debug("w $6105 $00")
            time.sleep(0.5)
        L("marker $b2700:", last_mem(h.debug("m $b2700 8", 0.8)))
        L("tick clock $b8f00:", last_mem(h.debug("m $b8f00 8", 0.8)))
        if a.vars:
            L("driveb vars (unit, pref[0], pref[1]) @$%x:" % int(a.vars, 16), last_mem(h.debug(f"m ${a.vars} 6", 0.8)))
        lt = h._logtext()
        nb = len(re.findall(r"fdc change drive/side io_porta_old=0x\w+ io_porta_new=0x\w+ side \d->\d drive -?\d->1\b", lt))
        L("drive B selected (PSG change drive ->1) %d time(s) in the whole run" % nb)
        for tag, text in (("whole run", lt), ("after the insert", lt[mark:])):
            rd = [l for l in text.splitlines() if "fdc read sector" in l]
            cnt = {}
            for l in rd:
                m = re.search(r"drive=(\d)", l)
                cnt[m.group(1) if m else "?"] = cnt.get(m.group(1) if m else "?", 0) + 1
            L(f"fdc read sectors {tag}: per drive {cnt}")
            if tag != "whole run" or True:
                dr1 = [l for l in rd if "drive=1" in l]
                L(f"  drive=1 reads {tag}: {len(dr1)}; first/last:", dr1[0].strip() if dr1 else "-", "|", dr1[-1].strip() if dr1 else "-")
        post = [l for l in lt[mark:].splitlines() if "fdc read sector" in l or "fdc type" in l or "fdc" in l and "drive=1" in l]
        (OUT / f"{a.name}_fdc_after_insert.txt").write_text("\n".join(post) + "\n")
        (OUT / f"{a.name}_fdc_all.txt").write_text("\n".join(l[:150] for l in lt.splitlines() if "fdc change drive" in l or "fdc type" in l or "fdc read sector" in l) + "\n")
        L("RESULT", a.name, "OK" if ok else ("n/a" if a.mode == "none" else "FAIL"))
    finally:
        h.close()
        shutil.rmtree(h.R, ignore_errors=True)       # the fdc trace log of a cell is 0.4-1.8 GB on /tmp (RAM): keep only the extracted lines
        shutil.rmtree(scratch, ignore_errors=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
