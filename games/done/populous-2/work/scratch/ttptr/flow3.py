import sys
from lib import *
build,mach,tag=sys.argv[1:4]
mem=int(sys.argv[4]) if len(sys.argv)>4 else 4096
extra=["--mmu","true"] if mach=="tt" else []
h=Populous2(game_dir=build, machine=mach, memsize_kb=mem, extra=extra)
OFF=(0,0)
if mach=="falcon": OFF=(2,64)
def click_st(x,y,wait=3.0):
    goto_st(h,x,y); time.sleep(0.3); h.click(hold=0.4); time.sleep(wait)
def st(name,P,**k): return stage(h,f"{tag}_{name}",P,off=OFF,**k)
try:
    t0=time.time()
    print("boot_to_menu",h.boot_to_menu(),f"{time.time()-t0:.0f}s",flush=True); time.sleep(2)
    print("boot_to_game",h.boot_to_game(),flush=True)
    st("6map",(160,90),still=12,moving=12)
    st("7panel",(60,170),still=12,moving=12,mov=[(30+i*20,165+(i%3)*10) for i in range(12)])
    click_st(301,156,3)           # game requester
    st("8requester",(160,100),still=8,moving=8)
finally:
    h.close()
