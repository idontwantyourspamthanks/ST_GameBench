import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
mach,tos,mem,d=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
st=Path("/tmp/diag14.st"); shutil.copy(G/d/"Populous2_boot.st",st)
h=Populous2(game_dir=G/d,files=[],autorun="",machine=mach,tos=TOS[tos],memsize_kb=mem,extra=["--disk-a",str(st)]+(["--mmu","true"] if mach=="tt" else []))
try:
    time.sleep(12)
    fa=h.R/"a.txt"; fa.write_text("m $3f8080 48\nm $1f8080 48\nm $42e 8\nsavebin /tmp/live_%s.bin $0 $4000\nsavebin /tmp/top_%s.bin $3f8000 $8000\n"%(mach,mach))
    h.cmd(f"hatari-debug b pc = $3f9020 :trace :once :file {fa}"); time.sleep(0.5)
    for i in range(300):
        h.key("space",0.3); time.sleep(0.5)
        if "> savebin /tmp/top" in h._logtext(): break
    time.sleep(2)
    lg=h._logtext(); i=lg.find("> m $3f8080"); print(lg[i:i+1800])
finally: h.close()
