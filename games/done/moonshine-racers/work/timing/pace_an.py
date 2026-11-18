import sys,re
sys.path.insert(0,'.')
from tlib import *
def events(raw):
    ev=parse_chain(raw,0)
    rows=[]
    for pc,vals in ev:
        e=[v[1] for v in vals if v[0]=='e']; m=[v for v in vals if v[0]=='m']
        if len(e)<2 or len(m)<3: continue
        b611a=m[0][2][0]; b611b=m[0][2][1]
        s1004=int.from_bytes(m[1][2][0:4],'big'); s1008=int.from_bytes(m[1][2][4:8],'big')
        hw=m[2][2]; base=(hw[1]<<16)|(hw[3]<<8)
        rows.append(dict(pc=pc,vbl=e[0],fc=e[1],c611a=b611a,c611b=b611b,b1004=s1004,b1008=s1008,hw=base))
    return rows
def fit(rows):
    best=None
    for c0 in sorted({r['fc'] for r in rows})+[CYC]:
        t=[(r['vbl']+(1 if r['fc']<c0 else 0))*CYC+r['fc'] for r in rows]
        bad=sum(1 for i in range(1,len(t)) if t[i]<t[i-1])
        if best is None or bad<best[0]: best=(bad,c0)
    return best
if __name__=='__main__':
    raw=open(sys.argv[1]).read()
    rows=events(raw)
    bad,c0=fit(rows)
    print("events",len(rows),"viol",bad,"c0",c0)
    t0=None
    for r in rows:
        t=(r['vbl']+(1 if r['fc']<c0 else 0))*CYC+r['fc']
        if t0 is None: t0=t
        print(f"{r['pc']:05x} t={(t-t0)/CYC:7.3f} VBL  game611a={r['c611a']:3d} 611b={r['c611b']:3d} $1004={r['b1004']:05x} $1008={r['b1008']:05x} ff8201/03={r['hw']:05x}")
