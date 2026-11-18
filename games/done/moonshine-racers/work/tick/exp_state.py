"""Per-pass state capture (stock vs tick prototype). python3 exp_state.py VARIANT SNAP MHZ NPASS OUT.json [TICK]
At every execution of $7b86 (`addq.w #1,$100e.w`, first instruction of the tail after the flip) a debugger file dumps
$1000-$1400, $2c68-$3500 and the RNG long $dae6; hits are keyed by the frame counter $100e."""
import sys, json, re; sys.path.insert(0, '../timing'); sys.path.insert(0, '.')
from tlib import *
from live import *
from mtlive import apply_mt
variant, snap, mhz, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
tick = int(sys.argv[6]) if len(sys.argv) > 6 else 36
RANGES = [(0x1000, 0x400), (0x2c68, 0x898), (0xdae6, 4)]
h = open_snap(snap, mhz)
try:
    if variant == "T":
        apply_mt(h)
    time.sleep(1)
    f = h.R / "state.txt"
    f.write_text("e VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in RANGES))
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7b86 :trace :file {f}")
    t0 = time.time()
    while h._logtext()[n0:].count("> e VBL") < npass:
        if time.time() - t0 > 900: break
        time.sleep(1)
    h.debug("b all", 0.5)
    log = h._logtext()[n0:]
finally:
    h.close()
open(out + ".raw", "w").write(log)
hits = log.split("> e VBL")[1:]
res = []
for ht in hits:
    mem = {}
    vbl = None
    m = re.search(r"#(\d+) \(dec\)", ht)
    if m: vbl = int(m.group(1))
    for ln in ht.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            bs = bytes.fromhex(m.group(2).replace(" ", ""))
            for i, x in enumerate(bs): mem[a + i] = x
    res.append((vbl, mem))
json.dump([{"vbl": v, "mem": {hex(k): x for k, x in mm.items()}} for v, mm in res], open(out, "w"))
print(variant, snap, mhz, "hits", len(res), "mem bytes/hit", len(res[0][1]) if res else 0)
