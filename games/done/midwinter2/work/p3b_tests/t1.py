import sys,os,pickle
sys.path.insert(0,'/tmp/p3b')
from exp2 import *
which,snapname,n=sys.argv[1],sys.argv[2],int(sys.argv[3])
snap=str(ROOT/'work/snapshots/1mb_ingame_walking.sav') if snapname=='walk' else snapname
live='/tmp/p3b/live/'+which
D=["m $66e6 8","m $6742 2","m $6290 2","m $eb8c 4","m $764c 2","m $6746 2","m $6750 2","m $6772 2","m $674e 2","m $b42e6 2","m $6220 2","m $6fbe 2"]
txt=run(snap,live,'pc = $3158c',D,n,apply_extra=['w $26aca $4e $71 $4e $71'],tag='p3b_t1_'+which+snapname.split('/')[-1][:5])
rows=parse(txt)
out=[]
for r in rows:
    if 0x6290 not in r or 0x66e6 not in r: continue
    out.append(dict(X=sw(r[0x66e6][0:4]),Y=sw(r[0x66e6][4:8]),H=uw(r[0x6742]),clk=uw(r[0xeb8c]),cd=uw(r[0x6290]),alt=sw(r[0x764c]),bank=sw(r[0x6746]),thr=uw(r[0x6750]),spd=uw(r[0x6772]),lean=sw(r[0x674e]),PH=uw(r[0xb42e6]) if 0xb42e6 in r else None,btn=uw(r[0x6fbe])))
pickle.dump(out,open(f'/tmp/p3b/t1_{which}_{snapname.split('/')[-1][:5]}.pkl','wb'))
for i,o in enumerate(out): print(i,o)
