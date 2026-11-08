import sys,os,pickle
sys.path.insert(0,'/tmp/ti2')
from exp import *
which,n=sys.argv[1],int(sys.argv[2])
snap=str(ROOT/'work/snapshots/1mb_ingame_walking.sav')
D=["m $66e6 4","m $6fbe 2","m $675a 2","m $6740 2","m $6746 2","m $b42e6 2","m $eb8c 4","m $6290 2"]
txt=run(snap,'/tmp/p3b/live/'+which,'pc = $3461e',D,n,'p3b_t5_'+which)
for r in parse(txt):
    if 0x6fbe not in r: continue
    print(uw(r[0x6fbe]),uw(r[0x675a]),sw(r[0x6740]),uw(r[0x6746]),uw(r[0xb42e6]) if 0xb42e6 in r else None,uw(r[0x6290]),uw(r[0xeb8c]))
