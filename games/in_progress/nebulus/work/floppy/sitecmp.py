import struct,re,sys
from pathlib import Path
NEB=Path('../..').resolve()
def load(path):
    x=open(path,'rb').read()
    ts,ds=struct.unpack('>LL',x[2:10])
    ss=struct.unpack('>L',x[14:18])[0]
    body=bytearray(x[28:28+ts+ds])
    rt=x[28+ts+ds+ss:]
    offs=[]
    o=struct.unpack('>L',rt[:4])[0]; p=4
    if o:
        offs.append(o)
        while rt[p]:
            if rt[p]==1: o+=254
            else: o+=rt[p]; offs.append(o)
            p+=1
    return body,offs,ts
BASE=0x33b1c
def reloc(body,offs):
    b=bytearray(body)
    for o in offs:
        v=struct.unpack('>L',b[o:o+4])[0]+BASE
        b[o:o+4]=struct.pack('>L',v)
    return b
pp,ppo,ppts=load(NEB/'work/boot/NEBEXE.FIC.out')
fl,flo,flts=load('ex/TOPPLER.JMP')
print('PP text',hex(ppts),'relocs',len(ppo),' floppy text',hex(flts),'relocs',len(flo))
# mapping PP text offset -> floppy text offset (structural diffs found by resync)
def m(p):
    # piecewise deltas (PP - floppy)
    pts=[(0,0),(0x4c46,36),(0x8406,24),(0x8436,12),(0x8505,8)]
    d=0
    for s,dd in pts:
        if p>=s: d=dd
    return p-d
if __name__=='__main__':
    print('map check: text off 0x7588 ->',hex(m(0x7588)))

# exact map segments: (pp_start, pp_end, delta) where f = p - delta ; None = changed block
SEG=[(0,0x4c46,0),(0x4c78,0x8406,36),(0x8406+0,0x8436,24),(0x8436,0x8505+5,12)]
SEG=[(0,0x4c46,0),(0x4c78,0x8406,36),(0x8406,0x8436,24),(0x8436,0x850a,12),(0x850a,0xa866,8)]
def mp(p):
    for s,e,d in SEG:
        if s<=p<e: return p-d
    return None
def mabs(v):  # absolute address pp -> floppy
    o=v-BASE
    if o>=0x8000000: return None
    r=mp(o) if o<ppts else None
    if o>=ppts: r=o-8
    return None if r is None else BASE+r
def compare():
    ppr=reloc(pp,ppo); flr=reloc(fl,flo)
    ppset=set(ppo)
    # normalise PP
    n=bytearray(ppr)
    for o in ppo:
        v=struct.unpack('>L',n[o:o+4])[0]; a=mabs(v)
        if a is None: continue
        n[o:o+4]=struct.pack('>L',a)
    bad=[]
    for p in range(0,ppts):
        f=mp(p)
        if f is None: continue
        if n[p]!=flr[f]: bad.append(p)
    return n,flr,bad
if __name__=='__main__':
    n,flr,bad=compare()
    print('mismatching bytes in mapped text:',len(bad))
    # group
    g=[];
    for p in bad:
        if g and p-g[-1][1]<=3: g[-1][1]=p
        else: g.append([p,p])
    for a,b in g[:60]: print('pp %x-%x (addr %x) floppy %x'%(a,b,a+BASE,mp(a)+BASE), n[a:b+1].hex(), flr[mp(a):mp(a)+b-a+1].hex())
    print(len(g))
