import sys, time, struct
from pathlib import Path
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1/tools")
import pmww, wwhd
wd = sys.argv[1]
h = wwhd.PMWHD(Path("/tmp/pmww1fhd/dbg/hd1"), workdir=wd, machine="falcon", tos=pmww.TOS["4.04"], memsize_kb=4096, extra=["--borders","false"])
_cs = h.click_st
def snap():
    d = bytes(h.ram(0x72a80, 64)); return h.vbl(), struct.unpack(">L", d[32:36])[0]
def passrate(tag):
    v0, p0 = snap(); time.sleep(5); v1, p1 = snap(); print(f"{tag}: {(v1-v0)/max(1,p1-p0):.2f} VBL/pass", flush=True)
def isopen(): return h.peekw(pmww.WINDOW_OPEN) != 0
def trial(hold, n=4):
    res = []
    for i in range(n):
        if isopen():
            res.append("STUCK-OPEN"); _cs(200, 60, hold=0.8, wait=2.0)
            if isopen(): _cs(200, 60, hold=0.8, wait=2.0)
        _cs(*pmww.OPTION_XY, hold=hold, wait=2.0)
        op = isopen()
        cl = None
        if op:
            _cs(200, 60, hold=0.8, wait=2.0); cl = not isopen()
        res.append("open" if op else "MISS")
    print(f"hold {hold}: {res}", flush=True)
try:
    h.boot_to_options(log=print); time.sleep(2)
    h.options_to_map(noprot=True, swap=False, log=print)
    time.sleep(2); passrate("map (land)")
    for hold in (0.1, 0.2): trial(hold)
    r = h.saveload_hd(log=print); print(r, flush=True)
    time.sleep(3); passrate("after load")
    h.shot(str(Path(wd)/"shots"/"after_load.png"))
    for hold in (0.1, 0.2, 0.3, 0.8): trial(hold)
finally:
    h.close()
