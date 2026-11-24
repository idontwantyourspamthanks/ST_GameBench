"""Rate measurement: python3 exp_mx.py VARIANT(A|T|X) SNAP MHZ VBLS [POKE addr=hex ...]
A = stock, T = mt_* (fixed tick), X = mt_clock + mt_pre + mx_sync (fixed tick + extra frames)
Atomic captures (CPU halted) at two VBL breakpoints: $100e passes, $5ff8, flip-count statistics of the blob, flip log."""
import sys, json, re; sys.path.insert(0, '../timing'); sys.path.insert(0, '../tick'); sys.path.insert(0, '.')
from tlib import *
from live import *
from mxlive import apply_mx
variant, snap, mhz, nvbl = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
pokes = [(int(x.split('=')[0], 16), bytes.fromhex(x.split('=')[1])) for x in sys.argv[5:] if '=' in x]
CAP = ["e VBL", "m $5ff8 2", "m $100e 2", "m $130c 2", "m $b8f00 12", "m $b8f38 12", "m $b8f80 64", "m $b8fc0 64", "m $b8f44 2", "m $1318 2", "m $11b0 4", "m $b8f54 24"]
def parse(txt):
    out = {}; seq = []
    for ln in txt.splitlines():
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m: out["vbl"] = int(m.group(1)); continue
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m: seq.append((int(m.group(1), 16), bytes.fromhex(m.group(2).replace(" ", ""))))
    g = {}
    for a, b in seq:
        for i, x in enumerate(b): g[a + i] = x
    w = lambda a: (g[a] << 8) | g[a + 1]
    l = lambda a: (w(a) << 16) | w(a + 2)
    out.update(pos=w(0x5ff8), fc=w(0x100e), spd=w(0x130c), clk=l(0xb8f00), next=l(0xb8f04), pend=g[0xb8f08], nframes=l(0xb8f38), ngroups=l(0xb8f3c), nticks=l(0xb8f40),
               fidx=w(0xb8f44), rsn=[w(0xb8f54+2*i) for i in range(9)], flog=[w(0xb8f80 + 2 * i) for i in range(32)], klog=[w(0xb8fc0 + 2 * i) for i in range(32)], lat=w(0x1318))
    return out
h = open_snap(snap, mhz)
try:
    if variant == "T":
        from mtlive import apply_mt
        apply_mt(h)
    elif variant == "X":
        apply_mx(h, pokes=pokes)
    time.sleep(1)
    v = h.vbl()
    fa = h.R / "capA.txt"; fb = h.R / "capB.txt"
    fa.write_text("\n".join(CAP) + "\n"); fb.write_text("\n".join(CAP) + "\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v + 80} :trace :once :file {fa}")
    h.cmd(f"hatari-debug b VBL > {v + 80 + nvbl} :trace :once :file {fb}")
    t0 = time.time()
    while h._logtext()[n0:].count("Removed CPU breakpoint") < 2:
        if time.time() - t0 > 900: raise TimeoutError
        time.sleep(0.5)
    time.sleep(0.5)
    log = h._logtext()[n0:]
    parts = log.split("Reading debugger commands")
    A = parse(parts[1]); B = parse(parts[2])
    dv = B["vbl"] - A["vbl"]
    d = lambda k: (B[k] - A[k]) & 0xFFFF
    dl = lambda k: (B[k] - A[k]) & 0xFFFFFFFF
    passes = d("fc"); extra = dl("nframes")
    r = dict(variant=variant, snap=snap, mhz=mhz, vbls=dv, passes=passes, extra_frames=extra, groups=dl("ngroups"), ticks=dl("nticks"),
             pass_per_s=round(passes * 50 / dv, 3), fps=round((passes + extra) * 50 / dv, 3), pos_per_s=round(d("pos") * 50 / dv, 2), A=A, B=B)
    r['rsn_delta']=[(B['rsn'][i]-A['rsn'][i])&0xffff for i in range(9)]
    print(json.dumps(r), flush=True)
finally:
    h.close()
