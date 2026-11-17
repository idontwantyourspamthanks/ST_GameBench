from cl import *
import json
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 2.adf'])
rows=[];calls=[]
with Session(m) as s:
    s.load_state(OUT+'st_n5.clstate')
    s.mmio(0xdff0d0,0x10,'write'); s.mmio(0xdff096,2,'write')
    bid=s.break_pc(0x7b70)
    phases=[dict(up=True),dict(up=True,left=True),dict(up=True,right=True),dict(up=True,fire=True),dict(down=True),dict(up=True,left=True,fire=True),dict(up=True,right=True,fire=True)]
    t0=s.now(); end=t0+130; k=0
    while s.now()<end:
        s.joy(port=2,**phases[k%len(phases)]); k+=1
        tt=min(s.now()+5,end)
        while s.now()<tt:
            r=s.run_to(tt)
            rs=r.get('reason')
            if rs=='mmio':
                a=r['access']; p=a['position']
                rows.append((round(p['seconds'],4),p['frame'],a['pc'],a['addr'],a['size'],a['value']))
            elif rs and 'mmio' not in rs and ('break' in rs or rs=='pc'):
                rg=s.regs(); calls.append((round(s.now(),4),rg['d'][0]&0xffff,rg['d'][1]&0xffff,s.read_l(rg['a'][7])))
            else: break
    json.dump(dict(rows=rows,calls=calls),open(OUT+'gear_trace.json','w'))
    print(len(rows),len(calls))
