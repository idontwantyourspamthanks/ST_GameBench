"""Same run: count $d1ca hits (trace) and the $100e delta over one 600-VBL window, for a given variant."""
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
    fa = h.R/"a.txt"; fb = h.R/"b.txt"
    for f in (fa, fb): f.write_text("e VBL\nm $100e 2\nm $5ff8 2\nm $1021 2\nm $1024 2\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $d1ca :trace")
    h.cmd(f"hatari-debug b VBL > {v + 80} :trace :once :file {fa}")
    h.cmd(f"hatari-debug b VBL > {v + 680} :trace :once :file {fb}")
    t0 = time.time()
    while h._logtext()[n0:].count("Removed CPU breakpoint") < 2:
        if time.time() - t0 > 600: raise TimeoutError
        time.sleep(0.5)
    time.sleep(0.5)
    log = h._logtext()[n0:]
    h.debug("b all", 0.5)
finally:
    h.close()
import re
hv = re.findall(r"#(\d+) \(dec\)", log)
# the first two captures' VBL and the counter reads, in order
vals = []
for ln in log.splitlines():
    m = re.search(r"#(\d+) \(dec\)", ln)
    if m: vals.append(("vbl", int(m.group(1)))); continue
    m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
    if m: vals.append(("m", int(m.group(1), 16), bytes.fromhex(m.group(2).replace(" ", "")[:4])))
caps = []
cur = None
for x in vals:
    if x[0] == "vbl":
        if cur: caps.append(cur)
        cur = {"vbl": x[1], "m": {}}
    elif cur is not None:
        cur["m"][x[1]] = int.from_bytes(x[2], "big")
if cur: caps.append(cur)
print(json.dumps(dict(variant=variant, mhz=mhz, d1ca_hits=log.count("pc = $d1ca :trace"),
    caps=[{"vbl": c["vbl"], "fc": c["m"].get(0x100e), "pos": c["m"].get(0x5ff8), "mode": c["m"].get(0x1021)} for c in caps])))
