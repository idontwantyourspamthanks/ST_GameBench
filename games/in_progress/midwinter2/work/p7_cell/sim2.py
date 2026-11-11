import glob, collections
from model import *
from sim1 import PL, Yp
def blocks(cellidx, phase):
    px,py=phase
    return ((cellidx[0]-px)//3,(cellidx[1]-py)//3)
def run(fn,verbose=False):
    s,r,m=analyze(fn)
    cells={}
    for c,k,a,oc in r:
        i=(c-0x6c000)//16; row,col=divmod(i,32)
        cells[(col,row)]=(c,a)
    best=None
    for px in range(3):
        for py in range(3):
            g=collections.defaultdict(list)
            for (col,row),v in cells.items(): g[((col-px)//3,(row-py)//3)].append((col,row))
            if best is None or len(g)<best[0]: best=(len(g),(px,py))
    phase=best[1]
    g=collections.defaultdict(list)
    for (col,row),v in cells.items(): g[((col-phase[0])//3,(row-phase[1])//3)].append((col,row))
    culled_total=sum(1 for v in cells.values() if v[1]); 
    covered=0; blk_culled=0
    for bk,lst in g.items():
        # collect hull: all cell corner vertices of cells in the block (vertices from heights)
        pts=[]
        hs=[]
        for (col,row) in lst:
            c,a=cells[(col,row)]
            for dx,dy,o in ((0,0,0),(1,0,0x10),(0,1,0x200),(1,1,0x210)):
                hs.append(S(m,c+o))
        hmin,hmax=min(hs),max(hs)
        c0=cells[lst[0]][0]
        # hull over the cells' corners at hmin,hmax
        fm={p:-10**9 for p in PL}
        for (col,row) in lst:
            c,a=cells[(col,row)]
            for dx in (0,1):
                for dy in (0,1):
                    for h in (hmin,hmax):
                        X,Y,Wd=corner_view(m,c,dx,dy,h)
                        for p,f in PL.items(): fm[p]=max(fm[p],f(X,Yp(Y),Wd))
        if any(v<0 for v in fm.values()):
            blk_culled+=1
            covered+=sum(1 for q in lst if cells[q][1])
            # all culled? yes by hull
            assert all(cells[q][1] for q in lst)
    return len(cells),culled_total,len(g),blk_culled,covered
if __name__=='__main__':
    for fn in sorted(glob.glob('*_1ebda_*.bin')): print(fn,run(fn))
