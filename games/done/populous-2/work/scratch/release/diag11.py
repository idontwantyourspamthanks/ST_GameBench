import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
mach,tos=sys.argv[1],sys.argv[2]
st=Path("/tmp/diag11.st"); shutil.copy(G/"build/Pop2ReleaseF2/Populous2_boot.st",st)
h=Populous2(game_dir=G/"build/Pop2ReleaseF2",files=[],autorun="",machine=mach,tos=TOS[tos],memsize_kb=4096,extra=["--disk-a",str(st),"--trace","gemdos,bios,fdc"]+(["--mmu","true"] if mach=="tt" else []))
try:
    time.sleep(14)
    for i in range(14):
        h.key("space",0.6); time.sleep(5)
        if 'Fopen("P2D"' in h._logtext(): time.sleep(8); break
    lg=h._logtext().splitlines()
    ks=[i for i,l in enumerate(lg) if 'Fopen("P2D"' in l]
    k=ks[-1] if ks else len(lg)-60
    print("\n".join(l for l in lg[max(0,k-40):k+70] if not l.startswith('fdc')))
finally: h.close()
