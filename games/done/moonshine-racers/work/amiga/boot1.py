import sys
sys.path.insert(0,'/home/ryan/Code/Amiga/gamebench/tools')
import os
os.chdir('/home/ryan/Code/Amiga/gamebench')
from clharness import Machine, Session
ADF='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/alt/amiga/Moonshine Racers (PeakStar + Millennium) A.adf'
OUT='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/amiga/'
m=Machine(model="A500", fast=None, chip="1M", floppies=[ADF])
print(m.toml())
with Session(m) as s:
    for t in (3,6,10,15,20,30,45):
        s.run_to(t)
        s.shot(OUT+f'boot_{t:03d}.png')
        r=s.regs(); print(t, hex(r['pc']), s.frame())
