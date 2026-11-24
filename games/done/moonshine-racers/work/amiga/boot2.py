import sys
sys.path.insert(0,'/home/ryan/Code/Amiga/gamebench/tools')
import os
os.chdir('/home/ryan/Code/Amiga/gamebench')
from clharness import Machine, Session
B='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/alt/amiga/'
OUT='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/amiga/'
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 1.adf'])
with Session(m) as s:
    for t in (10,20,40,60):
        s.run_to(t)
        s.shot(OUT+f'd1_{t:03d}.png')
        r=s.regs(); print(t, hex(r['pc']), s.frame())
