from cl import *
import json,random
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 2.adf'])
calls=[]
with Session(m) as s:
    s.load_state(OUT+'st_n5.clstate')
    bid=s.break_pc(0x7b70)
    t0=s.now(); T=t0
    s.joy(port=2,up=True)
    phases=[('up',dict(up=True)),('upL',dict(up=True,left=True)),('upR',dict(up=True,right=True)),('upF',dict(up=True,fire=True)),('down',dict(down=True)),('upLF',dict(up=True,left=True,fire=True)),('upRF',dict(up=True,right=True,fire=True))]
    end=t0+120; k=0
    while s.now()<end:
        name,d=phases[(k//1)%len(phases)]; k+=1
        s.joy(port=2,**d)
        tt=s.now()+5
        while s.now()<tt:
            r=s.run_to(tt)
            if r.get('reason')=='break' or r.get('reason')=='pc' or 'break' in str(r.get('reason')):
                rg=s.regs(); a7=rg['a'][7]
                ret=s.read_l(a7)
                calls.append((round(s.now(),3),name,rg['d'][0]&0xffff,rg['d'][1]&0xffff,hex(ret)))
            else:
                break
    json.dump(calls,open(OUT+'calls_race2.json','w'))
    s.shot(OUT+'race2_end.png')
    print(len(calls)); print(calls[:40])
