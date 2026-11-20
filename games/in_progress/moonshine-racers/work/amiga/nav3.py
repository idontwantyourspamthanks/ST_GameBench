from cl import *
m=machine()
with Session(m) as s:
    s.load_state(OUT+'st_presskey.clstate')
    t0=s.now(); print('t0',t0)
    s.key(0x40)
    s.run_to(t0+12)
    s.type('x'); s.run_for(0.3); s.key(0x44)
    for k in range(1,12):
        s.run_for(8)
        s.shot(OUT+f'n3_{k:02d}.png'); print(k, round(s.now(),1), hex(s.regs()['pc']))
    s.save_state(OUT+'st_after_manual.clstate')
