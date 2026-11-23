"""Per-loop trace of one shot at a hopping ball (sim, play_enemy base): trace1.py BALL_X HOP_CNT SPEED [FROG_X]"""
import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from sim import *
bx,cnt,spd=map(int,sys.argv[1:4]); fx=int(sys.argv[4]) if len(sys.argv)>4 else 105
s=Sim(); img=s.snap(); pr=Probe(s)
prep(s,img,dict(x=bx,y=60,spd=spd,cnt=cnt),dict(x=fx))
for r in shoot(s,fire_at=0,nloops=22,probe=pr):
    print(r['i'],'ball',r['bx'],r['by'],r['bst'],r['bcnt'],r['bspd'],'shot',r['sx'],r['sy'],r['sst'],r['scnt'],'P',r['pst'],r['pstep'],'dx',sgn(r['sx']-r['bx'],128),'dy',r['sy']-r['by'],r['ov'],r['terr'])
