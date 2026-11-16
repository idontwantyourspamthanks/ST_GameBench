import sys; sys.path.insert(0,'work/hud')
from hudlab import *
NAMES=[n for n,_ in STAGES[1:-1]]
def classes(p,s):
    c={}
    for k in p:
        if k in s:
            a=s[k]['11ab']; c[k]='typing' if a==1 else 'hold' if a and a>=2 else 'none'
    return c
def table(p,keys,label):
    keys=[k for k in keys if k in p]
    if not keys: print(label,'no passes'); return
    print(f"{label}: {len(keys)} passes")
    tot=0
    for n in NAMES+['work']:
        vs=[p[k]['work'] if n=='work' else p[k]['stage'].get(n,0) for k in keys]
        print(f"  {n:9s} mean {sum(vs)/len(vs):9.0f}  min {min(vs):8d} max {max(vs):8d}")
if __name__=='__main__':
    p,s=load(sys.argv[1]); c=classes(p,s)
    for cl in ('typing','hold','none'):
        table(p,[k for k in c if c[k]==cl],cl)
