import sys, struct, random
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
from emu import *
import model
from unicorn.m68k_const import *
mem=open(model.GAME+'/work/dumps/ram_race_start.bin','rb').read()
def reg(e,n,v): e.uc.reg_write(n,v)
R={'d0':UC_M68K_REG_D0,'d1':UC_M68K_REG_D1,'d7':UC_M68K_REG_D7,'a1':UC_M68K_REG_A1,'a5':UC_M68K_REG_A5,'a3':UC_M68K_REG_A3}
ents=[]
for i in list(range(0,5))+list(range(15,20))+list(range(30,35)):
    p,w,h,xo,yo,nib=struct.unpack('>IhhhhH',mem[0x2156a+i*14:0x2156a+i*14+14]); ents.append((p,h,2,130))
ents.append((struct.unpack('>I',mem[182996:182996+4])[0],21,4,132))
random.seed(1)
bad=0
for (p,h,s,x) in ents:
    for (xx,y) in ((x,151),(x+16*3+0,5),(x-2+... if False else x,170-h)):
        pass
    for xx in (x, x+16, (x&~15)+s+48):
      for y in (0,151,200-h):
        scr=bytes(random.getrandbits(8) for _ in range(32000))
        outs=[]
        for mode in ('stock','model'):
            e=Emu(model.GAME+'/work/extrap/h_start_7a88.bin')
            e.write(0x70000,scr)
            code=model.gen(mem,p,h,xx&15)
            e.write(0xC4000,code)
            reg(e,R['d0'],xx);reg(e,R['d1'],y);reg(e,R['d7'],h);reg(e,R['a1'],p);reg(e,R['a5'],0x70000)
            if mode=='stock': e.call(0x13f6e)
            else:
                a3=0x70000+y*160+(xx>>4)*8
                reg(e,R['a3'],a3); e.call(0xC4000)
            outs.append(e.read(0x70000,32000))
        d=sum(1 for a,b in zip(*outs) if a!=b)
        if d: bad+=1; print('DIFF',hex(p),h,xx,y,d)
print('done bad',bad,'of',len(ents)*9)
