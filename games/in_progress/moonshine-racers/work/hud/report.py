import sys, io, contextlib; sys.path.insert(0,'work/hud')
from analyze import *
import os
ALL='f1c0+efc6+f214+f3b6+f430+f53c+11ef0+f90c+f620+f76a+f7f0+f22c+f134'
out=io.StringIO()
def P(*a): print(*a, file=out)
# ---- savings, driving (race_start), windows
ps,ss=lw('race_start','stock')
cfgs=['f22c','f214','f22c+f214','f3b6','f430','f53c','f53c+f430','11ef0','f90c','11ef0+f90c','efc6','f1c0+f134','efc6+f1c0+f134','f620','f76a','f7f0','f76a+f7f0',ALL]
P('## savings of pass work (cycles/pass), race_start, stock game: windows 0x5c-0x80 (no speech), 0x83-0xb7 (speech typing/hold), 0x43-0xba (all)')
for cfg in cfgs:
    p,_=lw('race_start',cfg); row=[]
    for lo,hi in ((0x5c,0x80),(0x83,0xb7),(0x43,0xba)):
        ks=[k for k in win(ps,lo,hi) if k in p]; row.append((mean(ps,ks)-mean(p,ks),mean(ps,ks)))
    n,w=state_diff('race_start',cfg)
    P(f"{cfg[:30] if cfg!=ALL else 'ALL13':30s} {row[0][0]:9.0f} ({100*row[0][0]/row[0][1]:4.1f}%) {row[1][0]:9.0f} ({100*row[1][0]/row[1][1]:4.1f}%) {row[2][0]:9.0f} | state common {n}: {fmt_ranges(w)}")
# ---- grid
ps,ss=lw('race_grid','stock')
cl={k:('speech' if ss[k]['11ab'] else 'none') for k in ps if k in ss}
P('\n## savings, race_grid, classes by stock message state')
cfgs=['f22c','f214','f22c+f214','f620','f76a','f7f0','f76a+f7f0','efc6','f90c','11ef0+f90c','f53c','f3b6',ALL]
for cfg in cfgs:
    p,_=lw('race_grid',cfg); row=[]
    for c in ('none','speech'):
        ks=[k for k in cl if cl[k]==c and k in p]; row.append((mean(ps,ks)-mean(p,ks),mean(ps,ks)))
    n,w=state_diff('race_grid',cfg)
    P(f"{cfg[:30] if cfg!=ALL else 'ALL13':30s} none {row[0][0]:9.0f} ({100*row[0][0]/row[0][1]:4.1f}%)  speech {row[1][0]:9.0f} ({100*row[1][0]/row[1][1]:4.1f}%) | state common {n}: {fmt_ranges(w)}")
# ---- shipped
p,_=lw('race_start','stock')
P('\n## on top of mr_edge+mr_map+mr_digit (live image), race_start')
b,_=load('live3_race_start_stock')
for cfg in ['f22c+f214','f3b6','f53c','f7f0','f76a','f620','11ef0+f90c',ALL]:
    q,_=load(f'live3_race_start_{cfg}')
    row=[]
    for lo,hi in ((0x5c,0x80),(0x83,0xb7)):
        kk=[k for k in range(lo,hi+1) if k in b and k in q]; row.append((sum(b[k]['work']-q[k]['work'] for k in kk)/len(kk),sum(b[k]['work'] for k in kk)/len(kk)))
    P(f"{cfg[:30] if cfg!=ALL else 'ALL13':30s} {row[0][0]:9.0f} ({100*row[0][0]/row[0][1]:4.1f}%) {row[1][0]:9.0f} ({100*row[1][0]/row[1][1]:4.1f}%)")
# ---- cumulative
ps,ss=lw('race_start','stock')
P('\n## cumulative (order: f22c f214 f620 f76a f90c f7f0 f3b6 f53c f430 efc6 f1c0 f134), race_start windows')
for n in (2,3,4,5,6,7,8,12):
    f=RES/f'skip_race_start_cum_{n}.json'
    if not f.exists(): continue
    q,_=load(f'skip_race_start_cum_{n}')
    row=[]
    for lo,hi in ((0x5c,0x80),(0x83,0xb7)):
        kk=[k for k in win(ps,lo,hi) if k in q]; row.append((mean(ps,kk)-mean(q,kk),mean(ps,kk)))
    P(f"cum{n}: {row[0][0]:9.0f} ({100*row[0][0]/row[0][1]:4.1f}%) {row[1][0]:9.0f} ({100*row[1][0]/row[1][1]:4.1f}%)")
open(OUT/'res'/'numbers.txt','w').write(out.getvalue()); print(out.getvalue())
