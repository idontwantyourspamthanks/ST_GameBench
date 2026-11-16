#!/usr/bin/env python3
"""Boot a floppy image (plain .ST) on the harness and navigate to the first race; the floppy twin of tools/msr.py.

    python3 tools/msrfloppy.py boot  DISK_A.st [--disk-b B.st] [--machine ste --mem 1024 --tos 1.62]
    python3 tools/msrfloppy.py trace DISK_A.st --pcs 78000,6f5e --mem-at b2700:8 [--dump f.bin@PC] [--timeout 300]
    python3 tools/msrfloppy.py gate  build/floppy/disk_a.st --disk-b build/floppy/disk_b.st --machine ste --mem 1024 --tos 1.62 --name ste_1024   # patched build: intro, disk-2 swap, race
The game boots from drive A (10 sectors x 2 sides x 80 tracks); TOS boots it because its boot sector has a branch at offset 0
(no AUTO folder, no hard disk needed: the harness's empty drive C is not used by the game).
`boot` waits for the first race the same way tools/msr.py boot_to_race() does: presses SPACE (scancode 57) and polls the game's
mode byte $1021 == 2 and frame counter $100e > 40."""
import argparse, re, shutil, sys, tempfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BENCH / "tools"))
from stharness import Hatari, TOS   # noqa: E402


def mk(disk_a, disk_b=None, machine="ste", mem=1024, tos=None, workdir=None, trace=None):
    h = Hatari(game_dir=GAME / "originals" / "floppy", machine=machine, memsize_kb=mem, tos=TOS[tos] if tos else None,
               autorun=None, files=[], workdir=workdir,
               extra=["--disk-a", str(Path(disk_a).resolve())] + (["--disk-b", str(Path(disk_b).resolve())] if disk_b else [])
                     + (["--trace", trace] if trace else []))
    return h


def peekb(h, a):
    out = h.debug(f"m ${a:x} 1", 0.6)
    return int(re.findall(rf"{a:08x}:\s+([0-9a-f]{{2}})", out, re.I)[-1], 16)


def boot_to_race(h, timeout=400, log=print, shots=None, first_wait=60):
    t0 = time.time()
    n = 0
    while time.time() - t0 < timeout:
        time.sleep(4)
        v = h.vbl()
        try:
            st = (peekb(h, 0x1021), h.peekw(0x100E))
        except Exception:
            st = None
        log(f"t={time.time() - t0:5.0f}s vbl={v} $1021/$100e={st}")
        if shots:
            h.shot(f"{shots}_{n:02d}.png")
        n += 1
        if v > first_wait:
            if st and st[0] == 2 and st[1] > 40:
                return True
            h.keypress(57)
    return False


def _stack(h):
    """Dump registers and the top of the stack (call chain) at the current CPU state."""
    out = h.debug("r", 1.0)
    print(out)
    import re as _re
    m = _re.search(r"A7\s+([0-9A-F]{8})", out)
    a7 = int(m.group(1), 16)
    print(f"A7 = ${a7:x}")
    print(h.debug(f"m ${a7 - 32:x} 64", 1.0))
    print(h.debug("e PC", 0.5))


def parse_question(ram: bytes):
    """The protection question as the loader built it in RAM: the text buffer holds "PAGE  4,\rPARAGRAPH  5,\rLINE  5,\rWORD  9."
    -> (page, para, line, word).  None if the buffer is not there."""
    # the question block is the first "PAGE n ... PARAGRAPH n ... LINE n ... WORD n" in the buffer (the example line comes later)
    m = re.search(rb"PAGE\D{1,12}(\d+)\D{1,12}PARAGRAPH\D{1,12}(\d+)\D{1,12}LINE\D{1,12}(\d+)\D{1,12}WORD\D{1,12}(\d+)", ram)
    return tuple(int(x) for x in m.groups()) if m else None


def answer_for(ram: bytes, q):
    """The answer word for question `q` = (page, paragraph, line, word).  The table entries are "<space><4 numbers><WORD>" with single
    spaces between the first numbers and no separator before the word (the digit string is ambiguous, e.g. " 4 4 412PLYMOUTH" is
    4/4/4/12), so every split of each entry's digits is tried and the one that equals the question wins."""
    if not q:
        return None
    for ent in ram.split(b"\x00"):
        if not ent.startswith(b" ") or len(ent) > 40:
            continue
        m = re.match(rb"^([\d ]+)([A-Z]+)$", ent)
        if not m:
            continue
        digits = m.group(1).replace(b" ", b"").decode()
        word = m.group(2).decode()
        n = len(digits)
        for a in range(1, min(3, n)):
            for b in range(a + 1, min(a + 3, n)):
                for c in range(b + 1, min(b + 3, n)):
                    if n - c > 2:
                        continue
                    cand = (int(digits[:a]), int(digits[a:b]), int(digits[b:c]), int(digits[c:]))
                    if cand == tuple(q):
                        return word
    return None


