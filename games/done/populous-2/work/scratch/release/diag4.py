import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
st=Path("/tmp/diag4.st"); shutil.copy(G/"build/Pop2ReleaseFzero/Populous2_boot.st",st)
h=Populous2(game_dir=G/"build/Pop2ReleaseFzero",files=[],autorun="",machine="falcon",memsize_kb=4096,extra=["--disk-a",str(st)])
try:
    time.sleep(14)
    f=h.R/"cmds.txt"; f.write_text("r\nsavebin /tmp/haga_top.bin $3f8000 $4000\nm $e09520 16\n")
    h.cmd("hatari-debug b pc = $3f94b8 :trace :once :file "+str(f)); time.sleep(0.5)
    for i in range(6):
        h.key("space",0.6); time.sleep(5)
    lg=h._logtext(); i=lg.find("matched")
    print(lg[i-200:i+1800])
finally: h.close()
