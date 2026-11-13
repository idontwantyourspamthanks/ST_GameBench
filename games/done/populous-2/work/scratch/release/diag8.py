import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
mach,mem,tos=sys.argv[1],int(sys.argv[2]),sys.argv[3]; pokes=sys.argv[4:]
st=Path("/tmp/diag8.st"); shutil.copy(G/"build/Pop2ReleaseF/Populous2_boot.st",st)
h=Populous2(game_dir=G/"build/Pop2ReleaseF",files=[],autorun="",machine=mach,tos=TOS[tos],memsize_kb=mem,extra=["--disk-a",str(st)]+(["--mmu","true"] if mach=="tt" else []))
try:
    time.sleep(14)
    fa=h.R/"a.txt"; fa.write_text("m $fffa07 1\nm $fffa09 1\nm $fffa13 1\nm $fffa15 1\nm $fffa17 1\nm $fffa1d 1\nm $fffa23 1\n"+"".join(p.replace("_"," ")+"\n" for p in pokes)+"m $fffa09 1\nm $fffa15 1\n")
    fb=h.R/"b.txt"; fb.write_text("r\n")
    h.cmd(f"hatari-debug b pc = $3f9020 :trace :once :file {fa}"); time.sleep(0.5)
    h.cmd(f"hatari-debug b pc = $3f9024 :trace :once :file {fb}"); time.sleep(0.5)
    for i in range(14):
        h.key("space",0.6); time.sleep(5)
        if "> r" in h._logtext(): break
    time.sleep(2)
    lg=h._logtext(); i=lg.find("> m $fffa07"); print(lg[i:i+1800])
finally: h.close()
