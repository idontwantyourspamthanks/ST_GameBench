import sys,os,pickle
sys.path.insert(0,'/tmp/p3b')
from exp2 import *
which,hd,n=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
tag=sys.argv[4] if len(sys.argv)>4 else ''
snap=str(ROOT/'work/snapshots/1mb_ingame_walking.sav')
import os
extra=['w $26aca $4e $71 $4e $71']+['w $%x $%02x $%02x'%(a,hd>>8,hd&255) for a in (0x6742,0x6294,0x764a)]
if os.environ.get('POKEXY'):
    X,Y=map(int,os.environ['POKEXY'].split(','))
    extra.append('w $66e6 '+' '.join('$%02x'%b for b in X.to_bytes(4,'big')+Y.to_bytes(4,'big')))
if os.environ.get('POKEALT'):
    v=int(os.environ['POKEALT'])&0xffff
    extra.append('w $764c $%02x $%02x'%(v>>8,v&255))
D=["m $66e6 8","m $6742 2","m $6290 2","m $eb8c 4","m $764c 2","m $676e 2","m $6772 2","m $6746 2","m $66ee 8","m $b42e6 2","m $6220 2"]
txt=run(snap,'/tmp/p3b/live/'+which,'pc = $3158c',D,n,'p3b_t6_'+which+str(hd)+tag,apply_extra=extra)
out=[]
for r in parse(txt):
    if 0x6290 not in r or 0x66e6 not in r: continue
    out.append(dict(X=sw(r[0x66e6][0:4]),Y=sw(r[0x66e6][4:8]),H=uw(r[0x6742]),clk=uw(r[0xeb8c]),cd=uw(r[0x6290]),alt=sw(r[0x764c]),blk=uw(r[0x676e]),spd=uw(r[0x6772]),bank=sw(r[0x6746]),sv=(sw(r[0x66ee][0:4]),sw(r[0x66ee][4:8])),PH=uw(r[0xb42e6]) if 0xb42e6 in r else None,type=uw(r[0x6220])))
pickle.dump(out,open(f'/tmp/p3b/t6_{which}_{hd}{tag}.pkl','wb'))
print(len(out))
