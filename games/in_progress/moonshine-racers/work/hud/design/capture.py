#!/usr/bin/env python3
"""Capture clean frames: restore a snapshot in its own Hatari (own scratch dir /tmp/msrhd_<tag>, own memstate copy), run to a
chosen pass state with a debugger breakpoint, dump both screen buffers + palette tables + state, and take a Hatari screenshot
with --borders false (640x400 = 320x200 x 2, no border).  Usage: capture.py <snapshot> <tag> <cond> [wait_s]
cond = extra breakpoint condition at $7b86 (end of pass), e.g. "($11ab).b = 2" or "" ."""
import sys, time, shutil
from pathlib import Path
GAME = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(GAME / "tools"))
from msr import Moonshine
snap, tag, cond = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ""
wait = float(sys.argv[4]) if len(sys.argv) > 4 else 4
out = Path(__file__).resolve().parent / "cap"; out.mkdir(exist_ok=True)
wd = Path(f"/tmp/mhd_{tag}")
if wd.exists(): shutil.rmtree(wd)
h = Moonshine(snapshot=str(GAME / "work" / "snapshots" / snap), workdir=str(wd), extra=["--borders", "false"])
try:
    time.sleep(2)
    cf = wd / "cap.txt"
    cf.write_text(f"savebin {out}/{tag}_70000.bin $70000 $7d00\nsavebin {out}/{tag}_78000.bin $78000 $7d00\n"
                  f"savebin {out}/{tag}_pal.bin $3cc4 $4c\nm $1004 8\nm $1008 4\nm $ff8200 16\nm $ff8240 32\nm $100e 2\nm $11ab 8\nm $10ba 2\nm $10c0 2\nm $10ca 2\nm $10d8 4\nm $11d9 1\nm $11c2 2\n")
    c = f" && {cond}" if cond else ""
    cnt = f":{sys.argv[5]} " if len(sys.argv) > 5 else ""
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7b86{c} :trace :once {cnt}:file {cf}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[n0:]:
        if time.time() - t > 40: raise TimeoutError("bp never hit")
        time.sleep(0.2)
    log = h._logtext()[n0:]
    (out / f"{tag}_state.txt").write_text(log)
    time.sleep(1.0)
    p = h.shot(str(out / f"{tag}_shot.png"))
    print("shot", p)
finally:
    h.close()
