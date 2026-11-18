"""python3 cmpstate.py A.json B.json [--mask]  : per-pass state, common passes by $100e; mask = display scratch (documented)"""
import json, sys
def load(p):
    d = json.load(open(p)); out = {}
    for h in d:
        mem = {int(k, 16): v for k, v in h["mem"].items()}
        if 0x100e not in mem or 0x100f not in mem: continue
        out[(mem[0x100e] << 8) | mem[0x100f]] = (h["vbl"], mem)
    return out
MASK = [("mouse variables $6106-$6117 (ta_nomouse only)", 0x6106, 0x6118), ("buffer parity/pointer $1004-$100d", 0x1004, 0x100e), ("raster scratch $12f0-$1307", 0x12f0, 0x1308), ("raster bands $12fe-$1301", 0x12fe, 0x1302),
        ("object order list scratch $36e8-$36ff", 0x36e8, 0x3700), ("road geometry output $4724-$4f77 (rewritten before use)", 0x4724, 0x4f78),
        # --- new HUD: HUD-private variables the removed routines used to update (display only, nothing else reads them) ---
        ("HUD kernel scratch $100c", 0x100c, 0x100e),
        ("thermometer cache/flag $10bc-$10bd $11c9", 0x10bc, 0x10be), ("thermometer flag $11c9", 0x11c9, 0x11ca),
        ("puff erase pointers $10c2-$10c9", 0x10c2, 0x10ca), ("position cache $10cc-$10cd", 0x10cc, 0x10ce), ("position flag $11cc", 0x11cc, 0x11cd),
        ("dial cache $10d4-$10d7", 0x10d4, 0x10d8), ("dial flag $11cd", 0x11cd, 0x11ce), ("minimap variables $10dc-$10e3", 0x10dc, 0x10e4),
        ("score cache/flag $11c4-$11c5 $11c7", 0x11c4, 0x11c6), ("score flag $11c7", 0x11c7, 0x11c8), ("puff animation $11ca-$11cb", 0x11ca, 0x11cc),
        ("gear lever animation $11da-$11dc", 0x11da, 0x11dd),
        ("cloud slots $29c8-$2c67 (dd50 removed)", 0x29c8, 0x2c68), ("cloud counters $27de-$27ed (dd50 removed)", 0x27de, 0x27ee)]
a, b = load(sys.argv[1]), load(sys.argv[2])
usemask = "--mask" in sys.argv
common = sorted(set(a) & set(b))
tot = 0; where = {}; maskedn = 0; mcat = {}
for k in common:
    ma, mb = a[k][1], b[k][1]
    for ad in ma:
        if ad >= 0xb8000 or ad not in mb: continue
        tot += 1
        if ma[ad] != mb[ad]:
            mk = [nm for nm, lo, hi in MASK if lo <= ad < hi] if usemask else []
            if mk: maskedn += 1; mcat[mk[0]] = mcat.get(mk[0], 0) + 1; continue
            where.setdefault(ad, []).append((k, ma[ad], mb[ad]))
print(f"{sys.argv[1]} ({len(a)} passes) vs {sys.argv[2]} ({len(b)}): common {len(common)} (keys {common[0] if common else None}..{common[-1] if common else None}); {tot} bytes compared; mask={'on' if usemask else 'off'} (masked differing bytes {maskedn}); differing addresses {len(where)}, differing bytes {sum(len(v) for v in where.values())}")
for ad in sorted(where)[:30]:
    k, x, y = where[ad][0]; print(f"   ${ad:05x}: {len(where[ad])} passes, e.g. pass {k}: {x:02x} -> {y:02x}")

for nm, c in sorted(mcat.items()): print(f"   masked: {c} differing bytes in {nm}")
