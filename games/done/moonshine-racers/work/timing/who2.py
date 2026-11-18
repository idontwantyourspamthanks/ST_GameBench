import sys, json; sys.path.insert(0,'.')
from tlib import *
from live import *
from tickpatch import sync_only
blobs, sites, sy = sync_only("sync2.s")
h = open_snap("ste1m_race_start.sav", 8)
try:
    apply_live(h, blobs, sites)
    time.sleep(1)
    # dump the patched bytes as the CPU sees them
    print(h.debug("m $d1e4 12", 0.6))
    print(h.debug("m $7b08 8", 0.6))
    print(h.debug("m $d126 8", 0.6))
    print(h.debug("m $b8000 32", 0.6))
    pcs = {0xd1ca: "$d1ca", 0x7b74: "$7b74", 0xd1e4: "$d1e4", sy["sync"]: "sync", sy["sync"] + 2: "sync+2", 0xd1fe: "$d1fe"}
    for a in pcs: h.cmd(f"hatari-debug b pc = ${a:x} :trace")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {h.vbl() + 300} :trace :once")
    import time
    t0 = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[n0:]:
        if time.time() - t0 > 300: break
        time.sleep(0.5)
    time.sleep(0.3)
    log = h._logtext()[n0:]
    h.debug("b all", 0.5)
finally:
    h.close()
print(json.dumps({v: log.count(f"pc = ${a:x} :trace") for a, v in pcs.items()}))
