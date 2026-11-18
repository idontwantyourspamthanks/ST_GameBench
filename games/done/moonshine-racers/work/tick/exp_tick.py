"""Rate measurement of a snapshot with/without the tick prototype; atomic captures at two VBL breakpoints.
python3 exp_tick.py VARIANT SNAP MHZ VBLS [TICK_UNITS] [hz60]"""
import sys, json, re; sys.path.insert(0, '../timing'); sys.path.insert(0, '.')
from tlib import *
from live import *
from mtlive import apply_mt
variant, snap, mhz, nvbl = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
tick = int(sys.argv[5]) if len(sys.argv) > 5 else 36
hz60 = len(sys.argv) > 6 and sys.argv[6] == "hz60"
HZV = 60 if hz60 else 50
CAP = ["e VBL", "m $5ff8 2", "m $100e 2", "m $130c 2", "m $11c2 2", "m $10ce 4", "m $1024 2", "m $ff820a 2", "m $b8f00 8"]
def j4(a): return b"\x4e\xb9" + a.to_bytes(4, "big")
def build():
    blob, sy = assemble(0xb8000, open("tick.s").read(), f"TICK equ {tick}\nMAXLAG equ {2*tick}", syms=True)
    sites = [(0xd128, j4(sy["vblclk"])), (0x7b74, j4(sy["newsync"])), (0x7b0a, j4(sy["pre17c42"])), (0x7b7a, bytes.fromhex("4e71") * 6)]
    return [(0xb8000, blob)], sites
def parse(txt):
    out = {}; seq = []
    for ln in txt.splitlines():
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m: out["vbl"] = int(m.group(1)); continue
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m: seq.append((int(m.group(1), 16), bytes.fromhex(m.group(2).replace(" ", "")[:32])))
    g = dict(seq)
    out.update(pos=int.from_bytes(g[0x5ff8][:2], "big"), fc=int.from_bytes(g[0x100e][:2], "big"), spd=int.from_bytes(g[0x130c][:2], "big"),
              d11c2=int.from_bytes(g[0x11c2][:2], "big"), sw=int.from_bytes(g[0x10ce][:4], "big") >> 16, m1024=g[0x1024][0], sync=g[0xff820a][0])
    return out
h = open_snap(snap, mhz)
try:
    if variant == "T":
        apply_mt(h)
    if hz60:
        h.debug("w $ff820a $fc")
    time.sleep(1)
    v = h.vbl()
    fa = h.R / "capA.txt"; fb = h.R / "capB.txt"
    fa.write_text("\n".join(CAP) + "\n"); fb.write_text("\n".join(CAP) + "\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v + 80} :trace :once :file {fa}")
    h.cmd(f"hatari-debug b VBL > {v + 80 + nvbl} :trace :once :file {fb}")
    t0 = time.time()
    while h._logtext()[n0:].count("Removed CPU breakpoint") < 2:
        if time.time() - t0 > 600: raise TimeoutError
        time.sleep(0.5)
    time.sleep(0.5)
    log = h._logtext()[n0:]
    parts = log.split("Reading debugger commands")
    A = parse(parts[1]); B = parse(parts[2])
    dv = B["vbl"] - A["vbl"]
    d = lambda k: (B[k] - A[k]) & 0xFFFF
    r = dict(variant=variant, snap=snap, mhz=mhz, tick=tick, hz60=hz60, vbls=dv, dpos=d("pos"), dfc=d("fc"), dsw=d("sw"), dscore=d("d11c2"),
             pos_per_s=round(d("pos") * HZV / dv, 2), pass_per_s=round(d("fc") * HZV / dv, 3), vbl_per_pass=round(dv / max(d("fc"), 1), 3),
             sw_per_s=round(d("sw") * HZV / dv, 3), A=A, B=B)
    print(json.dumps(r), flush=True)
finally:
    h.close()
