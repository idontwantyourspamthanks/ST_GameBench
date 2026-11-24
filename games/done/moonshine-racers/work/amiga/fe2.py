from cl import *
import json,collections
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 1.adf'])
D2=B+'Moonshine Racers Disk 2.adf'
with Session(m) as s:
    s.load_state(OUT+'st_presskey.clstate')
    tr=Tracer(s)
    s.key(0x40); tr.run_to(202)
    s.type('x'); tr.run_to(202.3); s.key(0x44); tr.run_to(214)
    s.call('media.floppy.eject',drive=0); tr.run_to(215)
    s.call('media.floppy.insert',drive=0,path=D2); tr.run_to(216)
    s.key(0x40)
    t=216
    for k in range(60):
        tr.run_to(t+5); t+=5
        if k%2==1: s.key(0x40)
        s.shot(OUT+f'fe2_{k:02d}.png')
    tr.dump(OUT+'trace_fe2.jsonl')
    print('done',len(tr.rows))
