#!/usr/bin/env python3
"""Who writes into screen rows 58-199 of the back buffer during one frame of the ORIGINAL game?

    python3 work/cockpit/writers.py <snapshot.sav> <tag>

Captures both buffers at four points of one frame (sky-fill exit $1b9fe, replay entry $30f2c, replay exit
$30f54, flip $26e98) into /tmp/wr/<tag>/ and prints: rows still equal to the pure fill pattern at each point,
the first row the terrain touched, rows changed by the replay, rows changed between replay exit and flip.
"""
import struct, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from mw2harness import Hatari

snap, tag = sys.argv[1], sys.argv[2]
od = Path('/tmp/wr') / tag; od.mkdir(parents=True, exist_ok=True)
h = Hatari(snapshot=snap)
try:
    pts = [('fillexit', 0x1b9fe), ('repentry', 0x30f2c), ('repexit', 0x30f54), ('flip', 0x26e98)]
    files = []
    for i, (n, pc) in enumerate(pts):
        f = h.R / f'w_{n}.txt'
        lines = [f'savebin {od}/{n}_60.bin $60000 $8000', f'savebin {od}/{n}_70.bin $70000 $8000', f'savebin {od}/{n}_ptr.bin $67a6 8']
        if i + 1 < len(pts):
            lines.append(f'b pc = ${pts[i + 1][1]:x} :trace :once :file {h.R}/w_{pts[i + 1][0]}.txt')
        f.write_text('\n'.join(lines) + '\n'); files.append(f)
    at = (h.vbl() // 100 + 3) * 100
    h.cmd(f'hatari-debug b VBL > {at} && pc = ${pts[0][1]:x} :trace :once :file {files[0]}')
    t = time.time()
    while not (od / 'flip_ptr.bin').exists():
        if time.time() - t > 300: raise TimeoutError
        time.sleep(0.5)
    time.sleep(1)
finally:
    h.close()

FILL = bytes.fromhex('7fff7fff7fff7fff' + 'ffffffffffffffff' * 19)
ptr = struct.unpack('>I', (od / 'repentry_ptr.bin').read_bytes()[:4])[0]; b = '60' if ptr >> 16 == 6 else '70'
g = lambda n: (od / f'{n}_{b}.bin').read_bytes()
fe, re_, rx, fl = g('fillexit'), g('repentry'), g('repexit'), g('flip')
row = lambda buf, r: buf[r * 160:(r + 1) * 160]
print(tag, 'back buffer', hex(ptr))
print(' fill exit: rows 58-199 all pure fill:', all(row(fe, r) == FILL for r in range(58, 200)))
print(' replay entry: first row != fill (terrain ymin):', next((r for r in range(58, 200) if row(re_, r) != FILL), None),
      '; rows 182-199 not pure fill:', sum(row(re_, r) != FILL for r in range(182, 200)), 'of 18')
print(' replay changes rows', [r for r in range(200) if row(re_, r) != row(rx, r)][:1], '..', [r for r in range(200) if row(re_, r) != row(rx, r)][-1:])
print(' rows changed between replay exit and flip:', [r for r in range(200) if row(rx, r) != row(fl, r)])
print(' rows 0-57 changed between fill exit and flip:', sum(row(fe, r) != row(fl, r) for r in range(58)))
