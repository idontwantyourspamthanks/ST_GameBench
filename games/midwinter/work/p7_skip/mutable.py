"""mutable.py: bytes the render reads (union of the traces) that differ between the four ski snapshot dumps (dumps.py) = state, not constant."""
import sys, json, numpy as np
sys.path.insert(0, '.')
import chan, rdset
traces = sys.argv[1:] or ['/tmp/p7s/t_stand.txt', '/tmp/p7s/t_walk.txt', '/tmp/p7s/t_turn.txt', '/tmp/p7s/t_busy.txt']
R, W, carried, n, nr = chan.run(traces)
ds = {k: np.fromfile(f'/tmp/p7s/d_{k}.bin', dtype=np.uint8) for k in ('stand', 'walk', 'turn', 'busy')}
mut = set(); names = list(ds)
for i in range(4):
    for j in range(i + 1, 4):
        mut.update(int(x) for x in np.nonzero(ds[names[i]] != ds[names[j]])[0])
res = sorted(b for b in R if b in mut and not chan.is_screen(b))
print('render read-before-write bytes', len(R), ' mutable among the 4 snapshots', len(res))
for s, e in rdset.intervals(res):
    print(f'{s:06x}-{e:06x} {e-s+1:5d} nrW {sum(1 for b in range(s,e+1) if b in W):3d} readers {sorted({hex(R[b]) for b in range(s,e+1) if b in R})[:3]}')
