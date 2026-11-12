import glob, collections, itertools, sys
from model import *
# 4F upper bound functional coefficients on (X,Y,W) [Y real, Y'=2.25Y], slack
PLANES={'B':((0,9,4),0),'R':((-4,0,4),4),'L':((4,0,4),0),'T':((0,-9,4),3+4),'Z':((0,0,4),0)}
def tab(m,base,idx,k): return S(m,base+8*idx+2*k)
def run(fn,planes,gran=3,slack_extra=8):
    s,r,m=analyze(fn)
    cells={}
    for c,k,a,oc in r:
        i=(c-0x6c000)//16; row,col=divmod(i,32); cells[(col,row)]=(c,a)
    best=None
    for px in range(3):
        for py in range(3):
            g=collections.defaultdict(list)
            for (col,row) in cells: g[((col-px)//3,(row-py)//3)].append((col,row))
            if best is None or len(g)<best[0]: best=(len(g),g,(px,py))
    g,(px,py)=best[1],best[2]
    mh=[S(m,a) for a in (0x18568,0x1856a,0x1856c)]
    culled=sum(1 for v in cells.values() if v[1])
    covered=0; nb=0; blk_by_plane=collections.Counter()
    for (gx,gy),lst in g.items():
        bx0=3*gx+px; by0=3*gy+py
        # heights of 4x4 vertex window
        hs=[]
        for dj in range(4):
            for di in range(4):
                rec=0x6c000+16*((by0+dj)*32+(bx0+di))
                hs.append(S(m,rec))
        hmin,hmax=min(hs),max(hs)
        if hmin<0: continue
        ic=[S(m,0x6c000+16*(by0*32+bx0)+0xc)//8, ]
        i0=S(m,0x6c000+16*(by0*32+bx0)+0xc)//8; j0=S(m,0x6c000+16*(by0*32+bx0)+0xe)//8
        ok=None
        for p in planes:
            (a,b,c),sl=PLANES[p]
            coef=[a,b,c]
            # position part max over corners entries i0..i0+3, j0..j0+3
            pm1=max(sum(coef[k]*tab(m,0x188f8,i,k) for k in range(3)) for i in (i0,i0+3))
            pm2=max(sum(coef[k]*tab(m,0x18a40,j,k) for k in range(3)) for j in (j0,j0+3))
            K=sum(coef[k]*mh[k] for k in range(3))
            hsel=hmax if K>=0 else hmin
            hb=(K*hsel)/16384.0
            ub=pm1+pm2+hb+sl+slack_extra
            if ub<0:
                ok=p; blk_by_plane[p]+=1; break
        nb+=1
        if ok:
            n=sum(1 for q in lst if cells[q][1])
            assert n==len(lst),(fn,'false cull',lst,[cells[q] for q in lst])
            covered+=len(lst)
    return len(cells),culled,nb,covered,dict(blk_by_plane)
if __name__=='__main__':
    for planes in (['B'],['B','R','L'],['B','R','L','T','Z']):
        print(planes)
        tot=[0,0,0]
        for fn in sorted(glob.glob('*_1ebda_*.bin')):
            r=run(fn,planes); 
            print(' ',fn,r)
            tot[0]+=r[0]; tot[1]+=r[1]; tot[2]+=r[3]
        print(' TOTAL cells/culled/covered',tot)
