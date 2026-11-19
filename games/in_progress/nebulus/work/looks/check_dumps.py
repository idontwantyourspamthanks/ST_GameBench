"""Verify per level-start dump: palette == table[tower], raster 4 colours == table[tower], eye buffer == f(tower&3), body buffer == g(tower), mission independent."""
import sys,struct
D=sys.argv[1]
ref=open('work/dumps/tower_1mb.bin','rb').read()
spec=[(1,t) for t in range(8)]+[(2,0),(2,3)]
d=[open(f'{D}/lvl{i}.bin','rb').read() for i in range(len(spec))]
eye={}; body={}
print('lvl  mission tower | $351ac==pal[t]  $40398==ras[t]  eye-buf md5(t&3)  body-buf $100e0 md5 (t)')
import hashlib
for i,(m,t) in enumerate(spec):
    x=d[i]
    p=x[0x351ac:0x351cc]==ref[0x35250+32*t:0x35250+32*t+32]
    r=x[0x40398:0x403a0]==ref[0x351e8+8*t:0x351e8+8*t+8]
    e=hashlib.md5(x[0x24be0:0x2fae0]).hexdigest()[:8]; b=hashlib.md5(x[0x100e0:0x110e0]).hexdigest()[:8]
    eye.setdefault(t&3,set()).add(e); body.setdefault(t,set()).add(b)
    print(f'{i:3d}  M{m}      T{t+1}    | {p!s:14s} {r!s:14s} {e} (set {t&3})   {b}  mission-in-RAM {struct.unpack(">H",x[0x33910:0x33912])[0]} tower-in-RAM {struct.unpack(">H",x[0x3390c:0x3390e])[0]}')
print('eye buffer values per t&3 (must be one each):',{k:len(v) for k,v in eye.items()},' body buffer values per tower (one each):',{k+1:len(v) for k,v in body.items()})
print('distinct eye buffers over 10 levels:',len({hashlib.md5(x[0x24be0:0x2fae0]).hexdigest() for x in d}),' distinct body buffers:',len({hashlib.md5(x[0x100e0:0x110e0]).hexdigest() for x in d}),' ball/frame 0-11 buffers distinct:',len({hashlib.md5(x[0x14560:0x24be0]).hexdigest() for x in d}))
