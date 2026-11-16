import sys, re; sys.path.insert(0,'.')
from tlib import *
from live import *
from tickpatch import sync_only
variant, mhz = sys.argv[1], int(sys.argv[2])
blobs, sites, sy = (sync_only("sync3.s") if variant == "F" else sync_only("sync2.s") if variant == "E" else ([], [], {}))
h = open_snap("ste1m_race_start.sav", mhz)
try:
    if sites: apply_live(h, blobs, sites)
    time.sleep(1)
    pcs=[0x7a88, 0x17c42, 0x7b74, 0xd1ca, 0x7b7a, 0x7b86]
    log = chain(h, pcs, ["e VBL", "e FrameCycles", "m $ff820a 1"], 6, tag=f"x{variant}{mhz}")
finally:
    h.close()
ev = parse_chain(log, 3)
for pc, v in ev[-12:]:
    e = [x[1] for x in v if x[0] == "e"]
    print(f"{pc:05x} vbl={e[0]:6d} fc={e[1]:6d}")
