import sys
from mflib import *
dump=DUMPS['L12']; kind='hard'; target=int(sys.argv[1])
def mk(v,tag):
    e=Emu(dump); apply_live(e, live_build(v,tag)); e.setb(0xB8F21,2); return e
X=mk('X','cmp_ref'); G=mk('G','cmp_cand')
for p in range(target+1):
    v=schedule(p,kind)
    for e in (X,G):
        e.setb(0x6105,v); e.setb(0xB8F08,0); e.setl(0xB8F00,30*(p+1))
    if p==target:
        X.run(0x7a88,0xb8400); G.run(0x7a88,0xb8400)
        a=X.read(0x1000,0xb1700); b=G.read(0x1000,0xb1700)
        d=[0x1000+i for i in range(len(a)) if a[i]!=b[i] and not (0x70000<=0x1000+i<0x80000)]
        runs=[]
        for x in d:
            if runs and x-runs[-1][1]<=1: runs[-1][1]=x
            else: runs.append([x,x])
        print('pass',p,'diff runs at extras entry (X after post stages vs G before):',' '.join(f'{x:x}-{y:x}' for x,y in runs[:40]))
        break
    X.run(0x7a88,0x7b7a); G.run(0x7a88,0x7b7a); X.run(0x7b7a,0x7a88); G.run(0x7b7a,0x7a88)
