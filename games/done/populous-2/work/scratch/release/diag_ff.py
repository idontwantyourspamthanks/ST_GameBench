import sys,time,shutil
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
src=sys.argv[1]; st=Path("/tmp/diag_ff.st"); shutil.copy(G/src,st)
h=Populous2(game_dir=G/"build/Pop2ReleaseFzero",files=[],autorun="",machine="falcon",memsize_kb=4096,extra=["--disk-a",str(st),"--trace","gemdos,exception_all" if False else "gemdos"])
try:
    time.sleep(25)
    for l in h._logtext().splitlines()[:60]: print(l)
    h.shot("/tmp/diag_ff.png")
finally: h.close()
