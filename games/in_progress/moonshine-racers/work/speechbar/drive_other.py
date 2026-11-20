"""restart transient: compare the NON-drawn (displayed) buffer of F and S around the race_drive restart: python3 drive_other.py F_DIR S_DIR"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbart import *
F, S = Path(sys.argv[1]), Path(sys.argv[2])
mf, ms = json.load(open(F / 'meta.json')), json.load(open(S / 'meta.json'))
kf = {m['pass_']: i for i, m in enumerate(mf)}; ks = {m['pass_']: i for i, m in enumerate(ms)}
for p in [1704, 1705, 1706, 0, 1, 2, 3, 4]:
    if p not in kf or p not in ks: continue
    a, b = kf[p], ks[p]
    out = []
    for nm, d, i, m in (('F', F, a, mf[a]), ('S', S, b, ms[b])):
        other = '78000' if m['back'] == 0x70000 else '70000'
        I = planar_to_idx((d / f'p{i:03d}_{other}.bin').read_bytes())
        out.append(f"{nm}: other buffer {other} rows16-41 colours {sorted(set(I[16:42].ravel().tolist()))} rows42-64 {sorted(set(I[42:65].ravel().tolist()))}")
    print('pass', p, ' | '.join(out))
