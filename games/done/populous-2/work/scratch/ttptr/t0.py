import sys, time
G="/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2"
sys.path[:0]=[G+"/tools","/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
build, mach = sys.argv[1], sys.argv[2]
extra=["--mmu","true"] if mach=="tt" else []
mem = 4096
h=Populous2(game_dir=build, machine=mach, memsize_kb=mem, extra=extra)
try:
    ok=h.boot_to_menu()
    print("menu",ok, h.peekw(0x393fa), h.peekw(0x393fc), flush=True)
    for i in range(3):
        p=h.shot(G+f"/work/scratch/ttptr/t0_{mach}_{i}.png"); print(p); time.sleep(1.5)
finally:
    h.close()
