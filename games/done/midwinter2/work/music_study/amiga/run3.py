from trace import *
m=Machine(floppies=disks())
with Session(m) as s:
    s.run_to(14.0)
    s.mouse(left=True); s.run_to(17.0); s.mouse(left=False)
    for T in (62,70,80,100):
        s.run_to(T); print(T, hex(s.regs()['pc'])); s.shot(f'shots/r3_{T}.png')
    print([hex(x) for x in s.find(bytes.fromhex('48e7fefe4a79'),0x200000,0xa00000)])
