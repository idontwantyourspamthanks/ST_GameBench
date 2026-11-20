"""Scratch harness for the floppy-campaign study (MSRCampFloppy): Hatari cells on the built floppy.  Private HOME via env (run_env.sh)."""
import re, shutil, sys, tempfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools")); sys.path.insert(0, str(GAME / "tools"))
from stharness import Hatari, TOS   # noqa

BUILD = HERE / "build"
REF = GAME / "work" / "ref" / "floppy_insert_disk2.png"
BOX = (170, 250, 660, 282)

def mk(disk_a=None, disk_b=None, machine="ste", mem=1024, tos=None, fast=False, trace=None, nob=False, extra=()):
    scratch = Path(tempfile.mkdtemp(prefix="msrcf_"))
    ex = ["--fastfdc", "yes" if fast else "no"]
    if trace: ex += ["--trace", trace]
    if disk_a:
        da = scratch / "disk1.st"; shutil.copy(disk_a, da); ex += ["--disk-a", str(da)]
    if disk_b:
        db = scratch / "disk2.st"; shutil.copy(disk_b, db); ex += ["--disk-b", str(db)]
    if nob: ex += ["--drive-b", "false"]
    ex += list(extra)
    h = Hatari(game_dir=GAME / "originals" / "floppy", machine=machine, memsize_kb=mem, tos=TOS[tos] if tos else None,
               autorun=None, files=[], extra=ex)
    h.scratch = scratch
    return h

def rd(h, a, n):
    """read n bytes at a via the debugger -> bytes"""
    out = h.debug(f"m ${a:x} {n}", 0.6 + n / 400)
    got = {}
    for m in re.finditer(r"^([0-9A-Fa-f]{8}):\s+((?:[0-9a-f]{2} )+)", out, re.M):
        base = int(m.group(1), 16)
        for i, b in enumerate(m.group(2).split()):
            got[base + i] = int(b, 16)
    return bytes(got.get(a + i, 0xEE) for i in range(n))

def close(h):
    h.close(); shutil.rmtree(h.R, ignore_errors=True); shutil.rmtree(h.scratch, ignore_errors=True)

def wait_log(h, pat, start, timeout=200, key=57, every=3.0):
    """poll the Hatari log from offset `start` for regex `pat`; press `key` every `every` s (None = no key)."""
    t0 = time.time(); last = 0
    while time.time() - t0 < timeout:
        if re.search(pat, h._logtext()[start:]):
            return True
        if key is not None and time.time() - last >= every:
            h.keypress(key); last = time.time()
        time.sleep(0.5)
    return False

def at_prompt(h):
    return h.screen_matches(REF, BOX)


def build_blob(src="campread.s"):
    """assemble the prototype, return {symbol: address}; outputs <stem>.bin / <stem>.lst"""
    stem = Path(src).stem
    r = subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-L", str(HERE / f"{stem}.lst"), "-o", str(HERE / f"{stem}.bin"), str(HERE / src)], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    sym = {}
    txt = (HERE / f"{stem}.lst").read_text()
    for m in re.finditer(r"^(\w+)\s+[AE]:([0-9A-F]{8})$", txt.split("Symbols by name:")[1].split("Symbols by value:")[0], re.M):
        sym[m.group(1)] = int(m.group(2), 16)
    return sym

def build_hooks(vars_addr):
    r = subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", f"-DVARS={vars_addr}", "-L", str(HERE / "camphooks.lst"), "-o", str(HERE / "camphooks.bin"), str(HERE / "camphooks.s")], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return (HERE / "camphooks.bin").stat().st_size
import subprocess
