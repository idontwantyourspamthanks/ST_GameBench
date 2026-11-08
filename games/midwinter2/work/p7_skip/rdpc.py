import sys, collections, re
sys.path.insert(0,'.')
import rdset
n, sk, firstR, written, unk = rdset.analyze(sys.argv[1])
# group first-read pcs by coarse interval
iv = rdset.intervals(firstR.keys())
merged=[]
for s,e in iv:
    if merged and s-merged[-1][1] <= 16: merged[-1][1]=e
    else: merged.append([s,e])
for s,e in merged:
    pcs=collections.Counter(firstR[b] for b in range(s,e+1) if b in firstR)
    print(f'{s:06x}-{e:06x} {e-s+1:5d}  pcs:', ' '.join(f'{p:x}x{c}' for p,c in pcs.most_common(4)))
