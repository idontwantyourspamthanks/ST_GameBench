import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
from emuhud import *
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/tools')
import msrmask
A,B=sys.argv[1],sys.argv[2]; levels=[int(x) for x in sys.argv[3].split(',')]; n=int(sys.argv[4])
def run(dump,live,kind):
    e=Emu(dump); apply_live_p(e,live); fl=[]
    e.uc.hook_add(UC_HOOK_CODE,lambda uc,a,s,u: fl.append((bytes(uc.mem_read(e.l(0x1008),0x7d00)),e.w(0x100e))),begin=0xd1ca,end=0xd1ca)
    for p in range(n):
        v=schedule(p,kind)
        if v is not None: e.setb(0x6105,v)
        e.run(0x7a88,0x7b74); flip(e); e.run(0x7b7a,0x7a88)
    return fl
tot=0; frames=0; dfr=0; ys=[]; xs=[]; mx=0
for L in levels:
    fa=run(DUMPS%L,A,'up'); fb=run(DUMPS%L,B,'up')
    for (a,_),(b,_) in zip(fa,fb):
        frames+=1
        ia=msrmask.planar_to_idx(a); ib=msrmask.planar_to_idx(b)
        d=ia!=ib
        if d.any():
            dfr+=1; yy,xx=np.nonzero(d); ys+=list(yy); xs+=list(xx); tot+=int(d.sum()); mx=max(mx,int(d.sum()))
print('frames',frames,'differing',dfr,'pixels total',tot,'max per frame',mx)
if ys: print('bbox rows',min(ys),max(ys),'cols',min(xs),max(xs))
