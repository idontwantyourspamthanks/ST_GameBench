import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
mach,mem,tos,bp=sys.argv[1],int(sys.argv[2]),sys.argv[3],sys.argv[4]
st=Path("/tmp/diag7.st"); shutil.copy(G/"build/Pop2ReleaseF/Populous2_boot.st",st)
h=Populous2(game_dir=G/"build/Pop2ReleaseF",files=[],autorun="",machine=mach,tos=TOS[tos],memsize_kb=mem,extra=["--disk-a",str(st)])
try:
    time.sleep(14)
    f=h.R/"cmds.txt"; f.write_text("m $4ba 4\nm $fffa07 16\nm $114 4\nm $70 4\nm $454 8\nm $43e 2\nm $4a6 2\nm $4c6 4\nm $440 2\n")
    h.cmd(f"hatari-debug b pc = {bp} :trace :once :file "+str(f)); time.sleep(0.5)
    for i in range(14):
        h.key("space",0.6); time.sleep(5)
        if "matched" in h._logtext(): break
    lg=h._logtext(); i=lg.find("> m $4ba"); i=lg.find('> m $4ba'); print(lg[i:i+1500]); time.sleep(2); print('LATER'); print(h.debug('m $4ba 4',0.6)); print(h.debug('m $fffa07 16',0.6))
finally: h.close()
