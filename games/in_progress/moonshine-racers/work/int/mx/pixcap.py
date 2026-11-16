"""Capture the DRAWN main-frame buffer of N consecutive passes (at $7b74 = the pacer call, before the flip) of A/T/X.
python3 pixcap.py VARIANT SNAP MHZ N OUTDIR [skipVBL]   -> OUTDIR/p000.bin ... + meta.json (pass counter, $1008)
Extras never reach $7b74 (they flip inside the blob), so every capture is a main frame."""
import sys, re, json
from mxlib import *
variant, snap, mhz, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), Path(sys.argv[5]).resolve()
skip = int(sys.argv[6]) if len(sys.argv) > 6 else 40
hz60 = "hz60" in sys.argv[7:]
pokes = parse_pokes(sys.argv[7:])
out.mkdir(parents=True, exist_ok=True)
h = open_snap(snap, mhz, next((a for a in sys.argv[1:] if a in MACHINES), None))
try:
    nm = variant_names(variant)
    cmds = []
    if nm:
        o = live_build(nm, variant); spec = json.loads(o.with_suffix(".json").read_text())
        cmds.append(f"loadbin {o.with_suffix('.img')} ${spec['img_base']:x}")
        for s in spec["sites"]:
            b = bytes.fromhex(s["new"])
            for k in range(0, len(b), 8): cmds.append(f"w ${s['addr'] + k:x} " + " ".join(f"${x:02x}" for x in b[k:k + 8]))
    for a_, b_ in pokes: cmds.append(f"w ${a_:x} " + " ".join(f"${x:02x}" for x in b_))
    if hz60: cmds.append("w $ff820a $fc")
    if "hold" in sys.argv[7:]:
        (h.R / "hold.txt").write_text("w $6105 $01\n"); cmds.append(f"b pc = $7a88 :trace :file {h.R}/hold.txt")
    cmds.append(f"b pc = $7b74 :trace :once :file {h.R}/cf_0.txt")
    (h.R / "apply.txt").write_text("\n".join(cmds) + "\n")
    for i in range(n):
        lines = [f"savebin {out}/p{i:03d}_70000.bin $70000 $7d00", f"savebin {out}/p{i:03d}_78000.bin $78000 $7d00", "m $1008 4", "e VBL", "m $100e 2", "m $b8f38 4"]
        lines.append(f"b pc = $7b86 :trace :once :file {h.R}/ar_{i}.txt")   # re-arming at the same pc would hit at once: arm the tail first
        (h.R / f"cf_{i}.txt").write_text("\n".join(lines) + "\n")
        if i + 1 < n: (h.R / f"ar_{i}.txt").write_text(f"b pc = $7b74 :trace :once :file {h.R}/cf_{i+1}.txt\n")
        else: (h.R / f"ar_{i}.txt").write_text("e VBL\n")
    v0 = h.vbl()
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v0 + skip} && pc = $7a88 :trace :once :file {h.R}/apply.txt")
    t0 = time.time()
    while h._logtext()[n0:].count("Removed CPU breakpoint") < 2 * n + 1:
        if time.time() - t0 > 900: raise TimeoutError(h._logtext()[-500:])
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
        if not mv or 0x1008 not in g: continue
        w = lambda a: (g[a] << 8) | g[a + 1]
        meta.append(dict(vbl=int(mv.group(1)), back=(w(0x1008) << 16) | w(0x100a), pass_=w(0x100e), extra=(w(0xb8f38) << 16) | w(0xb8f3a)))
    json.dump(meta, open(out / "meta.json", "w"))
    print(variant, snap, mhz, "captured", len(meta), "passes", meta[0]["pass_"], "..", meta[-1]["pass_"], "extras", meta[-1]["extra"] - meta[0]["extra"])
finally:
    h.close()
