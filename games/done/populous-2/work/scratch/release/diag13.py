import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
mach,tos=sys.argv[1],sys.argv[2]
st=Path("/tmp/diag13.st"); shutil.copy(G/"build/Pop2ReleaseF/Populous2_boot.st",st)
h=Populous2(game_dir=G/"build/Pop2ReleaseF",files=[],autorun="",machine=mach,tos=TOS[tos],memsize_kb=4096,extra=["--disk-a",str(st),"--trace","gemdos"])
try:
    time.sleep(10)
    fb=h.R/"b.txt"; fb.write_text("r\nm $160c 2\n")
    h.cmd(f"hatari-debug b ($160c).w ! ($160c).w :trace :file {fb}"); time.sleep(0.5)
    for i in range(300):
        h.key("space",0.3); time.sleep(0.5)
        if 'Fopen("P2D"' in h._logtext(): break
    time.sleep(3)
    lg=h._logtext()
    L=lg.splitlines(); idx=[i for i,l in enumerate(L) if l.startswith("  $160c =")]
    print(len(idx),"hits")
    for i in idx[-6:]: print("\n".join(x[:110] for x in L[i:i+16])); print("-----")
finally: h.close()
