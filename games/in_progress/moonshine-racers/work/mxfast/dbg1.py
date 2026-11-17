import sys
from mflib import *
sys.argv=['x']
dump=DUMPS['start']
def mk(v):
    e=Emu(dump); apply_live(e, live_build(v,'cmp_'+v)); e.setb(0xB8F21,2); return e
A=mk('X'); B=mk('M')
sy=symbols(GAME+'/patches/mf_sync.s'); sx=symbols(GAME+'/patches/mx_sync.s')
for e in (A,B):
    e.setb(0xB8F08,0); e.setl(0xB8F00,30); e.run(0x7a88,0x7b74)
pa=A.read(0xB9E00,2688); pb=B.read(0xB9E00,2688)
print('slots equal at 7b74:', A.read(0x2c68,2688)==B.read(0x2c68,2688))
blocks=lambda b:[b[i:i+48] for i in range(0,2688,48)]
print('PREBUF M reversed blocks == X:', blocks(pb)[::-1]==blocks(pa))
print('PREBUF == slots(before post)?', pa==A.read(0x2c68,2688))
rb=b''.join(blocks(pb)[::-1])
d=[i for i in range(2688) if rb[i]!=pa[i]]
print(len(d), d[:20])
print(pa[:48].hex()); print(rb[:48].hex()); print(pb[-48:].hex())
print(hex(B.l(0x7b46+2)), B.read(0x7b46,6).hex(), B.read(0xb8300,0x40).hex())
for i in d[:12]: print(i, hex(0x2c68+i), 'X', pa[i], 'M', rb[i], 'slots', A.read(0x2c68+i,1)[0])
