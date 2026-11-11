#!/usr/bin/env python3
"""verify.py snap live_prefix K [--pre 'cmd;cmd'] [--maxwait S]
Self-check of the skip decision: restore the snapshot, apply the live set at a flip (+ optional pokes), then K times:
arm a breakpoint at the hook's `.skip` label; when the hook decides to skip, save the three screen buffers (A), force the
render instead (r pc = .render), and at the frame's $14e72 save the buffers again (B).  A skipped frame is correct iff A == B
(all 32000 B of all three buffers).  Prints one line per check and a summary."""
import sys, time, json, argparse, struct
from pathlib import Path
import numpy as np
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/done/midwinter/tools']
from mw1 import MW1
ap = argparse.ArgumentParser()
ap.add_argument('snap'); ap.add_argument('live'); ap.add_argument('K', type=int)
ap.add_argument('--pre', default=''); ap.add_argument('--at', default='')
ap.add_argument('--maxwait', type=float, default=90)
ap.add_argument('--shots', default='')
ap.add_argument('--settle', type=int, default=30, help='VBL between applying the set and the first check')
a = ap.parse_args()
snap = a.snap if '/' in a.snap else f'../snapshots/1mb_ski_{a.snap}.sav'
img = Path(a.live + '.img').read_bytes()
spec = json.loads(Path(a.live + '.json').read_text())
base = spec['img_base']
pat = bytes.fromhex('52ae0010' '4cdf7fff' '588f')              # .skip: addq.l #1,16(a6); movem.l (a7)+,d0-d7/a0-a6; addq.l #4,a7
pos = img.find(pat); assert pos >= 0 and img.find(pat, pos + 1) < 0
SKIP = base + pos
# .render: movem.l (a7)+,d0-d7/a0-a6 ; move.l (a7)+,D+12.l  = 4cdf7fff 23df 000b600c
pat2 = bytes.fromhex('4cdf7fff23df000b600c')
p2 = img.find(pat2); assert p2 >= 0 and img.find(pat2, p2 + 1) < 0
RENDER = base + p2
V = Path('/tmp/p7s/v'); V.mkdir(exist_ok=True)
for f in V.glob('*'): f.unlink()
h = MW1(snapshot=snap)
def counters():
    b = h.peek(0xb6000, 64)
    w = lambda o: struct.unpack('>H', b[o:o+2])[0]
    l = lambda o: struct.unpack('>I', b[o:o+4])[0]
    return dict(GEN=w(4), NSKIP=l(16), NREND=l(20), NCHG=l(24), NMK=l(28), NFORCE=l(32), NINV=l(36), NUNS=l(40))
try:
    cmds = [f"loadbin {Path(a.live + '.img').resolve()} ${base:x}"]
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
    time.sleep(2)
    while h.vbl() < v + 20 + a.settle: time.sleep(0.5)
    chk = V / 'chk.txt'
    chk.write_text("".join(f"savebin {V}/b{n}.bin ${ad:x} $7d00\n" for n, ad in (('58', 0x58000), ('68', 0x68000), ('78', 0x78000)))
                   + f"savebin {V}/done.bin $b6000 $60\nsavebin {V}/buf.bin $12d0a 4\n")
    skp = V / 'skip.txt'
    skp.write_text("".join(f"savebin {V}/a{n}.bin ${ad:x} $7d00\n" for n, ad in (('58', 0x58000), ('68', 0x68000), ('78', 0x78000)))
                   + f"b pc = $14e72 :once :trace :file {chk}\nr pc=${RENDER:x}\n")
    ok = bad = 0; t0 = time.time(); sk0 = None
    for k in range(a.K):
        for f in V.glob('*.bin'): f.unlink()
        h.cmd(f"hatari-debug b pc = ${SKIP:x} :once :trace :file {skp}")
        t = time.time()
        while not (V / 'done.bin').exists():
            if time.time() - t > a.maxwait:
                print('no skip decision within', a.maxwait, 's (check', k, ')'); break
            time.sleep(0.2)
        else:
            time.sleep(0.4)
            d = {n: int((np.fromfile(V / f'a{n}.bin', dtype=np.uint8) != np.fromfile(V / f'b{n}.bin', dtype=np.uint8)).sum()) for n in ('58', '68', '78')}
            bufp = struct.unpack('>I', (V / 'buf.bin').read_bytes())[0]
            c = {'GEN': struct.unpack('>H', (V / 'done.bin').read_bytes()[4:6])[0], 'NSKIP': struct.unpack('>I', (V / 'done.bin').read_bytes()[16:20])[0],
                 'NREND': struct.unpack('>I', (V / 'done.bin').read_bytes()[20:24])[0]}
            same = not any(d.values())
            ok += same; bad += not same
            if not same or k % 20 == 0:
                print(f'check {k}: buffer ${bufp:x} A vs B differing bytes {d} {"OK" if same else "MISMATCH"}  {c}', flush=True)
            if not same and a.shots:
                for n in ('58', '68', '78'):
                    np.savez(f'{a.shots}_{k}_{n}.npz', a=np.fromfile(V / f'a{n}.bin', dtype=np.uint8), b=np.fromfile(V / f'b{n}.bin', dtype=np.uint8))
            continue
        break
    print('SUMMARY checked', ok + bad, 'identical', ok, 'MISMATCH', bad, 'counters', counters())
finally:
    h.close()
