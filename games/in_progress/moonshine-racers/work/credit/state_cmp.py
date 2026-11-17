"""python3 state_cmp.py A.json B.json : compare per-pass state (6,716 B/pass): the passes are aligned on the frame counter $100e (shift found so that the counter sequences agree) and compared byte for byte."""
import sys, json
def load(p): return json.load(open(p))
def key(mm): return (mm["0x100e"] << 8) | mm["0x100f"]
A, B = load(sys.argv[1]), load(sys.argv[2])
ka, kb = [key(m) for m in A], [key(m) for m in B]
best = None
for s in range(-len(A), len(A)):                      # B[i] <-> A[i+s]
    pairs = [(i + s, i) for i in range(len(B)) if 0 <= i + s < len(A)]
    ok = sum(1 for a, b in pairs if ka[a] == kb[b])
    if pairs and (best is None or ok > best[1]): best = (s, ok, len(pairs))
s, ok, n = best
pairs = [(i + s, i) for i in range(len(B)) if 0 <= i + s < len(A) and ka[i + s] == kb[i]]
bad = {}
for a, b in pairs:
    for addr in A[a]:
        if A[a][addr] != B[b].get(addr): bad.setdefault(addr, []).append(ka[a])
print(f"{sys.argv[1]} vs {sys.argv[2]}: passes A {len(A)} B {len(B)}, aligned shift {s}, common passes {len(pairs)} (counter {ka[pairs[0][0]] if pairs else '-'}..{ka[pairs[-1][0]] if pairs else '-'}), {len(A[0])} B/pass; differing addresses: {len(bad)}")
for addr in sorted(bad, key=lambda x: int(x, 16))[:12]:
    print("  ", addr, "first/last counter", bad[addr][0], bad[addr][-1], "passes", len(bad[addr]))
