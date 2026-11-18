from cl import *
m=machine()
with Session(m) as s:
    s.run_to(190)
    s.save_state(OUT+'st_presskey.clstate')
    s.key(0x40); 
    for T in range(195,260,6):
        s.run_to(T)
        s.shot(OUT+f'n2_{T:03d}.png')
        print(T, hex(s.regs()['pc']))
