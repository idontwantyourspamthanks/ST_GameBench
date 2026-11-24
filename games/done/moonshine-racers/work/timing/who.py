"""Count executions of $d1ca and $7b74 (the race-loop flip call site) over 600 VBL, variant E vs stock."""
import sys, json, re; sys.path.insert(0,'.')
from tlib import *
from live import *
from tickpatch import sync_only
variant, mhz = sys.argv[1], int(sys.argv[2])
blobs, sites, sy = (sync_only("sync2.s") if variant == "E" else ([], [], {}))
h = open_snap("ste1m_race_start.sav", mhz)
try:
    if sites: apply_live(h, blobs, sites)
    time.sleep(1)
    v = h.vbl()
    n0 = len(h._logtext())
    h.cmd("hatari-debug b pc = $d1ca :trace")
    h.cmd("hatari-debug b pc = $7b74 :trace")
    h.cmd("hatari-debug b pc = $d1e4 :trace")
    h.cmd(f"hatari-debug b VBL > {v + 80} :trace :once")
    t0 = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[n0:]:
        if time.time() - t0 > 400: break
        time.sleep(0.5)
    time.sleep(0.3)
    # now measure a 600-VBL window with the same three counters
    n1 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {h.vbl() + 600} :trace :once")
    t0 = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[n1:]:
        if time.time() - t0 > 400: break
        time.sleep(0.5)
    time.sleep(0.3)
    log = h._logtext()[n1:]
    h.debug("b all", 0.5)
finally:
    h.close()
print(json.dumps(dict(variant=variant, mhz=mhz, d1ca=log.count("pc = $d1ca :trace"),
                      call_site=log.count("pc = $7b74 :trace"), d1e4=log.count("pc = $d1e4 :trace"))))
