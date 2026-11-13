import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
media,mach,mem=sys.argv[1],sys.argv[2],int(sys.argv[3]); d=sys.argv[4]
kw=dict(machine=mach,memsize_kb=mem)
ex=["--trace","gemdos"]
if mach=="tt": ex+=["--mmu","true"]
if media=="hd": kw.update(game_dir=G/d)
else:
    st=Path("/tmp/diag3.st"); shutil.copy(G/d/"Populous2_boot.st",st); kw.update(game_dir=G/d,files=[],autorun=""); ex+=["--disk-a",str(st)]
h=Populous2(extra=ex,**kw)
try:
    time.sleep(14)
    for i in range(10):
        h.key("space",0.6); time.sleep(5)
    for l in h._logtext().splitlines():
        if re.search(r"Fopen|Fread|Pexec|Mshrink|Bus|Address|Fseek|Fclose|Fsfirst|Malloc|Pterm",l): print(l)
finally: h.close()
