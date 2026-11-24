"""Compare two per-pass state captures: key passes by $100e, ignore the raster-table copy $12fe-$1305 (copied one VBL later by
the prototype) and report differing bytes per pass key."""
import json, sys
def load(p):
    d = json.load(open(p)); out = {}
    for h in d:
        mem = {int(k, 16): v for k, v in h["mem"].items()}
        key = (mem[0x100e] << 8) | mem[0x100f]
        out[key] = (h["vbl"], mem)
    return out
SKIP = [(0x12fe, 0x1306)]
def diffs(a, b):
    n = 0; where = {}
    for k in sorted(set(a) & set(b)):
        ma, mb = a[k][1], b[k][1]
        for ad in ma:
            if ad in mb and ma[ad] != mb[ad] and not any(lo <= ad < hi for lo, hi in SKIP):
                n += 1; where.setdefault(ad, []).append((k, ma[ad], mb[ad]))
    return n, where
A, B = load(sys.argv[1]), load(sys.argv[2])
ka, kb = sorted(A), sorted(B)
print(f"{sys.argv[1]}: {len(A)} passes, keys {ka[0]}..{ka[-1]}")
print(f"{sys.argv[2]}: {len(B)} passes, keys {kb[0]}..{kb[-1]}")
n, w = diffs(A, B)
print(f"common passes {len(set(A) & set(B))}; differing bytes (excluding $12fe-$1305): {n}")
for ad in sorted(w)[:40]:
    k, x, y = w[ad][0]
    print(f"  ${ad:04x}: {len(w[ad])} passes differ, e.g. pass {k}: {x:02x} -> {y:02x}")
