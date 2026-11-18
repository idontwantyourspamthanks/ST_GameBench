import sys,time,struct
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy')
from e160_lib import grab,T,W,L
from nebfloppy import NebFloppy
img,wd,mach,mem,tos=sys.argv[1:6]
h=NebFloppy(img,machine=mach,mem=int(mem),tos=tos,workdir=wd)
print('title',h.boot_to_title(timeout=300,space_at=25 if int(mem)>1024 else 20),flush=True)
t=T(h)
print('marker',grab(h,0x77ec0,4),'RS',grab(h,0x77c80,64).hex())
print('tosP',hex(L(h,0x77c80+52)),'n',W(h,0x77c80+56),'mfpP',hex(L(h,0x77c80+58)))
h.close()
