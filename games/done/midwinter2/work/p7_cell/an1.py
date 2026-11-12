import sys, struct, glob
def W(m,a): return struct.unpack('>H',m[a:a+2])[0]
def S(m,a): return struct.unpack('>h',m[a:a+2])[0]
def L(m,a): return struct.unpack('>I',m[a:a+4])[0]
def analyze(fn, verbose=False):
    m=open(fn,'rb').read()
    p58=L(m,0x18758); p5c=L(m,0x1875c); p60=L(m,0x18760)
    mode=W(m,0x18768); cur=W(m,0x67c4)
    cells=[]
    a=p5c
    while True:
        c=L(m,a); a+=4
        if c==0: break
        cells.append(c)
    # accepted list
    acc=[]; a=p58
    while True:
        c=L(m,a); a+=4
        if c==0: break
        acc.append(c)
    stat={'acc':len(acc),'cl':len(cells),'mode':mode}
    nculled=0; cls={}
    res=[]
    for c in cells:
        k=m[c+0xa]; 
        offs=[W(m,c+8),W(m,c+0x18),W(m,c+0x208),W(m,c+0x218)]
        dat=[W(m,0x7c718+o) for o in offs]; oc=[W(m,0x7c718+d+4) for d in dat]
        andv=oc[0]&oc[1]&oc[2]&oc[3]
        cls.setdefault(k,[0,0]); cls[k][0]+=1
        if andv: cls[k][1]+=1
        res.append((c,k,andv,oc))
    stat['cls']=cls
    return stat,res,m
if __name__=='__main__':
    for fn in sorted(glob.glob(sys.argv[1])):
        s,r,m=analyze(fn)
        print(fn.split('/')[-1], s)
