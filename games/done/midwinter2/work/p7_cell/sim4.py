import glob
from model import *
# plane coefficient (a,b,c) for X,Y,W in 4F units; slack folded constants
PL={'B':((0,9,4),1),'R':((-4,0,4),5),'L':((4,0,4),1),'T':((0,-9,4),12),'Z':((0,0,4),1)}
def cellcull(m,c,planes):
    hs=[S(m,c+o) for o in (0,0x10,0x200,0x210)]
    hmax=max(hs);hmin=min(hs)
    ci=S(m,c+0xc); ei=S(m,c+0xe)
    out=[]
    for p in planes:
        (a,b,cc),sl=PL[p]
        co=[a,b,cc]
        # position max over the 4 corners
        def pos(base,idx):
            return sum(co[k]*S(m,base+8*idx+2*k) for k in range(3))
        i=ci//8; j=ei//8
        pm=max(pos(0x188f8,i),pos(0x188f8,i+1))+max(pos(0x18a40,j),pos(0x18a40,j+1))
        K=sum(co[k]*S(m,0x18568+2*k) for k in range(3))
        hsel=hmax if K>=0 else hmin
        ub=pm+ ((-(-K//8))*hsel>>11) +sl+ (2 if K<0 else 0)
        if ub<0: out.append(p)
    return out
tot={k:0 for k in ('cells','real','B','BR','BRL','BRLZT')}
for fn in sorted(glob.glob('*_1ebda_*.bin')):
    s,r,m=analyze(fn)
    cnt={k:0 for k in ('B','BR','BRL','BRLZT')}
    nreal=0; ncell=0
    for c,k,a,oc in r:
        if S(m,c+6)!=0: continue
        ncell+=1
        real=a!=0
        if not real: 
            continue
        nreal+=1
        ps=cellcull(m,c,['B','R','L','Z','T'])
        if 'B' in ps: cnt['B']+=1
        if 'B' in ps or 'R' in ps: cnt['BR']+=1
        if set(ps)&{'B','R','L'}: cnt['BRL']+=1
        if ps: cnt['BRLZT']+=1
    print(fn,len(r),'real',nreal,cnt)
