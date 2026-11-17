from cl import *
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 2.adf'])
with Session(m) as s:
    s.load_state(OUT+'st_n4.clstate')
    print(s.now())
    for k in range(1,17):
        s.key(0x40); s.run_for(4)
        s.key(0x44); s.run_for(4)
        s.shot(OUT+f'n5_{k:02d}.png'); print(k, round(s.now(),1), hex(s.regs()['pc']))
    s.save_state(OUT+'st_n5.clstate')
