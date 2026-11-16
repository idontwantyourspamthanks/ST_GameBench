import json, sys
def load(p):
    d = json.load(open(p)); out = {}
    for h in d:
        mem = {int(k, 16): v for k, v in h["mem"].items()}
        if 0x100e not in mem or 0x100f not in mem: continue
        out[(mem[0x100e] << 8) | mem[0x100f]] = (h["vbl"], mem)
    return out
# display scratch / buffer parity / raster bands / HUD scratch: not game state (see work/notes/extrap.md section on masks)
MASK = [(0x1004, 0x100e), (0x12f0, 0x1308), (0x12fe, 0x1302), (0x3732, 0x3750), (0x37c0, 0x37cc)]
def masked(a): return a >= 0xb8000 or any(lo <= a < hi for lo, hi in MASK)
A, B = load(sys.argv[1]), load(sys.argv[2])
common = sorted(set(A) & set(B))
print(f"{sys.argv[1]}: {len(A)} passes; {sys.argv[2]}: {len(B)} passes; common {len(common)} (keys {common[0] if common else None}..{common[-1] if common else None})")
n = 0; where = {}
for k in common:
    ma, mb = A[k][1], B[k][1]
    for ad in ma:
        if ad in mb and ma[ad] != mb[ad] and not masked(ad):
            n += 1; where.setdefault(ad, []).append((k, ma[ad], mb[ad]))
print(f"differing addresses (outside the mask): {len(where)}; differing bytes total {n}")
for ad in sorted(where)[:40]:
    k, x, y = where[ad][0]; print(f"  ${ad:04x}: {len(where[ad])} passes differ, e.g. pass {k}: {x:02x} -> {y:02x}")
