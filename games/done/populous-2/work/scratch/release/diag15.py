import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
import p2tick as TK
media,mach,d=sys.argv[1:4]
kw=dict(machine=mach,memsize_kb=4096); ex=["--mmu","true"] if mach=="tt" else []
if media=="hd": kw.update(game_dir=G/d)
else:
    st=Path("/tmp/diag15.st"); shutil.copy(G/d/"Populous2_boot.st",st); kw.update(game_dir=G/d,files=[],autorun=""); ex+=["--disk-a",str(st)]
h=Populous2(extra=ex,**kw)
try:
    print("menu",h.boot_to_menu())
    for a in (0xff8260,0xff8262,0xff8240,0xff8400,0xff820a,0xff8201,0xff8203):
        print(hex(a), TK.rdb(h,a,4).hex())
    print("$70",hex(h.peekl(0x70)),"turn",h.peekw(h.TURN))
    time.sleep(20)
    for i in range(4):
        o=h.debug("r",0.6); m=re.search(r"\n([0-9a-f]{8}) ([0-9a-f]{4})[^\n]*\n",o[o.find("SR="):]); print("PC line:", re.findall(r"\n([0-9a-f]{8}) [0-9a-f]{4}[^\n]*",o)[-1:] , "SR", re.findall(r"SR=(\w+)",o)); time.sleep(1)
    print("palette",TK.rdb(h,0xff8240,4).hex(),"turn",h.peekw(h.TURN))
    h.shot(str(G/f"work/shots/rel_d15_{media}_{mach}.png"))
finally: h.close()
