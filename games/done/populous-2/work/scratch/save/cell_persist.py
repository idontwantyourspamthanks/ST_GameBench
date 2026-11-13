"""Persistence cell: save, quit Hatari at once (= power off), cold boot a new Hatari on the same disk, load.
python3 cell_persist.py --tag X [--media hd|acsi] [--machine ..] [--tos ..] [--mem ..]"""
import argparse, hashlib, shutil, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *

ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--media", default="hd"); ap.add_argument("--build", default="build/Pop2Save")
ap.add_argument("--machine", default="ste"); ap.add_argument("--tos", default=None); ap.add_argument("--mem", type=int, default=2048)
a = ap.parse_args()
P = lambda *x: print(*x, flush=True)
OUT = SD / f"out_{a.tag}"; OUT.mkdir(exist_ok=True)
keep = Path(tempfile.mkdtemp(prefix="p2per-"))
md5 = lambda b: hashlib.md5(b).hexdigest()
# ---- phase 1
h, info = make(a.media, a.build, a.machine, a.tos, a.mem, a.tag + "1")
try:
    ok = h.boot_to_game(); P(f"CELL {a.tag} phase 1: {info} in_play={ok} marker={h.marker()!r} turn={turn(h)}")
    time.sleep(5)
    arm(h, 0x80300, OUT / "A.bin", "&& d0 = 1", tag="A")
    assert open_req(h); choose(h, "save"); name(h, "pers"); confirm(h)
    okf = waitfile(OUT / "A.bin"); r = wait_running(h, 90)
    A = (OUT / "A.bin").read_bytes() if okf else b""
    P(f"SAVE PERS: dump={okf} back_in_play={r} md5={md5(A)} turn_in_dump={int.from_bytes(A[0x16c:0x16e],'big') if A else None}")
    time.sleep(2)
    P("quitting Hatari 2 s after the save returned (= power off)")
    h.cmd("hatari-shortcut quit")
    for _ in range(30):
        if h.proc.poll() is not None:
            break
        time.sleep(1)
    P("hatari exited:", h.proc.poll() is not None)
    if a.media == "hd":
        p = hdfile(h, "PERS.GAM"); disk = p.read_bytes() if p.exists() else None
        shutil.copytree(h.R / "C" / "FILES", keep / "FILES", ignore=shutil.ignore_patterns("P2D", "P2M.FIC", "P2CR.TOS"))
    else:
        disk = imgfile(info["img"], "PERS.GAM"); shutil.copy(info["img"], keep / "hd.img")
    P(f"after power-off: PERS.GAM on disk {None if disk is None else len(disk)} B, equals RAM at the write: {disk == A and len(A) == SIZE}")
finally:
    shutil.copy(h.logpath, SD / f"{a.tag}1.log")
    h.close()
# ---- phase 2: a new Hatari, cold boot, load
if a.media == "hd":
    h, info = make("hd", a.build, a.machine, a.tos, a.mem, a.tag + "2", overlay=keep)
else:
    h, info = make("acsi", a.build, a.machine, a.tos, a.mem, a.tag + "2", img=keep / "hd.img")
try:
    ok = h.boot_to_game(); P(f"phase 2 (cold boot on the same disk): in_play={ok} marker={h.marker()!r} turn={turn(h)}")
    time.sleep(5)
    t_before = turn(h)
    arm(h, 0x2cc5e, OUT / "B.bin", tag="B")
    assert open_req(h); choose(h, "load"); time.sleep(1); shot(h, f"{a.tag}_dir.png"); name(h, "pers"); confirm(h)
    okb = waitfile(OUT / "B.bin", 60); r = wait_running(h, 90)
    B = (OUT / "B.bin").read_bytes() if okb else b""
    P(f"LOAD PERS after the cold boot: dump={okb} RAM after read == RAM at the save in the previous session: {B == A and len(A) == SIZE}; running={r} turn before {t_before} -> {turn(h)}")
    bad = logbad(h); P(f"LOG errors: {len(bad)}"); [P("  ", l) for l in bad[:6]]
    P(f"RESULT {a.tag}: " + ("PASS" if (okf and disk == A and B == A and r) else "CHECK"))
finally:
    shutil.copy(h.logpath, SD / f"{a.tag}2.log")
    h.close()
