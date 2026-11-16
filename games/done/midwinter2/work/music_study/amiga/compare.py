import sys, json, collections
sys.path.insert(0,'.')
from sim import *
rows=[json.loads(l) for l in open(sys.argv[1] if len(sys.argv)>1 else 'tl_trace.jsonl')]
tune=int(sys.argv[2]) if len(sys.argv)>2 else 1
LO=0x24cb80; HI=0x24d980
names={0xdff096:'DMACON'}
for c in range(4):
    b=0xdff0a0+16*c
    names[b]=f'LC{c}'; names[b+4]=f'LEN{c}'; names[b+6]=f'PER{c}'; names[b+8]=f'VOL{c}'
real=[r for r in rows if LO<=r[4]<HI and r[5] in names]
print('real rows',len(real))
# start = first row (reset DMACON 15 at frame f0)
f0=real[0][0]
byf=collections.OrderedDict()
for r in real: byf.setdefault(r[0],[]).append((names[r[5]],r[7]))
frames=list(byf)
print('first frame',f0,'last',frames[-1],'nframes',len(frames))
# determine delta for LC
delta=None
m=Music(); m.start(tune)
# reset frame
reset=byf[f0]
sim_reset=m.out[:]
mism=0
def norm(seq,delta):
    return [(k,(v-delta) if k.startswith('LC') and v!=0 and delta is not None else v) for k,v in seq]
# find delta from first real LC nonzero
simfirst=None
m2=Music(); m2.start(tune); m2.tick()
sl=[v for k,v in m2.out if k.startswith('LC') and v]
rl=[v for k,v in byf[frames[1]] if k.startswith('LC') and v]
delta=sl[0]-rl[0]
print('LC delta (operand-runtime)',delta, hex(0x89478-delta))
def lcmap(v): return v+0x1F5670 if v<0x89478 else v-delta
print('reset sim',sim_reset[:6],'real',reset[:6])
print('reset match', reset==[(k,v) for k,v in sim_reset])
nt=frames[-1]-f0
bad=0; first_bad=None
for i in range(1,nt+1):
    f=f0+i
    m.out=[]; m.tick()
    sim=[(k,lcmap(v) if k.startswith('LC') and v!=0 else v) for k,v in m.out]
    rl=byf.get(f,[])
    if sim!=rl:
        bad+=1
        if first_bad is None:
            first_bad=(i,f,sim,rl)
print('ticks compared',nt,'mismatching ticks',bad)
if first_bad:
    i,f,sim,rl=first_bad; print('first mismatch tick',i,'frame',f); print(' sim ',sim); print(' real',rl)
