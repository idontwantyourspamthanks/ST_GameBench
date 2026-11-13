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
    f=h.R/"a.txt"; f.write_text("m $432 8\nm $4b2 8\nm $4c2 4\nm $4c6 4\nm $4a6 2\nm $4a2 4\nm $4a4 4\nm $4be 2\nm $4d6 4\nm $4f6 4\nm $4fa 4\nm $4fe 4\nm $502 4\nm $506 4\nm $4ee 4\nm $4e6 4\nm $4ca 4\nm $4cc 4\nm $4c8 4\nm $4de 4\nm $4ea 4\n")
    h.cmd(f"hatari-debug b pc = $3f9020 :trace :once :file {f}"); time.sleep(0.5)
    for i in range(14):
        h.key("space",0.6); time.sleep(5)
        if "Removed CPU breakpoint" in h._logtext(): break
    time.sleep(2)
    lg=h._logtext(); i=lg.find("> m $432")
    print("\n".join(l for l in lg[i:i+3000].splitlines() if l.startswith(("> m","0000"))))
    # follow _bufl pointers
    def L(a): 
        o=h.debug(f"m ${a:x} 4",0.5); m=re.findall(rf"{a:08x}:\s+([0-9a-f]{{2}}) ([0-9a-f]{{2}}) ([0-9a-f]{{2}}) ([0-9a-f]{{2}})",o,re.I)[-1]; return int("".join(m),16)
    for nm,a in (("_bufl[0]",0x4b2),("_bufl[1]",0x4b6)):
        p=L(a); print(nm,hex(p)); 
        n=0
        while p and p<0x400000 and n<12:
            print("   buflist node",hex(p),"->",hex(L(p)), "(+4:",hex(L(p+4)),"+8:",hex(L(p+8)),"+C:",hex(L(p+0xc)),")"); p=L(p); n+=1
finally: h.close()
