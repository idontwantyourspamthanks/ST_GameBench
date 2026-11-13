import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
d=sys.argv[1]; st=Path("/tmp/diag5.st"); shutil.copy(G/d/"Populous2_boot.st",st)
h=Populous2(game_dir=G/d,files=[],autorun="",machine=sys.argv[3],memsize_kb=int(sys.argv[2]),extra=["--disk-a",str(st),"--trace","gemdos"])
try:
    time.sleep(14)
    for i in range(16):
        h.key("space",0.6); time.sleep(5)
        lg=h._logtext()
        if "Bus Error" in lg: break
    print("--- tail"); print("\n".join(h._logtext().splitlines()[-8:]))
    try: print("$70 =",hex(h.peekl(0x70)), "turn", h.peekw(h.TURN))
    except Exception as e: print("peek fail",e)
    h.shot("/tmp/diag5.png")
finally: h.close()
