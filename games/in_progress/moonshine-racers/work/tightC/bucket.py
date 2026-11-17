"""python3 bucket.py NAME [top] : per-function exclusive cycles/pass from res/prof_NAME.txt + res/ram_NAME.bin"""
import sys, bisect, struct
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, G+'/tools')
import msrprof as P
name=sys.argv[1]; top=int(sys.argv[2]) if len(sys.argv)>2 else 60
ram=open(f'{G}/work/tightC/res/ram_{name}.bin','rb').read()
prof=P.load(f'{G}/work/tightC/res/prof_{name}.txt')
tg=set(P.targets(ram))
# extra: blob entry points
for a in (0xb3040,0xb4004,0xb5004,0xb6000,0xbb004,0xbb700):
    tg.add(a)
tg=sorted(tg)
frames=prof.get(0xd1ca,(0,0))[1]
tot=sum(c for c,_ in prof.values())
out={}
for a,(c,n) in prof.items():
    i=bisect.bisect_right(tg,a)-1; f=tg[i] if i>=0 else a
    b=out.setdefault(f,[0,0]); b[0]+=c; b[1]=max(b[1],prof.get(f,(0,0))[1])
print(f'frames={frames} cyc/frame={tot/frames:.0f}')
for f,(c,n) in sorted(out.items(),key=lambda kv:-kv[1][0])[:top]:
    print(f'${f:05x} {c/frames:9.0f} {100*c/tot:5.1f}% calls/f {n/frames:6.2f} cyc/call {(c/n if n else 0):8.0f}')
