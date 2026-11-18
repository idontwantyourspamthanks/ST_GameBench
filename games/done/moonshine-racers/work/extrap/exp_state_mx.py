"""Per-pass state capture at $7b86 (first instruction of the tail), keyed by $100e. python3 exp_state_mx.py VARIANT(A|X) SNAP MHZ NPASS OUT.json
captures $1000-$1400, $2c68-$3500 (object slots), $4500-$4b88?? no: $1000-$1400, $2c68-$3500, the RNG $dae6, the kernel patch longs are not compared."""
import sys, json, re; sys.path.insert(0, '../timing'); sys.path.insert(0, '../tick'); sys.path.insert(0, '.')
from tlib import *
from live import *
from mxlive import apply_mx
variant, snap, mhz, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
pokes = [(int(x.split('=')[0], 16), bytes.fromhex(x.split('=')[1])) for x in sys.argv[6:] if '=' in x]
RANGES = [(0xb8f38, 12), (0x1000, 0x400), (0x2c68, 0x898), (0xdae6, 4), (0x23bc, 0x10), (0x27c8, 0x26), (0x1bb0, 12), (0x13a2, 16)]
h = open_snap(snap, mhz)
try:
    if variant == "X": apply_mx(h, pokes=pokes)
    time.sleep(1)
    f = h.R / "state.txt"
    f.write_text("e VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in RANGES))
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7b86 :trace :file {f}")
    t0 = time.time()
    while h._logtext()[n0:].count("> e VBL") < npass:
        if time.time() - t0 > 1500: break
        time.sleep(1)
    h.debug("b all", 0.5)
    log = h._logtext()[n0:]
finally:
    h.close()
hits = log.split("> e VBL")[1:]
res = []
for ht in hits:
    mem = {}
    m = re.search(r"#(\d+) \(dec\)", ht); vbl = int(m.group(1)) if m else None
    for ln in ht.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): mem[a + i] = x
    res.append((vbl, mem))
json.dump([{"vbl": v, "mem": {hex(k): x for k, x in mm.items()}} for v, mm in res], open(out, "w"))
print(variant, snap, mhz, "hits", len(res), "mem bytes/hit", len(res[0][1]) if res else 0)
