"""Consecutive flips (main AND extra) of A/T/X: drawn buffer at each $d1ca entry, then montage. python3 flips.py VARIANT SNAP MHZ N OUTBASE [skipVBL]
Chain: bp $d1ca (capture) -> bp $d1d2 (inside the flip, arms $d1ca again): re-arming at the same pc would hit at once."""
import sys, re, json
from mxlib import *
sys.path.insert(0, str(GAME / "tools"))
from planar import decode
from PIL import Image
variant, snap, mhz, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), Path(sys.argv[5]).resolve()
skip = int(sys.argv[6]) if len(sys.argv) > 6 else 60
out.mkdir(parents=True, exist_ok=True)
h = open_snap(snap, mhz)
try:
    nm = variant_names(variant)
    if nm: apply_names(h, nm, variant)
    time.sleep(1)
    for i in range(n):
        lines = [f"savebin {out}/f{i:03d}_70000.bin $70000 $7d00", f"savebin {out}/f{i:03d}_78000.bin $78000 $7d00", "m $1008 4", "e VBL", "m $100e 2", "m $130c 2", "m $b8f38 4", "m $5ff8 2", "m $b8f44 2", "m $b8f80 64", "m $b8fc0 64",
                 f"b pc = $d1d2 :trace :once :file {h.R}/fa_{i}.txt"]
        (h.R / f"ff_{i}.txt").write_text("\n".join(lines) + "\n")
        (h.R / f"fa_{i}.txt").write_text((f"b pc = $d1ca :trace :once :file {h.R}/ff_{i+1}.txt\n") if i + 1 < n else "e VBL\n")
    v0 = h.vbl(); n0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v0 + skip} && pc = $d1ca :trace :once :file {h.R}/ff_0.txt")
    t0 = time.time()
    while h._logtext()[n0:].count("Removed CPU breakpoint") < 2 * n:
        if time.time() - t0 > 600: raise TimeoutError(h._logtext()[-400:])
        time.sleep(0.5)
    time.sleep(1.0)
    meta = []
    for part in h._logtext()[n0:].split("Reading debugger commands")[1:]:
        g = {}
        for ln in part.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
            if m:
                a = int(m.group(1), 16)
                for k, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + k] = x
        mv = re.search(r"#(\d+) \(dec\)", part)
        if not mv or 0x1008 not in g: continue
        w = lambda a: (g[a] << 8) | g[a + 1]
        meta.append(dict(vbl=int(mv.group(1)), back=(w(0x1008) << 16) | w(0x100a), pass_=w(0x100e), spd=w(0x130c), pos=w(0x5ff8), extra=(w(0xb8f38) << 16) | w(0xb8f3a),
                         fidx=w(0xb8f44), flog=[w(0xb8f80 + 2 * i) for i in range(32)], klog=[w(0xb8fc0 + 2 * i) for i in range(32)]))
    json.dump(meta, open(out / "meta.json", "w"))
    print(variant, mhz, "MHz: flips captured", len(meta), [(m["vbl"], m["pass_"], m["extra"]) for m in meta])
    for i, m in enumerate(meta):
        nmf = "70000" if m["back"] == 0x70000 else "78000"
        decode((out / f"f{i:03d}_{nmf}.bin").read_bytes()).save(out / f"img{i:03d}.png")
finally:
    h.close()
