"""Timer-B ISR cost and count: Hatari profile cycles in $d616-$d6f8 + executions of $d616, over 400 VBL."""
import sys, json; sys.path.insert(0,'.')
from tlib import *
from live import *
from tickpatch import sync_only
variant, mhz = sys.argv[1], int(sys.argv[2])
h = open_snap("ste1m_race_start.sav", mhz)
try:
    if variant in ("D", "E"):
        b, s, _ = sync_only("sync.s" if variant == "D" else "sync2.s"); apply_live(h, b, s)
    time.sleep(1)
    # count executions of $d616 and passes, over 400 VBL
    f = h.R / "tb.txt"; f.write_text("")
    n0 = len(h._logtext())
    v = h.vbl()
    h.cmd(f"hatari-debug b pc = $d616 :trace")
    h.cmd(f"hatari-debug b VBL > {v + 400} :trace :once")
    t0 = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[n0:]:
        if time.time() - t0 > 300: break
        time.sleep(0.5)
    h.debug("b all", 0.5)
    log = h._logtext()[n0:]
    n = log.count("pc = $d616 :trace")
    print(json.dumps(dict(variant=variant, mhz=mhz, vbls=400, timerb=n, per_pass=round(n / (400 / (6.0 if mhz == 8 else 3.0)), 1))))
finally:
    h.close()
