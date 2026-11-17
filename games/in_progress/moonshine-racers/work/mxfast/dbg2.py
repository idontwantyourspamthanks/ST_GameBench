import sys
from mflib import *
dump=DUMPS['start']
def mk(v):
    e=Emu(dump); apply_live(e, live_build(v,'cmp_'+v)); e.setb(0xB8F21,2); return e
A=mk('X'); B=mk('M')
for p in range(3):
    for e in (A,B):
        e.setb(0xB8F08,0); e.setl(0xB8F00,30*(p+1)); e.run(0x7a88,0x7b74)
    pre=(A.read(0x27c8,0x26).hex(), B.read(0x27c8,0x26).hex())
    for e in (A,B): e.run(0x7b74,0x7b7a)
    print(p,'before', pre[0]); print('  X after', A.read(0x27c8,0x26).hex()); print('  M after', B.read(0x27c8,0x26).hex())
    for e in (A,B): e.run(0x7b7a,0x7a88)
