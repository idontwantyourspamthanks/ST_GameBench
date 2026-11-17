from cl import *
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 2.adf'])
with Session(m) as s:
    s.load_state(OUT+'st_n5.clstate')
    data=b''
    for a in range(0,0x100000,0x10000): data+=bytes(s.read(a,0x10000))
    open(OUT+'ram_race_a.bin','wb').write(data)
    s.shot(OUT+'race_a.png')
    t=Tracer(s)
    t0=s.now()
    t.run_to(t0+8); print('idle',len(t.rows))
    s.joy(port=2,up=True); t.run_to(t0+16); print('up',len(t.rows))
    s.shot(OUT+'race_b.png')
    s.joy(port=2,up=True,left=True); t.run_to(t0+22); print('upleft',len(t.rows))
    s.joy(port=2,up=True,right=True); t.run_to(t0+28); print('upright',len(t.rows))
    s.joy(port=2,up=True,fire=True); t.run_to(t0+34); print('upfire',len(t.rows))
    s.joy(port=2,down=True); t.run_to(t0+40); print('down',len(t.rows))
    s.joy(port=2); t.run_to(t0+44)
    s.shot(OUT+'race_c.png')
    t.dump(OUT+'trace_race1.jsonl')
    data=b''
    for a in range(0,0x100000,0x10000): data+=bytes(s.read(a,0x10000))
    open(OUT+'ram_race_b.bin','wb').write(data)
    print(t0)
