import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
import scripted2 as S
from pathlib import Path
S.W = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')   # logs go to work/shotmiss/sc/
from sim import *
snap='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input/snap/play_enemy.sav'
fl, txt = S.run('shotval1', [], duration=12.0, snap=snap)
print(len(fl))
s=Sim()
exp={}
for i in range(200):
    loop(s)
    t=(s.rw(0x3ad98),s.rw(0x3ad9a),s.rw(0x3ad9c))
    blk=s.uc.mem_read(0x33900,336)
    exp[t]=bytes(blk)
ok=bad=0
first=None
for f in fl:
    t=f['timer']
    if t in exp:
        a=f['blk']; b=exp[t]
        # compare creature slots + player vars (skip scroll/draw fields: compare 0x33944..0x339ae slot block and 0x33a16..0x33a24)
        def rng(x,lo,hi): return x[lo-0x33900:hi-0x33900]
        d=[]
        for (lo,hi) in ((0x33944,0x33944+12*12),(0x33a16,0x33a28)):
            if rng(a,lo,hi)!=rng(b,lo,hi): d.append((hex(lo),))
        if d: bad+=1; first=first or (t,d)
        else: ok+=1
print('matched flips',ok,'differing',bad,first)
n=0
for f in fl:
    t=f['timer']
    if t in exp:
        a=f['blk']; b=exp[t]
        A=[int.from_bytes(a[0x33944-0x33900+o:][:2],'big') for o in range(0,0x72*1,2)]
        B=[int.from_bytes(b[0x33944-0x33900+o:][:2],'big') for o in range(0,0x72*1,2)]
        if A!=B:
            print(t,[ (hex(0x33944+2*i),x,y) for i,(x,y) in enumerate(zip(A,B)) if x!=y][:8]); n+=1
            if n>6: break
print('----')
def sl(b,s):
    g=lambda F:int.from_bytes(b[0x33944-0x33900+F+2*s:][:2],'big')
    return (g(0),g(12),g(0x3c),g(0x48),g(0x54))
for f in fl[:40]:
    t=f['timer']
    if t in exp: print(t,[sl(f['blk'],k) for k in range(2)],'|',[sl(exp[t],k) for k in range(2)], int.from_bytes(f['blk'][0x33a20-0x33900:][:2],'big'))
    else: print(t,'--',[sl(f['blk'],k) for k in range(2)])
print('====')
for f in fl:
    t=f['timer']
    if t in exp and (t[1]==64 and t[2]<=23 or t[1]==63 and t[2]>=70):
        print(t,[sl(f['blk'],k) for k in range(4)],'|',[sl(exp[t],k) for k in range(4)], int.from_bytes(f['blk'][0x33a20-0x33900:][:2],'big'), int.from_bytes(exp[t][0x33a20-0x33900:][:2],'big'))
