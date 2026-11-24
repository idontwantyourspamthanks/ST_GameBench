"""E8: which disk reads does the game make between the first title loop and the 'Insert Disk 2' prompt (does it ever need disk 1 again)?  Breakpoint on the driver $cac0, d0/d1/d2 per call."""
import re, sys, time
from cf import *
h = mk(BUILD / "disk_a.st", machine="ste", mem=2048, fast=True)
log = open(HERE / "logs" / "e8_reads.txt", "w")
def L(*x):
    s = " ".join(str(v) for v in x); print(s, flush=True); log.write(s + "\n"); log.flush()
try:
    cm = h.scratch / "t.txt"; cm.write_text("w $60ff $00\n")
    n0 = len(h._logtext()); h.cmd(f"hatari-debug b pc = $7242 :trace :once :file {cm}")
    assert wait_log(h, r"Changed back to", n0, 300), "no title"
    L("title loop reached, VBL", h.vbl())
    rc = h.scratch / "r.txt"; rc.write_text("r\n")
    n1 = len(h._logtext()); h.cmd(f"hatari-debug b pc = $cac0 :trace :file {rc}")
    time.sleep(1)
    t0 = time.time(); found = False
    while time.time() - t0 < 150:
        h.keypress(57); time.sleep(4)
        if at_prompt(h): found = True; break
    L("disk-2 prompt reached:", found, "VBL", h.vbl())
    time.sleep(8)
    h.debug("b all", 0.3)
    txt = h._logtext()[n1:]
    calls = re.findall(r"D0 (\w{8})   D1 (\w{8})   D2 (\w{8})   D3 (\w{8})", txt)
    L("driver calls ($cac0 entries) from the title to the prompt (+8 s of prompt loop):", len(calls))
    from collections import Counter
    c = Counter((x[0], int(x[1], 16), int(x[2], 16)) for x in calls)
    for (d0, d1, d2), n in sorted(c.items()): L(f"  d0={d0} d1(linear sector)={d1} d2(count)={d2}  x{n}")
    L("RESULT done")
finally:
    close(h)
