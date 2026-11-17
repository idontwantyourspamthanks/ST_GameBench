"""Per-pass state at $7b86 keyed by $100e. python3 exp_state.py VARIANT(A|T|X) SNAP MHZ NPASS OUT.json [hz60]
Ranges (decimal counts): the msrabtest ranges $1000-$13ff $29c8-$34ff $4500-$4fff $dae6 plus ring/state windows and the blob counters."""
import sys, json, re
sys.path.insert(0,"/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/speechbar")
from sblib import *
variant, snap, mhz, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
hz60 = "hz60" in sys.argv[6:]
pokes = parse_pokes([a for a in sys.argv[6:] if not a.startswith("zig=")])
RANGES = [(0x1000, 1024), (0x29c8, 2872), (0x4500, 2816), (0xdae6, 4), (0x1bb0, 12), (0x23bc, 16), (0x27c8, 38), (0x3500, 512), (0xdafe, 4), (0x6100, 24), (0xb8f38, 12)]
if 'kernbig' in sys.argv[6:]: RANGES = [(0x1000, 1024), (0x12000, 28672), (0xdafe, 4), (0xb8f38, 12)]   # whole kernel/code area $12000-$18fff
elif 'kern' in sys.argv[6:]: RANGES += [(0x12000, 16384), (0xdafe, 4)]   # sprite kernels (self-modified immediates) + the HUD face RNG immediate
h = open_snap(snap, mhz, next((a for a in sys.argv[1:] if a in MACHINES), None))
try:
    nm = variant_names(variant)
    if nm or pokes: apply_names(h, nm, variant, pokes=pokes)
    if hz60: h.debug("w $ff820a $fc")
    time.sleep(1)
    f = h.R / "state.txt"
    f.write_text("e VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in RANGES))
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    if "hold" in sys.argv[6:]:                    # up held at every pass (the restart clears the input byte)
        (h.R / "hold.txt").write_text("w $6105 $01\n"); h.cmd(f"hatari-debug b pc = $7a88 :trace :file {h.R}/hold.txt")
    zk = next((a for a in sys.argv[6:] if a.startswith("zig=")), None)
    if zk:                                        # steering as a pure function of the pass key $100e (identical inputs in stock and patched runs): from key KS, 15 passes up, up+left, up, up+right ...
        KS = int(zk[4:])
        for K in range(KS, KS + 400):
            (h.R / f"z_{K}.txt").write_text(f"w $6105 ${[1, 5, 1, 9][((K - KS) // 15) % 4]:02x}\nb pc = $7a88 && ($100e).w = ${K + 1:x} :trace :once :file {h.R}/z_{K + 1}.txt\n")
        h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = ${KS:x} :trace :once :file {h.R}/z_{KS}.txt")
    h.cmd(f"hatari-debug b pc = $7b86 :trace :file {f}")
    t0 = time.time()
    while h._logtext()[n0:].count("> e VBL") < npass:
        if time.time() - t0 > 1500: break
        time.sleep(1)
    h.debug("b all", 0.5)
    log = h._logtext()[n0:]
finally:
    h.close()
res = []
for ht in log.split("> e VBL")[1:]:
    mem = {}
    m = re.search(r"#(\d+) \(dec\)", ht); vbl = int(m.group(1)) if m else None
    for ln in ht.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): mem[a + i] = x
    res.append((vbl, mem))
json.dump([{"vbl": v, "mem": {hex(k): x for k, x in mm.items()}} for v, mm in res], open(out, "w"))
nf = None
if res and 0xb8f38 in res[0][1]:
    l = lambda mm: int.from_bytes(bytes(mm[0xb8f38 + i] for i in range(4)), "big")
    nf = l(res[-1][1]) - l(res[0][1])
print(variant, snap, mhz, "hits", len(res), "bytes/hit", len(res[0][1]) if res else 0, "extra frames in window", nf)
