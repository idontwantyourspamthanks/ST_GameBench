import sys; sys.path.insert(0,'work/sprite')
import kb, unit
e=kb.pick(7,2)
cs=[(0x122e8,0,0,1,4,0x30000),(kb.FULL[(7,2)],100,80,16,4,e['ptr'])]
f=kb.build(cs,'ms')
tl,res,_=unit.run(kb.HERE/'kb.s','work/snapshots/megaste4m_race_start.sav','megaste',4096,None,['r','c0ff0:4','d9000:12'],None,bins=[f'd0000:{f}'],timeout=40,trig=0x7b86)
print(tl)
for k,v in res.items():
    if k!='__log__': print(v)
print(res['__log__'][:3000])
