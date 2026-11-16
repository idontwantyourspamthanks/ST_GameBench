import sys, json, time; sys.path.insert(0,'.')
from tlib import *
from live import *
from tickpatch import sync_only
blobs, sites, sy = sync_only("sync2.s")
h = open_snap("ste1m_race_start.sav", 8)
try:
    apply_live(h, blobs, sites)
    time.sleep(1)
    print(h.debug("m $b8016 40", 0.6))
    pts = {0xd1ca: "flip", 0x7b74: "callsite", 0xd1e4: "d1e4", 0xd1ee: "old bsr flip", 0xd1ec: "old bcs",
           sy["sync"] + 6: "after jsr flip", sy["wait"]: "guard", sy["vbl"]: "vbl"}
    for a in pts: h.cmd(f"hatari-debug b pc = ${a:x} :trace")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {h.vbl() + 300} :trace :once")
    t0 = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[n0:]:
        if time.time() - t0 > 300: break
        time.sleep(0.5)
    time.sleep(0.3)
    log = h._logtext()[n0:]
    h.debug("b all", 0.5)
finally:
    h.close()
print(json.dumps({v: log.count(f"pc = ${a:x} :trace") for a, v in pts.items()}))