def parse_answer_table(ram: bytes):
    """The manual's answer table as shipped on disk A: entries " 3 2 3 2DRIVE" (space, four numbers, then the word) -> {(p,q,l,w): WORD}."""
    out = {}
    for m in re.finditer(rb" (\d{1,2}) (\d{1,2}) (\d{1,2}) ?(\d{1,2})([A-Z]+)", ram):
        p, q, l, w = (int(x) for x in m.groups()[:4])
        out.setdefault((p, q, l, w), m.group(5).decode())
    return out


DISK2_REF = GAME / "work" / "ref" / "floppy_insert_disk2.png"      # crop of the game's "Insert Disk 2 and press a key." line
DISK2_BOX = (170, 250, 660, 282)


def gate(h, a):
    """The floppy build gate, one machine: cold boot of disk A ONLY (a single-drive machine), SPACE through the intro, record the first
    post-intro screen (no manual question), the marker at $B2700, then the game's own "Insert Disk 2 and press a key." prompt: the swap is
    `hatari-option --disk-a <copy of disk B>` (Hatari refuses an image that is also in drive B / the config, hence the copy), then SPACE.
    Prints raw peeks and writes screenshots build/shots/floppy_<name>/NN_vblV.png (the whole sequence), floppy_<name>_{prompt,race}.png."""
    shots = GAME / "build" / "shots"
    seqdir = shots / f"floppy_{a.name}"
    seqdir.mkdir(parents=True, exist_ok=True)
    for f in seqdir.glob("*.png"):
        f.unlink()
    seq = []
    t0 = time.time(); got_intro = False; found = False
    while time.time() - t0 < a.timeout:
        time.sleep(3)
        v = h.vbl()
        st = (peekb(h, 0x1021), h.peekw(0x100E))
        if v > 900:
            seq.append(h.shot(str(seqdir / f"{len(seq):02d}_vbl{v}.png")))      # every screen from the cover on: no manual question may be among them
        if not got_intro and st[0] == 2:
            got_intro = True
            print("first mode-2 (story) screen:", seq[-1] if seq else None, "$1021/$100e", st, "vbl", v)
        if v > 1500 and h.screen_matches(DISK2_REF, DISK2_BOX):
            found = True
            break
        h.keypress(57)
    print("disk-2 prompt", found, "t", int(time.time() - t0), "vbl", h.vbl(), "story screen seen", got_intro, "screens saved", len(seq), "in", seqdir)
    print("prompt shot", h.shot(str(shots / f"floppy_{a.name}_prompt.png")))
    print("marker $b2700:", h.debug("m $b2700 8", 0.8).strip().splitlines()[-1])
    if not found:
        raise SystemExit("no disk-2 prompt")
    d2 = Path(tempfile.mkdtemp(prefix="msr_d2_")) / "disk2.st"
    shutil.copy(a.disk_b, d2)
    h.cmd(f"hatari-option --disk-a {d2}")
    time.sleep(2)
    h.keypress(57)
    time.sleep(30)
    print("after swap: vbl", h.vbl(), "$1021/$100e", (peekb(h, 0x1021), h.peekw(0x100E)))
    print("race shot", h.shot(str(shots / f"floppy_{a.name}_race.png")))
    print("marker $b2700:", h.debug("m $b2700 8", 0.8).strip().splitlines()[-1])
    print("tick clock $b8f00:", h.debug("m $b8f00 8", 0.8).strip().splitlines()[-1])
    print("road magic $d0000:", h.debug("m $d0000 8", 0.8).strip().splitlines()[-1], " WPTR $e7040:", h.debug("m $e7040 4", 0.8).strip().splitlines()[-1])
    if a.cpu:                                   # extra frames need spare time: raise the CPU clock, hold 'up', count the extra frames of the blob (mx_sync)
        h.set_cpuclock(a.cpu); time.sleep(2); h.debug("w $6105 $01"); time.sleep(40)
        print(f"extra-frame counters at {a.cpu} MHz, up held, $100e {h.peekw(0x100E)}: frames/groups/ticks $b8f38:", h.debug("m $b8f38 12", 0.8).strip().splitlines()[-1],
              " skip reasons $b8f54:", h.debug("m $b8f54 18", 0.8).strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("boot", "trace", "shot", "state", "prof", "stack", "auto", "gate"))
    ap.add_argument("disk")
    ap.add_argument("--disk-b"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--tos"); ap.add_argument("--timeout", type=int, default=400); ap.add_argument("--first-wait", type=int, default=60)
    ap.add_argument("--pcs"); ap.add_argument("--mem-at", default=""); ap.add_argument("--dump", action="append", default=[])
    ap.add_argument("--snap"); ap.add_argument("--shots"); ap.add_argument("--gemdos", action="store_true")
    ap.add_argument("--secs", type=int, default=10, help="wait this long before the command acts (state/prof/shot)")
    ap.add_argument("--trace", help="Hatari trace flags (e.g. fdc)")
    ap.add_argument("--cpu", type=int, default=0, help="gate: after the race starts set this CPU clock (MHz), hold up and print the extra-frame counters")
    ap.add_argument("--name", default="gate", help="gate: prefix of the screenshots build/shots/floppy_<name>_*.png")
    a = ap.parse_args()
    h = mk(a.disk, None if a.cmd == "gate" else a.disk_b, a.machine, a.mem, a.tos, trace=a.trace)
    try:
        if a.cmd == "gate":
            gate(h, a)
        elif a.cmd == "boot":
            ok = boot_to_race(h, a.timeout, shots=a.shots, first_wait=a.first_wait)
            print("RESULT in_race =", ok, "vbl", h.vbl())
            for x in (a.mem_at.split(",") if a.mem_at else []):
                ad, ln = x.split(":")
                print(f"PEEK ${int(ad,16):x}:", h.debug(f"m ${ad} {ln}", 0.8).strip())
            if a.shots:
                print("last shot", h.shot(None))
            if a.snap:
                h.savemem(a.snap)
        elif a.cmd == "auto":
            t0 = time.time(); found = False
            ref = Path("/tmp/prompt_ref.png")
            while time.time() - t0 < 200:
                if h.screen_matches(ref, (96, 250, 736, 343), tol=8.0):
                    found = True
                    break
                h.keypress(0x39)
                time.sleep(3)
            print("prompt", found, "vbl", h.vbl())
            if not found:
                raise SystemExit("no prompt")
            h.debug(f"savebin {GAME / 'work' / 'floppy' / 'ram_prompt.bin'} 0 $100000", 2.5)
            ram = (GAME / "work" / "floppy" / "ram_prompt.bin").read_bytes()
            q = parse_question(ram)
            tab = parse_answer_table(ram)
            print("question", q, "table entries", len(tab))
            word = answer_for(ram, q) if q else None
            print("answer", word)
            if not word:
                raise SystemExit("no answer for the question")
            SC = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44]))
            for ch in word:
                h.keypress(SC[ch]); time.sleep(0.3)
            h.keypress(28)
            time.sleep(2)
            print("accepted, vbl", h.vbl(), "shot", h.shot(str(GAME / "build" / "shots" / "auto_1.png")))
            ok = boot_to_race(h, a.timeout, shots=None, first_wait=a.first_wait)
            print("RESULT in_race =", ok, "vbl", h.vbl())
            print("shot", h.shot(str(GAME / "build" / "shots" / "auto_race.png")))
        elif a.cmd == "stack":
            time.sleep(a.secs)
            _stack(h)
        elif a.cmd == "prof":
            time.sleep(a.secs)
            from msr import prof
            out = str(GAME / "work" / "floppy" / "prof_floppy.txt")
            prof(h, a.first_wait, out)
            rows = []
            for l in open(out):
                f = l.split()
                if len(f) >= 2:
                    try:
                        rows.append((int(f[1]), f[0]))
                    except ValueError:
                        pass
            rows.sort(reverse=True)
            tot = sum(r[0] for r in rows) or 1
            print(f"profile: {len(rows)} addresses, {tot} cycles")
            for c, addr in rows[:25]:
                print(f"   {addr}  {c:10d}  {100.0 * c / tot:5.2f}%")
        elif a.cmd == "state":
            time.sleep(a.secs)
            out = str(GAME / "work" / "floppy" / "ram_floppy.bin")
            h.debug(f"savebin {out} 0 ${a.mem * 1024:x}", 2.5)
            print("vbl", h.vbl(), "ram", out, "shot", h.shot(str(GAME / "build" / "shots" / "floppy_state.png")))
        elif a.cmd == "shot":
            time.sleep(a.secs)
            if a.trace:
                import collections
                lines = [l for l in h._logtext().splitlines() if "fdc read sector" in l or "fdc write sector" in l or "fdc type" in l]
                print(f"{len(lines)} fdc trace line(s); first 40:")
                for l in lines[:40]:
                    print("  ", l)
            print("vbl", h.vbl(), "shot", h.shot(str(GAME / "build" / "shots" / f"floppy_{a.secs}s.png")))
        else:
            h.debug("b all", 0.3)
            pcs = [int(x, 16) for x in a.pcs.split(",")]
            dumps = {int(x.split("@")[1], 16): x.split("@")[0] for x in a.dump}
            for pc in pcs:
                f = h.R / f"hook_{pc:x}.txt"
                lines = ["r"] + [f"m ${m.split(':')[0]} {int(m.split(':')[1])}" for m in a.mem_at.split(",") if m]
                if pc in dumps:
                    lines.append(f"savebin {dumps[pc]} 0 ${a.mem * 1024:x}")
                f.write_text("\n".join(lines) + "\n")
                h.cmd(f"hatari-debug b pc = ${pc:x} :trace :once :file {f}")
                time.sleep(0.3)
            t = time.time()
            while time.time() - t < a.timeout:
                if h._logtext().count("Removed CPU breakpoint") >= len(pcs):
                    break
                time.sleep(2)
            time.sleep(3)
            log = h._logtext()
            print("\n".join(l for l in log.splitlines()
                            if re.search(r"breakpoint|pc = |^\s+D0|^\s+D4|^\s+A0|^\s+A4|^\s+A6|SR=|USP|^[0-9a-fA-F]{8}: |Fread|Fseek|Pexec|Flop|WARN|Bus", l)))
    finally:
        print("log:", h.logpath)
        h.close()

if __name__ == "__main__":
    main()
