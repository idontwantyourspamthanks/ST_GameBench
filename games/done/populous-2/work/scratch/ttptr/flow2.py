import sys
from lib import *
build,mach,tag=sys.argv[1:4]
mem=4096
extra=["--mmu","true"] if mach=="tt" else []
h=Populous2(game_dir=build, machine=mach, memsize_kb=mem, extra=extra)
OFF=(2,64) if mach=="falcon" else (0,0)
try:
    print("boot_to_game",h.boot_to_game(),flush=True)
    for nm,P in (("panel",(60,170)),("map",(160,90)),("top",(100,3))):
        stage_fast(h,f"{tag}_{nm}",P,n=int(sys.argv[4]) if len(sys.argv)>4 else 40,off=OFF)
finally: h.close()
