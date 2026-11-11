import glob, collections
from model import *
PL={'R':lambda X,Y,Wd: Wd-X, 'T':lambda X,Y,Wd: Wd-Y, 'L':lambda X,Y,Wd: X+Wd, 'B':lambda X,Y,Wd: Y+Wd, 'Z':lambda X,Y,Wd: Wd}
def Yp(Y): return 2*Y+(Y>>2)
def run(fn):
    s,r,m=analyze(fn)
    hn=collections.Counter(); tot=0; culled=0; caught=0; anyplane=0; caught_by_plane=collections.Counter()
    for c,k,a,oc in r:
        tot+=1
        hs=[S(m,c+o) for o in (0,0x10,0x200,0x210)]
        hmin,hmax=min(hs),max(hs)
        isc = (a!=0)
        culled+=isc
        got=set()
        for pn,f in PL.items():
            fm=-10**9
            for dx in (0,1):
                for dy in (0,1):
                    for h in (hmin,hmax):
                        X,Y,Wd=corner_view(m,c,dx,dy,h)
                        fm=max(fm,f(X,Yp(Y),Wd))
            if fm<0: got.add(pn)
        if got:
            anyplane+=1
            if not isc: print('FALSE CULL?!',hex(c))
        for p in got: caught_by_plane[p]+=1
    return tot,culled,anyplane,dict(caught_by_plane)
if __name__=='__main__':
    for fn in sorted(glob.glob('*_1ebda_*.bin'))[:40]:
        print(fn, run(fn))
