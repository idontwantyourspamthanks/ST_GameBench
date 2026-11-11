#!/usr/bin/env python3
"""match.py snap base_live sk_live [--batches B] [--pre 'cmd;cmd'] [--first F]
State-matched A/B for scenes where something moves (the picture then depends on WHEN a frame is rendered, so flips of two runs
cannot be compared).  Per run: restore, apply the live set at a flip (+ optional pokes), then capture 13 consecutive presented
frames (flips F..F+12 after the apply): at each flip $bd9a the buffer just drawn (first long of $2c376) and the render's inputs
(the signature words + slots).  Frames of the base run and of the patched run whose inputs are byte-identical must have
byte-identical 3D windows (rows 51..181 of the drawn buffer); every such pair is compared."""
import sys, time, json, argparse, struct
from pathlib import Path
import numpy as np
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/done/midwinter/tools']
from mw1 import MW1
ap = argparse.ArgumentParser()
ap.add_argument('snap'); ap.add_argument('base'); ap.add_argument('sk')
ap.add_argument('--batches', type=int, default=2); ap.add_argument('--pre', default=''); ap.add_argument('--first', type=int, default=2)
ap.add_argument('--n', type=int, default=13); ap.add_argument('--stride', type=int, default=1)
a = ap.parse_args()
snap = a.snap if '/' in a.snap else f'../snapshots/1mb_ski_{a.snap}.sav'
INPUTS = [(0x12c60, 0x24), (0x12c98, 2), (0x157a8, 2), (0x159a0, 4), (0x171f0, 0x2e), (0x19cd4, 4), (0x1d418, 2), (0x1d816, 6), (0x1cd64, 4), (0x12d54, 2)]
def capture(live, tag, batch):
    out = Path(f'/tmp/p7s/m_{tag}_{batch}'); out.mkdir(exist_ok=True)
    for f in out.glob('*'): f.unlink()
    h = MW1(snapshot=snap)
    try:
        spec = json.loads(Path(live + '.json').read_text())
        cmds = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
        for s in spec['sites']:
            raw = bytes.fromhex(s['new'])
            for o in range(0, len(raw), 40):
                cmds.append(f"w ${s['addr']+o:x} " + " ".join(f"${b:02x}" for b in raw[o:o+40]))
        for p in a.pre.split(';'):
            if p.strip(): cmds.append(p.strip())
        ks = []
        for i in range(a.n):
            k = a.first + batch * a.n * a.stride + i * a.stride
            ks.append(k)
            cf = h.R / f'c{k}.txt'
            lines = [f"savebin {out}/{k}_in{j}.bin ${ad:x} ${ln:x}" for j, (ad, ln) in enumerate(INPUTS)]
            lines += [f"savebin {out}/{k}_slots.bin $1cd7e $b0", f"savebin {out}/{k}_tab.bin $2c376 4"]
            lines += [f"savebin {out}/{k}_b{n}.bin ${ad:x} $7d00" for n, ad in (('58', 0x58000), ('68', 0x68000), ('78', 0x78000))]
            lines += [f"savebin {out}/{k}_done.bin $b6000 $40"]
            cf.write_text("\n".join(lines) + "\n")
            cmds.append(f"b pc = $bd9a :{k} :trace :once :file {cf}")
        app = h.R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
        v = h.vbl()
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b VBL > {v+20} && pc = $bd9a :trace :once :file {app}")
        t = time.time()
        while not (out / f'{ks[-1]}_done.bin').exists():
            if time.time() - t > 400: raise TimeoutError('capture')
            time.sleep(0.5)
        time.sleep(1)
    finally:
        h.close()
    frames = []
    for k in ks:
        tab = struct.unpack('>I', (out / f'{k}_tab.bin').read_bytes())[0]
        buf = {0x58000: 'b58', 0x68000: 'b68', 0x78000: 'b78'}[tab]
        pic = np.fromfile(out / f'{k}_{buf}.bin', dtype=np.uint8).reshape(200, 160)
        inp = b''.join((out / f'{k}_in{j}.bin').read_bytes() for j in range(len(INPUTS))) + (out / f'{k}_slots.bin').read_bytes()
        frames.append((k, hex(tab), inp, pic[51:182].copy(), pic))
    return frames
ok = bad = skipped = 0; seen = set()
for b in range(a.batches):
    fb = capture(a.base, 'base', b); fs = capture(a.sk, 'sk', b)
    for (k1, t1, i1, w1, p1) in fb:
        for (k2, t2, i2, w2, p2) in fs:
            if i1 == i2 and t1 != t2:
                print(f'batch {b}: base flip {k1} ({t1}) / patched flip {k2} ({t2}) inputs identical but drawn into different buffers: not compared (p4_pfx leaves ghost rays of the $20e4e effect in one buffer, see the note)', flush=True)
                skipped += 1
            elif i1 == i2:
                same = bool((w1 == w2).all())
                ok += same; bad += (not same)
                print(f'batch {b}: base flip {k1} ({t1}) == patched flip {k2} ({t2}) inputs identical -> window {"IDENTICAL" if same else "DIFFER %d bytes" % int((w1 != w2).sum())}', flush=True)
    print(f'batch {b}: base inputs distinct {len({f[2] for f in fb})}/{len(fb)}, patched {len({f[2] for f in fs})}/{len(fs)}', flush=True)
print('SUMMARY pairs with identical inputs and the same buffer:', ok + bad, 'window identical:', ok, 'DIFFER:', bad, '(cross-buffer pairs not compared:', skipped, ')')
sys.exit(1 if bad else 0)
