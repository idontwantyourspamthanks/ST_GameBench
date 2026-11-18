import sys,json; sys.path.insert(0,'work/hud')
from hudlab import *
st=[(0x100e,2),(0x1226,2),(0x1024,2),(0x1020,2),(0x11ab,2),(0x11b1,2),(0x1030,2),(0x10ce,4)]
for cfg in ('stock','11ef0','11ef0+f90c','f90c'):
    names=[] if cfg=='stock' else cfg.split('+')
    r=run('race_idle',skip(*names),520,state=st,stages=False,timeout=1200)
    rows=[]
    for k in sorted(r.state,key=lambda k:0):
        pass
    seq=[(k,v(m,0x1226,1),v(m,0x1024,1),v(m,0x1021,1),v(m,0x11ab,1),v(m,0x11b1,1),v(m,0x1030,1),v(m,0x10ce,4)>>16) for k,m in r.state.items()]
    json.dump(seq,open(f'work/hud/res/flow_{cfg}.json','w'))
    print(cfg,len(seq),flush=True)
