from cl import *
import json,re,collections
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 2.adf'])
log=[]
with Session(m) as s:
    s.load_state(OUT+'st_n4.clstate')
    tr=Tracer(s)
    for k in range(1,15):
        s.key(0x40); tr.run_to(s.now()+4)
        s.key(0x44); n0=len(tr.rows); tr.run_to(s.now()+4)
        rows=tr.rows[-1500:]
        pcs=collections.Counter(hex(r[4]>>8) for r in tr.rows[n0:])
        # modules resident
        mods=[]
        data=b''.join(bytes(s.read(a,0x10000)) for a in range(0,0x100000,0x10000))
        for mm in re.finditer(b'M.K.',data):
            o=mm.start()-1080
            if o>=0: 
                t=data[o:o+20].split(b'\0')[0]
                if t.isascii() and len(t)>=2 and t.decode().isprintable(): mods.append((hex(o),t.decode()))
        s.shot(OUT+f'fe_{k:02d}.png')
        log.append((k,round(s.now(),1),len(tr.rows)-n0,dict(pcs.most_common(3)),mods))
        print(log[-1],flush=True)
