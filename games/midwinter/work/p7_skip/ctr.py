"""ctr.py snap live_prefix vbls [--poke 'cmd;cmd' at flip]: restore snapshot, apply the live set at a flip (after VBL+50), run `vbls` VBL, print p7_skip counters.
Also prints slot-1 position per 100 VBL if --slot."""
import sys, time, json, argparse, struct
from pathlib import Path
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/midwinter/tools']
from mw1 import MW1
ap = argparse.ArgumentParser()
ap.add_argument('snap'); ap.add_argument('live'); ap.add_argument('vbls', type=int)
ap.add_argument('--pre', default='')
ap.add_argument('--shot', default='')
a = ap.parse_args()
snap = a.snap if '/' in a.snap else f'../snapshots/1mb_ski_{a.snap}.sav'
h = MW1(snapshot=snap)
def counters():
    b = h.peek(0xb6000, 64)
    w = lambda o: struct.unpack('>H', b[o:o+2])[0]
    l = lambda o: struct.unpack('>I', b[o:o+4])[0]
    return dict(GEN=w(4), GENB=(w(6), w(8), w(10)), NSKIP=l(16), NREND=l(20), NCHG=l(24), NMK=l(28), NFORCE=l(32), NINV=l(36), NUNS=l(40))
try:
    spec = json.loads(Path(a.live + '.json').read_text())
    cmds = [f"loadbin {Path(a.live + '.img').resolve()} ${spec['img_base']:x}"]
    for s in spec['sites']:
        raw = bytes.fromhex(s['new'])
        for o in range(0, len(raw), 40):
            cmds.append(f"w ${s['addr']+o:x} " + " ".join(f"${b:02x}" for b in raw[o:o+40]))
    for p in a.pre.split(';'):
        if p.strip(): cmds.append(p.strip())
    app = h.R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
    v = h.vbl()
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b VBL > {v+20} && pc = $bd9a :trace :once :file {app}")
    time.sleep(3)
    while h.vbl() < v + 30: time.sleep(0.5)
    c0 = counters(); v0 = h.vbl()
    f0 = h.fps(a.vbls)
    c1 = counters()
    print('flips', f0['flips'], 'in', a.vbls, 'VBL')
    print('before', c0)
    print('after ', c1)
    print('delta', {k: (c1[k] - c0[k]) for k in ('NSKIP', 'NREND', 'NCHG', 'NMK', 'NFORCE', 'NINV', 'NUNS')})
    if a.shot:
        import shutil
        shutil.copy(h.shot(), a.shot)
finally:
    h.close()
