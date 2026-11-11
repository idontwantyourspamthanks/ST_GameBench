import glob, sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from model import *
import blobsim
def decode(m):
    a=L(m,0x66d0); poly=[]; mk=0
    while True:
        d7=W(m,a); a+=2
        if d7==0: break
        if d7&0x8000: a+=2; mk+=1; continue
        rec=0x7c718+d7
        col=S(m,rec); 
        if col<0: continue
        vs=[]; p=rec+2
        if W(m,p)==0: continue
        while True:
            v=W(m,p); p+=2
            if v==0: break
            vs.append(v)
        d1=0; d2=0xffff
        for v in vs:
            oc=W(m,0x7c718+v+4); d1|=oc; d2&=oc
        drawn = (d1==0) or (d2==0)
        poly.append((vs,drawn))
    return poly,mk
rows=[]
for pat in sys.argv[1:]:
    for fn in sorted(glob.glob(pat)):
        s,r,m=analyze(fn)  # cells list (class etc.) still valid at 1dcaa
        poly,mk=decode(m)
        used=set(v for vs,dr in poly if dr for v in vs)
        # slot data offsets of all transformed vertices: dedupe by data offset
        allv=set(); keptv=set(); kept=0; real_nonempty=0
        D=blobsim.prologue(m)
        for c,k,a,oc in r:
            vs=[W(m,0x7c718+W(m,c+o+8)) for o in (0,0x10,0x200,0x210)]
            allv|=set(vs)
            cu = k==0xff and blobsim.celltest(m,D,c)
            if not cu: keptv|=set(vs); kept+=1
        # emitted polygons in stream: vertices of cells that emit
        ndrawn=sum(1 for p in poly if p[1])
        rows.append((fn.split('/')[-1],len(r),kept,len(allv),len(keptv),len(used),len(poly),ndrawn))
        print(rows[-1])
import statistics
print('mean cells %.1f kept %.1f | vertices transformed base %.1f after cull %.1f used by drawn %.1f | stream polys %.1f drawn %.1f'%tuple(statistics.mean(r[i] for r in rows) for i in range(1,8)))
