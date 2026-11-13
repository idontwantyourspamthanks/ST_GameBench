import sys,time,shutil,re
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2, HOME
d=sys.argv[1]; mach=sys.argv[2]; mem=int(sys.argv[3]); tag=sys.argv[4]
st=Path(f"/tmp/diag6_{tag}.st"); shutil.copy(G/d/"Populous2_boot.st",st)
h=Populous2(game_dir=G/d,files=[],autorun="",machine=mach,memsize_kb=mem,extra=["--disk-a",str(st)])
S=G/"work/shots"
def st_():
    try: return f"$70={h.peekl(0x70):#x} turn={h.peekw(h.TURN)} PC? marker={h.marker()}"
    except Exception as e: return "peek fail"
try:
    print("menu",h.boot_to_menu(), st_()); h.shot(str(S/f"d6_{tag}_menu.png"))
    h._click(384,257,3); h._click(260,98,1.0)
    for ch in "zeus": h.key(ch,0.3); time.sleep(0.4)
    h.key("Return",0.3); time.sleep(1); h._click(424,418,3); print("after deity",st_()); h.shot(str(S/f"d6_{tag}_a.png"))
    h._click(384,258,8); print("after conquest",st_()); h.shot(str(S/f"d6_{tag}_b.png"))
    h._click(216,448,12); print("after proceed",st_()); h.shot(str(S/f"d6_{tag}_c.png"))
    time.sleep(20); print("20s later",st_()); h.shot(str(S/f"d6_{tag}_d.png"))
    h._click(400,420,15); print("after OK",st_()); h.shot(str(S/f"d6_{tag}_e.png"))
    time.sleep(30); print("30s later",st_()); h.shot(str(S/f"d6_{tag}_f.png"))
    print("\n".join(l for l in h._logtext().splitlines() if re.search("Bus|Address",l)))
finally: h.close()
