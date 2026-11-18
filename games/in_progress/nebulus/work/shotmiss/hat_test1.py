import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from hatt import *
ats=[dict(bx=88,cnt=0,spd=0,fx=105),dict(bx=90,cnt=5,spd=1,fx=105),dict(bx=95,cnt=3,spd=1,fx=105)]
timers, fl, starts, txt = hat_chain(ats,'ht1')
_, srows, _ = sim_chain(ats)
hr = hat_rows(timers, fl)
print(len(fl),'flips', len(hr),'matched loops of', len(srows))
print(compare(srows,hr))
for r in srows[:12]:
    print(r['L'], {k:r[k] for k in ('bx','by','bst','sx','sy','sst','pst')}, hr.get(r['L']) and {k:hr[r['L']][k] for k in ('bx','by','bst','sx','sy','sst','pst')})
