"""python3 pixcmp.py DIR_A DIR_B : compare the drawn buffer (by $1008) of the same pass counter"""
import sys, json
from pathlib import Path
def load(d):
    d = Path(d); m = json.load(open(d / "meta.json")); r = {}
    for i, e in enumerate(m):
        name = "70000" if e["back"] == 0x70000 else "78000"
        r[e["pass_"]] = (d / f"p{i:03d}_{name}.bin").read_bytes()[:0x7d00]
    return r
A, B = load(sys.argv[1]), load(sys.argv[2])
common = sorted(set(A) & set(B)); nd = 0; worst = 0
for k in common:
    d = sum(1 for x, y in zip(A[k], B[k]) if x != y)
    if d: nd += 1; worst = max(worst, d); print(f"  pass {k}: {d} bytes differ")
print(f"{sys.argv[1]} vs {sys.argv[2]}: {len(A)} / {len(B)} passes, common {len(common)} main frames compared, differing {nd}, worst {worst} bytes")
