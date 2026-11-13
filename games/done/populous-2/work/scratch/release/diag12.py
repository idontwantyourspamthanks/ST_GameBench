import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
mach,tos=sys.argv[1],sys.argv[2]
st=Path("/tmp/diag12.st"); shutil.copy(G/"build/Pop2ReleaseF/Populous2_boot.st",st)
h=Populous2(game_dir=G/"build/Pop2ReleaseF",files=[],autorun="",machine=mach,tos=TOS[tos],memsize_kb=4096,extra=["--disk-a",str(st),"--trace","gemdos"])
try:
    time.sleep(14)
    fb=h.R/"b.txt"; fb.write_text("r\nm $15c0 64\n")
    for i in range(200):
        h.key("space",0.3); time.sleep(0.5)
        if 'Fclose(6) at PC 0xD1B4' in h._logtext(): break
    h.cmd(f"hatari-debug b pc = $e03f90 :trace :once :file {fb}"); time.sleep(25)
    lg=h._logtext(); i=lg.find("> r"); print(i); print(lg[i:i+2500] if i>=0 else "\n".join(lg.splitlines()[-15:]))
finally: h.close()
