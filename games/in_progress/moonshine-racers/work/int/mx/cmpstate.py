"""python3 cmpstate.py A.json B.json [--mask]  : per-pass state, common passes by $100e; mask = display scratch (documented)"""
import json, sys
def load(p):
    d = json.load(open(p)); out = {}
    for h in d:
        mem = {int(k, 16): v for k, v in h["mem"].items()}
        if 0x100e not in mem or 0x100f not in mem: continue
        out[(mem[0x100e] << 8) | mem[0x100f]] = (h["vbl"], mem)
    return out
MASK = [("buffer parity/pointer $1004-$100d", 0x1004, 0x100e), ("raster scratch $12f0-$1307", 0x12f0, 0x1308), ("raster bands $12fe-$1301", 0x12fe, 0x1302),
        ("object order list scratch $36e8-$36ff", 0x36e8, 0x3700), ("road geometry output $4724-$4f77 (rewritten before use)", 0x4724, 0x4f78)] + \
       [("cloud $28/$2a display history, 12 entries", 0x29c8 + n * 0x38 + 0x28, 0x29c8 + n * 0x38 + 0x2c) for n in range(12)]
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
