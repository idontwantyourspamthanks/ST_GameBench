import sys; sys.path.insert(0,'.')
from render import *
import numpy as np
PAL=3546895.0
print('tune  ticks   sec  avgvoices  max  %ticks>=3voices | share of voiced channel-ticks with rate above 6258 / 12517 / 25033 | per-voice rate p50/p90/max')
tot=[]
for n in range(1,18):
    per,L=loop_ticks(n); T=min(L,7000)
    m=Music(); m.start(n); chs=[Chan() for _ in range(4)]; apply_writes(chs,m.out)
    vc=[]; rates=[]
    for t in range(T):
        m.out=[]; m.tick(); apply_writes(chs,m.out)
        k=0
        for c in chs:
            if c.on and c.vol>0:
                k+=1; rates.append(PAL/max(c.per,113))
        vc.append(k)
    vc=np.array(vc); r=np.array(rates)
    f=lambda th: 100*(r>th).mean() if len(r) else 0
    print(f'{n:2d} {T:6d} {T/TICK_HZ:6.1f} {vc.mean():5.2f} {vc.max()} {100*(vc>=3).mean():5.1f}% | {f(6258):5.1f} {f(12517):5.1f} {f(25033):5.1f} | {np.percentile(r,50):7.0f} {np.percentile(r,90):7.0f} {r.max():7.0f}')
