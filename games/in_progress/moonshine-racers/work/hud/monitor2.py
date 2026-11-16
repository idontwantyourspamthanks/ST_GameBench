import sys,json; sys.path.insert(0,'work/hud')
from hudlab import *
st=[(0x100e,2),(0x11ab,2),(0x11b1,2),(0x1226,2),(0x1024,2),(0x10ce,4),(0x1030,2)]
cfg=sys.argv[1]
names=[] if cfg=='stock' else cfg.split('+')
r=run('race_start',skip(*names),1850,state=st,stages=False,timeout=1500)
seq=[(k,m.get(-1),v(m,0x1226,1),v(m,0x1024,1),v(m,0x11ab,1),v(m,0x11b1,1),v(m,0x10ce,4)>>16,v(m,0x1030,2)) for k,m in sorted(r.state.items(),key=lambda kv:kv[1].get(-1,0))]
json.dump(seq,open(f'work/hud/res/monitor2_{cfg}.json','w'))
print(cfg,len(seq),seq[-1],flush=True)
