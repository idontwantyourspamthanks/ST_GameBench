"""Capture N consecutive flips (both screen buffers, $1008, VBL, flip log) of a patched/stock snapshot run.
python3 capflips.py VARIANT SNAP MHZ NFLIPS OUTDIR [skip=VBL after apply]"""
import sys, re, json; sys.path.insert(0, '../timing'); sys.path.insert(0, '../tick'); sys.path.insert(0, '.')
from tlib import *
from live import *
from mxlive import apply_mx
variant, snap, mhz, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), Path(sys.argv[5]).resolve()
skip = int(sys.argv[6]) if len(sys.argv) > 6 else 40
out.mkdir(parents=True, exist_ok=True)
h = open_snap(snap, mhz)
try:
    if variant == "X": apply_mx(h)
    elif variant == "T":
        from mtlive import apply_mt; apply_mt(h)
    time.sleep(1)
    v0 = h.vbl()
    for i in range(n):
        lines = [f"savebin {out}/f{i:03d}_70000.bin $70000 $7d00", f"savebin {out}/f{i:03d}_78000.bin $78000 $7d00", "m $1008 4", "e VBL", "m $100e 2", "m $130c 2", "m $b8f38 4", "m $b8f00 4"]
        if i + 1 < n: lines.append(f"b pc = $d1ca :trace :once :file {h.R}/cf_{i+1}.txt")
        (h.R / f"cf_{i}.txt").write_text("\n".join(lines) + "\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v0 + skip} && pc = $d1ca :trace :once :file {h.R}/cf_0.txt")
    t0 = time.time()
    while h._logtext()[n0:].count("Removed CPU breakpoint") < n:
        if time.time() - t0 > 600: raise TimeoutError(h._logtext()[-500:])
        time.sleep(0.5)
    time.sleep(1.0)
    log = h._logtext()[n0:]
    meta = []
    for part in log.split("Reading debugger commands")[1:]:
        g = {}
        for ln in part.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
            if m:
                a = int(m.group(1), 16)
                for k, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + k] = x
        mv = re.search(r"#(\d+) \(dec\)", part)
        w = lambda a: (g[a] << 8) | g[a + 1]
        meta.append(dict(vbl=int(mv.group(1)), back=(w(0x1008) << 16) | w(0x100a), pass_=w(0x100e), spd=w(0x130c), extra=(w(0xb8f38) << 16) | w(0xb8f3a), clk=(w(0xb8f00) << 16) | w(0xb8f02)))
    json.dump(meta, open(out / "meta.json", "w"))
    print(json.dumps(meta[:12]))
finally:
    h.close()
