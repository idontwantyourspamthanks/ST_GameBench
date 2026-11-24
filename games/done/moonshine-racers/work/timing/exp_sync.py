"""Pacing variants, measured atomically over N VBL: A stock, B no post-flip wait, C post-flip wait moved before $17c42."""
import sys, json, re; sys.path.insert(0, '.')
from tlib import *
from live import *
variant, snap, mhz, nvbl = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
CAP = ["e VBL", "m $5ff8 2", "m $100e 2", "m $10ce 4", "m $1024 2"]
def j4(a): return b"\x4e\xb9" + a.to_bytes(4, "big")
blobs, sites = [], []
if variant == "B":
    sites = [(0xd1f2, bytes.fromhex("4e714e71"))]
elif variant == "D":
    from tickpatch import sync_only
    blobs, sites, sy = sync_only()
elif variant == "E":
    from tickpatch import sync_only
    blobs, sites, sy = sync_only("sync2.s")
elif variant == "C":
    blob, sy = assemble(0xb8000, """
sync:   jsr     $d1ca.l
        move.b  $611b.w,$b8100.l
        rts
wait:   move.w  d0,-(a7)
.w:     move.b  $b8100.l,d0
        cmp.b   $611b.w,d0
        beq.s   .w
        clr.b   $611a.l
        move.w  (a7)+,d0
        jmp     $17c42.l
""", syms=True)
    blobs = [(0xb8000, blob)]
    sites = [(0xd1e4, j4(sy["sync"])), (0x7b0a, j4(sy["wait"]))]
h = open_snap(snap, mhz)
try:
    if sites: apply_live(h, blobs, sites)
    time.sleep(1)
    v = h.vbl()
    fa = h.R / "a.txt"; fb = h.R / "b.txt"
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
finally:
    h.close()
def parse(txt):
    out = {}; g = {}
    for ln in txt.splitlines():
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m: out["vbl"] = int(m.group(1))
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m: g[int(m.group(1), 16)] = bytes.fromhex(m.group(2).replace(" ", "")[:8])
    out.update(pos=int.from_bytes(g[0x5ff8][:2], "big"), fc=int.from_bytes(g[0x100e][:2], "big"),
               sw=int.from_bytes(g[0x10ce][:4], "big") >> 16)
    return out
p = log.split("Reading debugger commands"); A = parse(p[1]); B = parse(p[2]); dv = B["vbl"] - A["vbl"]
print(json.dumps(dict(variant=variant, snap=snap, mhz=mhz, vbls=dv, dfc=(B["fc"] - A["fc"]) & 0xFFFF,
                      dpos=(B["pos"] - A["pos"]) & 0xFFFF, swps=round(((B["sw"] - A["sw"]) & 0xFFFF) * 50 / dv, 3),
                      vbl_per_pass=round(dv / max((B["fc"] - A["fc"]) & 0xFFFF, 1), 3))), flush=True)
