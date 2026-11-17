"""Main-frame capture for the integrated build (mg_sync flips the main frame at $7b52, stock/mt/mx at $7b74, so the old $7b74 hook of work/int/mx/pixcap.py does not apply).
python3 pixcap2.py VARIANT SNAP MHZ N OUTDIR [zig=KEYSTART] [hold] [poke=ADDR=HEX ...] [hz60] [ste4096|megaste60]
VARIANT: A stock, X default (tick+mg), T tick no extras, XM mx pacer, P previous default ... (mxlib_fin.SETS)
Per pass: chain of one-shot breakpoints: pass top $7a88 (records $100e) -> the FIRST flip $d1ca after it (the main frame of that pass in every variant; extras flip later)
-> saves both buffers + $1008 (= the buffer just drawn) and re-arms $7a88.  Steering (zig) as a pure function of the pass key $100e like exp_state_fin.py.
Output: OUTDIR/p000_70000.bin, p000_78000.bin ... + meta.json [{pass_, back, vbl}]"""
import sys, re, json, time
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2")
from mxlib_fin import *
variant, snap, mhz, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), Path(sys.argv[5]).resolve()
opts = sys.argv[6:]
hz60 = "hz60" in opts
pokes = parse_pokes([a[5:] for a in opts if a.startswith("poke=")])
zk = next((a for a in opts if a.startswith("zig=")), None)
AT = int(next((a[3:] for a in opts if a.startswith("at=")), "d1ca"), 16)      # capture point: default the first flip $d1ca after the pass top; at=7b52 = the pass reaches $7b52 (before the post stages)
out.mkdir(parents=True, exist_ok=True)
for f in out.glob("p*_*.bin"): f.unlink()
h = open_snap(snap, mhz, next((a for a in sys.argv[1:] if a in MACHINES), None))
try:
    nm = variant_names(variant)
    if nm or pokes: apply_names(h, nm, variant, pokes=pokes)
    if hz60: h.debug("w $ff820a $fc")
    time.sleep(1)
    h.debug("b all", 0.3)
    if "hold" in opts:
        (h.R / "hold.txt").write_text("w $6105 $01\n"); h.cmd(f"hatari-debug b pc = $7a88 :trace :file {h.R}/hold.txt")
    if zk:
        KS = int(zk[4:])
        for K in range(KS, KS + n + 60):
            (h.R / f"z_{K}.txt").write_text(f"w $6105 ${[1, 5, 1, 9][((K - KS) // 15) % 4]:02x}\nb pc = $7a88 && ($100e).w = ${K + 1:x} :trace :once :file {h.R}/z_{K + 1}.txt\n")
        h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = ${KS:x} :trace :once :file {h.R}/z_{KS}.txt")
    for i in range(n):
        (h.R / f"cf_{i}.txt").write_text(f"e VBL\nm $100e 2\nb pc = ${AT:x} :trace :once :file {h.R}/cg_{i}.txt\n")
        lines = [f"savebin {out}/p{i:03d}_70000.bin $70000 $7d00", f"savebin {out}/p{i:03d}_78000.bin $78000 $7d00", "m $1008 4", "e VBL"]
        if i + 1 < n: lines.append(f"b pc = $7a88 :trace :once :file {h.R}/cf_{i+1}.txt")
        (h.R / f"cg_{i}.txt").write_text("\n".join(lines) + "\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7a88 :trace :once :file {h.R}/cf_0.txt")
    t0 = time.time()
    last = out / f"p{n-1:03d}_78000.bin"
    while not last.exists():
        if time.time() - t0 > 1500: raise TimeoutError(h._logtext()[-500:])
        time.sleep(0.5)
    time.sleep(1.0)
    h.debug("b all", 0.5)
    log = h._logtext()[n0:]
    meta = []; cur = {}
    for part in log.split("Reading debugger commands")[1:]:
        g = {}
        for ln in part.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
            if m:
                a = int(m.group(1), 16)
                for k, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + k] = x
        mv = re.search(r"#(\d+) \(dec\)", part)
        w = lambda a: (g[a] << 8) | g[a + 1]
        if 0x100e in g and 0x1008 not in g:
            cur = dict(pass_=w(0x100e))
        elif 0x1008 in g and cur:
            cur["back"] = (w(0x1008) << 16) | w(0x100a); cur["vbl"] = int(mv.group(1)) if mv else None
            meta.append(cur); cur = {}
    json.dump(meta, open(out / "meta.json", "w"))
    print(variant, snap, mhz, "captured", len(meta), "main frames, passes", meta[0]["pass_"], "..", meta[-1]["pass_"], flush=True)
finally:
    h.close()
