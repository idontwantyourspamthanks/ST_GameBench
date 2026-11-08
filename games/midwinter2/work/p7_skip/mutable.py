import sys, glob, numpy as np
sys.path.insert(0,'.')
import rdset
traces = sys.argv[1:]
U = {}
for t in traces:
    n, sk, firstR, written, unk = rdset.analyze(t)
    print(t, 'instr', n, 'rbw', len(firstR), file=sys.stderr)
    for b, pc in firstR.items(): U.setdefault(b, pc)
dumps = {}
for f in glob.glob('/tmp/d_*/ram_*.bin'):
    sc = f.split('/')[2]
    dumps.setdefault(sc, []).append(np.fromfile(f, dtype=np.uint8))
mut = {}
for sc, lst in dumps.items():
    for i in range(len(lst)):
        for j in range(i+1, len(lst)):
            d = np.nonzero(lst[i] != lst[j])[0]
            for x in d:
                mut.setdefault(int(x), set()).add(sc)
res = sorted(b for b in U if b in mut and not (0x60000 <= b < 0x80000) and not (0x7d80 <= b < 0x8100) and not (0x7000 <= b < 0x7000))
print('read-before-write bytes (union):', len(U), ' mutable among them:', len(res))
iv = []
for b in res:
    if iv and b - iv[-1][1] <= 2: iv[-1][1] = b
    else: iv.append([b, b])
for s, e in iv:
    scs = set()
    pcs = {}
    for b in range(s, e+1):
        if b in mut: scs |= mut[b]
        if b in U: pcs[U[b]] = pcs.get(U[b], 0) + 1
    print(f'{s:06x}-{e:06x} {e-s+1:4d} {sorted(scs)} pcs={[hex(p) for p in list(pcs)[:3]]}')
