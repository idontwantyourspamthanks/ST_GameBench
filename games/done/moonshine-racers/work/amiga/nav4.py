from cl import *
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 1.adf'])
D2=B+'Moonshine Racers Disk 2.adf'; D1=B+'Moonshine Racers Disk 1.adf'
with Session(m) as s:
    s.run_to(190)
    s.key(0x40); s.run_to(202)
    s.type('x'); s.run_for(0.3); s.key(0x44)
    s.run_to(214)
    s.call('media.floppy.eject',drive=0); s.run_for(1.0)
    s.call('media.floppy.insert',drive=0,path=D2); s.run_for(1.0)
    s.key(0x40)
    for k in range(1,9):
        s.run_for(8)
        s.shot(OUT+f'n4_{k:02d}.png'); print(k, round(s.now(),1), hex(s.regs()['pc']))
    s.save_state(OUT+'st_n4.clstate')
