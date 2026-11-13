import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
mach,mem,tos=sys.argv[1],int(sys.argv[2]),sys.argv[3]
st=Path("/tmp/diag9.st"); shutil.copy(G/"build/Pop2ReleaseF/Populous2_boot.st",st)
h=Populous2(game_dir=G/"build/Pop2ReleaseF",files=[],autorun="",machine=mach,tos=TOS[tos],memsize_kb=mem,extra=["--disk-a",str(st)]+(["--mmu","true"] if mach=="tt" else []))
try:
    time.sleep(14)
    # break at RUNME's Fopen("HAGA") time is too early; take the state at the P2D Fopen
    f=h.R/"a.txt"; f.write_text("".join(f"m ${x} {n}\n" for x,n in (r.split(":") for r in sys.argv[4:])))
    h.cmd(f"hatari-debug b pc = $3f9020 :trace :once :file {f}"); time.sleep(0.5)
    for i in range(14):
        h.key("space",0.6); time.sleep(5)
        if "Removed CPU breakpoint" in h._logtext(): break
    time.sleep(2)
    lg=h._logtext(); i=lg.find("> m")
    i=lg.find("> m"); print(lg[i:i+3500])
finally: h.close()
