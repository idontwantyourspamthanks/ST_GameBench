"""compare region [$4b78,$4ff8) right after 17c24 (at $7b04) and after the geometry ($7b0a), REF vs LIVE. python3 emstage.py DUMP NPASS LIVE sched"""
import sys, os
sys.path.insert(0,'../extrap'); sys.path.insert(0,'.')
from emu import Emu
from proto import flip
import emgate
dump, npass, live, kind = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
a = Emu(dump); b = Emu(dump)
emgate.apply_live(a, os.environ['REF']); emgate.apply_live(b, live)
bad = [0, 0, 0]
for p in range(npass):
    v = emgate.schedule(p, kind)
    for e in (a, b):
        if v is not None: e.setb(0x6105, v)
    for i, stop in enumerate((0x7b04, 0x7b0a)):
        for e in (a, b): e.run(0x7a88 if i == 0 else 0x7b04, stop)
        if a.read(0x4b78, 0x480) != b.read(0x4b78, 0x480): bad[i] += 1
    for e in (a, b): e.run(0x7b0a, 0x7b74); flip(e); e.run(0x7b7a, 0x7a88)
print(f'{live} {kind} passes {npass}: region differs after 17c24 in {bad[0]} passes, after geometry in {bad[1]} passes')
