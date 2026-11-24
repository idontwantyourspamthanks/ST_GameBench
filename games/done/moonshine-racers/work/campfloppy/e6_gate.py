"""E6: the 2 MB gate on the FLOPPY build (private build with core_floppy.s two-list table + stage-0 phystop capture + gated fl_camp at site $7252).
At the first title loop: marker/flag/site bytes; RAM $1000-$B26FF dumped for the 1 MB A/B compare; F10 -> prompt (>= 2 MB) or the stock start (1 MB).
usage: e6_gate.py NAME --build work/campfloppy/buildcamp [--machine ste --mem 1024 --tos T]"""
import argparse, re, sys, time
from pathlib import Path
from cf import *
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--build", default=str(HERE / "buildcamp")); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--tos")
ap.add_argument("--f10", action="store_true")
a = ap.parse_args()
OUT = HERE / "logs"; log = open(OUT / f"e6_{a.name}.txt", "w")
def L(*x):
    s = " ".join(str(v) for v in x); print(s, flush=True); log.write(s + "\n"); log.flush()
h = mk(Path(a.build) / "disk_a.st", machine=a.machine, mem=a.mem, tos=a.tos, fast=True)
try:
    L("cell", a.name, a.machine, a.mem, a.build)
    dump = HERE / "snap" / f"gate_{a.name}.bin"; dump.parent.mkdir(exist_ok=True)
    cm = h.scratch / "t.txt"; cm.write_text(f"savebin {dump} $1000 $b1700\nm $b2700 8\nm $74fe 6\nm $7252 6\nm $72c4 6\nm $77da 12\nm $fda2 6\nm $731e 6\nm $b2704 4\nm $b9f00 6\nm $42e 4\n")
    n0 = len(h._logtext()); h.cmd(f"hatari-debug b pc = $7242 :trace :once :file {cm}")
    assert wait_log(h, r"Changed back to", n0, 300), "no title"
    time.sleep(2); txt = h._logtext()[n0:]
    for l in txt.splitlines():
        if re.match(r"^[0-9A-F]{8}: ", l): L("  ", l.strip()[:60])
    L("title reached at VBL", h.vbl(), "| dump", dump, dump.stat().st_size)
    if a.f10:
        h.keypress(68); time.sleep(5)
        L("F10 pressed; screenshot", h.shot(str(OUT / f"e6_{a.name}_f10.png")))
        L("$60ff", rd(h, 0x60ff, 1).hex(), "$1021", rd(h, 0x1021, 1).hex(), "prompt (disk-2) shown", at_prompt(h))
        h.keypress(1); time.sleep(3)
        L("after ESC / next key; screenshot", h.shot(str(OUT / f"e6_{a.name}_after.png")))
    L("RESULT done")
finally:
    close(h)
