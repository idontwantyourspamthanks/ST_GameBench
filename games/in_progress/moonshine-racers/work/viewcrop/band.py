"""Cycles per screen-row band for the main pass of the default set (Musashi, plain 68000 cycles = Hatari stage numbers minus interrupts).
python3 band.py DUMP KIND PASSES... : Unicorn warms to each pass (live image X, X_TEST=0), snapshots RAM at $7a88, Musashi runs $7a88->$7b74 with row attribution."""
import sys, json, pickle, struct
import numpy as np
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/work/extrap'); sys.path.insert(0, GAME + '/work/viewcrop')
from gate3 import *
import mlib
dump, kind = sys.argv[1], sys.argv[2]; targets = [int(x) for x in sys.argv[3:]]
out = sys.argv[0].replace('band.py', 'res/band_%s_%s.pkl' % (dump.split('/')[-1][:-4], kind))
LIVE = GAME + '/work/viewcrop/live/X'
e = Emu(dump)
spec = json.load(open(LIVE + '.json')); e.write(spec['img_base'], open(LIVE + '.img', 'rb').read())
for s in spec['sites']: e.write(s['addr'], bytes.fromhex(s['new']))
e.setb(0xB8F21, 0)
sites = []
x = 0x7a8c
while x < 0x7b52: sites.append((x, e.l(x + 2))); x += 6
sites += [(0x7b52, 0x18888), (0x7b5e, 0x18c86), (0x7b64, 0x18f0e)]
res = []
for p in range(max(targets) + 1):
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    if p in targets:
        e.setb(0xB8F08, 0); ram = e.read(0, 0x100000)
        buf = e.l(0x1008); oth = 0x78000 if buf == 0x70000 else 0x70000
        cyc, pcs, cy, rows = mlib.run(ram, 0x7a88, 0x7b74, scr=(buf, oth))
        # stage index per instruction: the pass table jsr/jmp at site addresses; instructions before the first site belong to 'head'
        st = np.full(len(pcs), -1)
        cur = -1
        site_pc = {s: i for i, (s, t) in enumerate(sites)}
        for i, pc in enumerate(pcs):
            j = site_pc.get(int(pc))
            if j is not None: cur = j
            st[i] = cur
        res.append(dict(p=p, cyc=cyc, pcs=pcs, cy=cy, rows=rows, st=st, sites=sites, speech=e.b(0x11ab)))
        print('pass', p, 'cycles', cyc, 'instrs', len(pcs), file=sys.stderr)
    e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
    e.run(0x7a88, 0x7b7a); e.run(0x7b7a, 0x7a88)
pickle.dump(res, open(out, 'wb'))
