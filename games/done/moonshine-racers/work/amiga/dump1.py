import sys
sys.path.insert(0,'/home/ryan/Code/Amiga/gamebench/tools')
import os
os.chdir('/home/ryan/Code/Amiga/gamebench')
from clharness import Machine, Session
B='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/alt/amiga/'
OUT='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/amiga/'
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 1.adf'])
with Session(m) as s:
    s.run_to(60)
    data=b''
    for a in range(0,0x100000,0x10000):
        data+=bytes(s.read(a,0x10000))
    open(OUT+'ram_d1_60s.bin','wb').write(data)
    print(len(data), s.regs())
    print([x for x in dir(s) if not x.startswith('_')])
