import sys, json, time, re; sys.path.insert(0,'.')
from tlib import *
from live import *
from tickpatch import sync_only
blobs, sites, sy = sync_only("sync2.s")
h = open_snap("ste1m_race_start.sav", 8)
try:
    apply_live(h, blobs, sites)
    time.sleep(1)
    for a in (0xd1e4, 0xd1ec, 0xd1ee, 0xd1ca, 0x7b74, 0x7b86):
        h.cmd(f"hatari-debug b pc = ${a:x} :trace")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {h.vbl() + 40} :trace :once")
    t0 = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[n0:]:
        if time.time() - t0 > 300: break
        time.sleep(0.5)
    time.sleep(0.3)
    log = h._logtext()[n0:]
    h.debug("b all", 0.5)
finally:
    h.close()
seq = re.findall(r"pc = \$([0-9a-f]+) :trace", log)
print(" ".join(seq[:80]))
print("total", len(seq))
