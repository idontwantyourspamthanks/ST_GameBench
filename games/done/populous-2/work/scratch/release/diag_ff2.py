import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
src=sys.argv[1]; st=Path("/tmp/diag_ff.st"); shutil.copy(G/src,st)
h=Populous2(game_dir=G/"build/Pop2ReleaseFzero",files=[],autorun="",machine="falcon",memsize_kb=4096,extra=["--disk-a",str(st),"--trace","gemdos"])
try:
    time.sleep(14)
    h.key("space",0.6); time.sleep(5)
    for i in range(4):
        h.key("space",0.6); time.sleep(5)
    lg=h._logtext().splitlines()
    n=len(lg)
    print("lines",n)
    for l in lg[-45:]: print(l)
    h.shot("/tmp/diag_ff2.png")
finally: h.close()
