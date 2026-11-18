from cl import *
import json,collections
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 2.adf'])
with Session(m) as s:
    s.load_state(OUT+'st_n5.clstate')
    s.joy(port=2,up=True); s.run_for(5)
    s.mmio(0xdff000,0x200,'write')
    rows=[]
    t0=s.now(); T=t0+4
    while s.now()<T:
        r=s.run_to(T)
        if r.get('reason')=='mmio':
            a=r['access']; p=a['position']; rows.append((p['frame'],a['pc'],a['addr']-0xdff000,a['size'],a['value']))
    c=collections.Counter(x[2] for x in rows)
    names={0x40:'BLTCON0',0x42:'BLTCON1',0x58:'BLTSIZE',0x80:'COP1LCH',0x82:'COP1LCL',0x88:'COPJMP1',0x96:'DMACON',0x100:'BPLCON0',0xe0:'BPL1PTH',0xe2:'BPL1PTL',0x9a:'INTENA',0x9c:'INTREQ',0x180:'COLOR00',0x8e:'DIWSTRT',0x90:'DIWSTOP',0x92:'DDFSTRT',0x94:'DDFSTOP'}
    print('events',len(rows),'in',4,'s; frames',rows[0][0],rows[-1][0])
    for k,v in c.most_common(30): print(hex(k),names.get(k,''),v)
    json.dump(rows[:20000],open(OUT+'hw_rows.json','w'))
