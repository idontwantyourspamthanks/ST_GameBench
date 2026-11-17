import sys, json, collections
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/work/extrap'); sys.path.insert(0, GAME + '/work/viewcrop')
from gate3 import *
import mlib
e = Emu(GAME + '/work/extrap/h_start_7a88.bin'); spec = json.load(open(GAME + '/work/viewcrop/live/X.json')); e.write(spec['img_base'], open(GAME + '/work/viewcrop/live/X.img', 'rb').read())
for s in spec['sites']: e.write(s['addr'], bytes.fromhex(s['new']))
e.setb(0xB8F21, 1)
for p in range(31):
    v = schedule(p, 'zig'); e.setb(0x6105, v)
    e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
    if p == 30:
        ram = e.read(0, 0x100000); buf = e.l(0x1008)
        cyc, pcs, cy, rows = mlib.run(ram, 0x7a88, 0x7b7a, scr=(buf, 0x78000 if buf == 0x70000 else 0x70000))
        fl = [i for i, pc in enumerate(pcs) if pc == 0xd1ca]
        d = collections.Counter()
        for pc, c in zip(pcs[fl[0]:fl[1]], cy[fl[0]:fl[1]]):
            if 0xb8000 <= pc < 0xbb000: d[int(pc)] += int(c)
        # group by 16-byte windows
        g = collections.Counter()
        for pc, c in d.items(): g[pc & ~0x1f] += c
        for k, v in g.most_common(15): print('%x %d' % (k, v))
        t = collections.Counter()
        for pc, c in zip(pcs[fl[1]:], cy[fl[1]:]): t[int(pc) & ~0x1f] += int(c)
        print('tail'); [print('%x %d' % (k, v)) for k, v in t.most_common(8)]
    e.run(0x7a88, 0x7b7a); e.run(0x7b7a, 0x7a88)
