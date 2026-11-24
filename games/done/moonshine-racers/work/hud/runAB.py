import sys,json; sys.path.insert(0,'work/hud')
from hudlab import *
from vars import *
shots=[0x70+i for i in range(8)]+[0xa0+i for i in range(8)]
r=run('race_start',{},135,state=None,stages=False,shots_at=shots,shotdir=OUT/'res'/'shots_series')
print('A done',flush=True)
# B: turbo key held (space = $6037) without / with a turbo unit ($176ae), applied at pass 0x6e
w2=lambda x:x.to_bytes(2,'big')
V3=[('100e',2),('10c0',2),('10d8',4),('11c2',2),('176ae',2),('6037',1),('11ab',1),('11b1',1),('10ba',2),('130c',2),('5ff8',2)]
st=[(0x1000,1024),(0x6030,16),(0x176a0,32)]
for tag,pk in (('turbo_keyonly',{0x6037:b'\xff'}),('turbo_unit',{0x6037:b'\xff',0x176ae:w2(0x100)}),('baseline',{})):
    r=run('race_start',pk,60,state=st,stages=False,at_pass=0x6e,shots_at=[0x80,0xa0],shotdir=OUT/'res'/f'shots_{tag}')
    out=[]
    for k in sorted(r.state):
        m=r.state[k]; out.append({n:v(m,int(a,16),sz) for a,(n,sz) in zip([x[0] for x in V3],[(x[0],x[1]) for x in V3])})
    json.dump({str(k):{f"{a}":v(m,int(a,16),sz) for a,sz in V3} for k,m in r.state.items()},open(OUT/'res'/f'{tag}.json','w'))
    print(tag,len(r.state),flush=True)
