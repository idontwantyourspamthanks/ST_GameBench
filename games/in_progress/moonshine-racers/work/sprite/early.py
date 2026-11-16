import sys; sys.path.insert(0,'work/sprite')
import kb, unit, re, struct
e1=kb.pick(7,1); e4=kb.pick(7,4)
cs=[(0x122e8,0,0,1,6,0x30000)]; meta=['calib']
for nm,(k,x,y,rows,a1) in {
 'c1 rows=0':(kb.FULL[(7,1)],100,80,0,e1['ptr']),'c1 x offscreen right':(kb.FULL[(7,1)],330,80,10,e1['ptr']),'c1 y>=200':(kb.FULL[(7,1)],100,205,10,e1['ptr']),
 'c4 rows=0':(kb.FULL[(7,4)],100,80,0,e4['ptr']),'c4 x offscreen left':(kb.FULL[(7,4)],-80,80,10,e4['ptr']),'c4 x offscreen right':(kb.FULL[(7,4)],330,80,10,e4['ptr']),'c4 y>=200':(kb.FULL[(7,4)],100,205,10,e4['ptr'])}.items():
    cs.append((k,x,y,rows,6,a1)); meta.append(nm)
f=kb.build(cs,'early'); tl,res,_=unit.run(kb.HERE/'kb.s','race_start','ste',1024,None,[],None,bins=[f'd0000:{f}'],timeout=120)
cyc=[];mc=None
for n,c in tl:
    if n=='m_case': mc=c
    elif n=='m_end' and mc is not None: cyc.append((c-mc)&0xffffffff); mc=None
b=cyc[0]/6
for m,c in zip(meta,cyc): print(f"{m:24s} {c/6-b:8.0f} cycles per call")
