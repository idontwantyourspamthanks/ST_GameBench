"""Floppy build cell: python3 cell_floppy.py --tag X [--machine ste|megaste] [--tos 1.62|2.06] [--mem 2048|4096] [--build build/Pop2SaveF]
1. SAVE with the default drawer = A:\\FILES (the boot disk has 43 KB free, a save is 56,690 B): the game's DISK FILE ERROR, nothing left behind on the disk.
2. swap A: for a blank formatted 720K (hatari-option --disk-a), SAVE with drawer A:\\ -> a file; LOAD it back; the directory lists it.
The Hatari log is scanned for FDC verify failures (the head-position symptom pop2_floppy_head fixes)."""
import argparse, shutil, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *

ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--build", default="build/Pop2SaveF")
ap.add_argument("--machine", default="ste"); ap.add_argument("--tos", default=None); ap.add_argument("--mem", type=int, default=2048)
a = ap.parse_args()
P = lambda *x: print(*x, flush=True)
OUT = SD / f"out_{a.tag}"; OUT.mkdir(exist_ok=True)
td = Path(tempfile.mkdtemp(prefix="p2fl-"))
blank = td / "blank.st"
subprocess.run(["mformat", "-C", "-f", "720", "-i", str(blank), "::"], check=True)
h, info = make("floppy", a.build, a.machine, a.tos, a.mem, a.tag)
st = Path(info["st"])


def free(img):
    md = subprocess.run(["mdir", "-i", str(img), "::"], capture_output=True, text=True).stdout
    return int(re.findall(r"([\d ]+) bytes free", md)[-1].replace(" ", ""))


try:
    free0 = free(st)
    ok = h.boot_to_game(); P(f"CELL {a.tag}: {info} in_play={ok} marker={h.marker()!r} turn={turn(h)} boot disk free bytes {free0}")
    time.sleep(5)
    h.cmd("hatari-option --trace fdc"); time.sleep(1)
    # 1. the boot disk is full for a save
    arm(h, 0x80300, OUT / "A0.bin", "&& d0 = 1", tag="A0")
    assert open_req(h); choose(h, "save"); name(h, "t1"); confirm(h)
    time.sleep(45); shot(h, f"{a.tag}_full1.png")
    P(f"1. SAVE to A:\\FILES on the boot disk: write call reached={(OUT/'A0.bin').exists()}; shot {a.tag}_full1.png; frozen (box up)={frozen(h)}")
    h._click(416, 177, 3); shot(h, f"{a.tag}_full2.png")
    cancel(h); time.sleep(2); h._click(416, 370, 3)
    P(f"   after the error box: running={wait_running(h, 30)} turn={turn(h)}")
    # 2. swap in a blank disk
    h.cmd(f"hatari-option --disk-a {blank}"); time.sleep(4)
    arm(h, 0x80300, OUT / "A1.bin", "&& d0 = 1", tag="A1")
    assert open_req(h); choose(h, "save"); drawer(h, "a:\\"); name(h, "t1"); confirm(h)
    okf = waitfile(OUT / "A1.bin", 60); r = wait_running(h, 90)
    P(f"2. SAVE A:\\T1.GAM on the swapped-in blank disk: dump={okf} back_in_play={r} turn={turn(h)}")
    time.sleep(5)
    arm(h, 0x2cc5e, OUT / "B1.bin", tag="B1")
    assert open_req(h); choose(h, "load"); drawer(h, "a:\\"); time.sleep(1); shot(h, f"{a.tag}_dir.png"); name(h, "t1"); confirm(h)
    okb = waitfile(OUT / "B1.bin", 90); r = wait_running(h, 90)
    A1 = (OUT / "A1.bin").read_bytes() if okf else b""; B1 = (OUT / "B1.bin").read_bytes() if okb else b""
    P(f"   LOAD A:\\T1.GAM: dump={okb} RAM after read == RAM at save: {B1 == A1 and len(A1) == SIZE}; running={r} turn={turn(h)}")
    time.sleep(2)
    h.cmd(f"hatari-option --disk-a {st}"); time.sleep(4)        # eject the blank disk (writes it back), boot disk back in
    f = subprocess.run(["mtype", "-i", str(blank), "::T1.GAM"], capture_output=True).stdout
    P(f"   blank disk after the session: T1.GAM {len(f)} B equals the dump: {f == A1}; mdir:", subprocess.run(["mdir", "-i", str(blank), "::"], capture_output=True, text=True).stdout.strip().splitlines()[-2:])
    P(f"   boot disk free bytes now {free(st)} (before {free0}); GAM files on it:", subprocess.run(["mdir", "-i", str(st), "::FILES"], capture_output=True, text=True).stdout.count("GAM"))
    log = h._logtext()
    vf = [l for l in log.splitlines() if "verify track failed" in l or "verify" in l.lower() and "fail" in l.lower()]
    P(f"FDC: lines with a failed verify: {len(vf)}", vf[:3])
    bad = logbad(h); P(f"LOG errors: {len(bad)}"); [P("  ", l) for l in bad[:6]]
finally:
    shutil.copy(h.logpath, SD / f"{a.tag}.log")
    h.close()
