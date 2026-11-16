import sys, json
sys.path.insert(0,'/home/ryan/Code/Amiga/gamebench/tools')
from clharness import *
from pathlib import Path
O=Path('/home/ryan/Code/Amiga/gamebench/games/in_progress/Midwinter-2/originals')
d=[next(O.glob(f"*Disk {i} of 3*SPL*.adf")) for i in (1,2,3)]
m=Machine(floppies=d)
with Session(m) as s:
    print(s.status())
    s.run_to(5)
    print(s.status())
    b=s.mmio(0xdff0a0,0x40,'write')
    r=s.run_to(30)
    print(r)
    print(s.events[:5])
    print(s.regs())
