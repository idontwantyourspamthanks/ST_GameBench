"""Rate: python3 exp_rate.py VARIANT(A|T|X) SNAP MHZ VBLS [hz60] [POKE addr=hex..]. Atomic captures at two VBL breakpoints."""
import sys, json, re
from mxlib import *
variant, snap, mhz, nvbl = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
hz60 = "hz60" in sys.argv[5:]
pokes = [(int(x.split('=')[0], 16), bytes.fromhex(x.split('=')[1])) for x in sys.argv[5:] if '=' in x]
HZV = 60 if hz60 else 50
CAP = ["e VBL", "m $5ff8 2", "m $100e 2", "m $130c 2", "m $b8f00 12", "m $b8f38 12", "m $b8f80 64", "m $b8fc0 64", "m $b8f44 2", "m $1318 2", "m $b8f54 24", "m $ff820a 2"]
def parse(txt):
    out = {}; g = {}
    for ln in txt.splitlines():
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m: out["vbl"] = int(m.group(1)); continue
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    w = lambda a: (g[a] << 8) | g[a + 1]
    l = lambda a: (w(a) << 16) | w(a + 2)
    out.update(pos=w(0x5ff8), fc=w(0x100e), spd=w(0x130c), nframes=l(0xb8f38) if 0xb8f38 in g else 0, ngroups=l(0xb8f3c), nticks=l(0xb8f40), rsn=[w(0xb8f54 + 2 * i) for i in range(9)])
    return out
h = open_snap(snap, mhz)
try:
    nm = variant_names(variant)
    if nm or pokes: apply_names(h, nm, variant, pokes=pokes)
    if hz60: h.debug("w $ff820a $fc")
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
    parts = h._logtext()[n0:].split("Reading debugger commands")
    A = parse(parts[1]); B = parse(parts[2])
    dv = B["vbl"] - A["vbl"]
    d = lambda k: (B[k] - A[k]) & 0xFFFF
    passes = d("fc"); extra = (B["nframes"] - A["nframes"]) & 0xFFFFFFFF if variant == "X" else 0
    print(json.dumps(dict(variant=variant, snap=snap, mhz=mhz, hz60=hz60, vbls=dv, passes=passes, extra_frames=extra,
          pass_per_s=round(passes * HZV / dv, 3), fps=round((passes + extra) * HZV / dv, 3), pos_per_s=round(d("pos") * HZV / dv, 2),
          rsn=[(B['rsn'][i] - A['rsn'][i]) & 0xffff for i in range(9)])), flush=True)
finally:
    h.close()
