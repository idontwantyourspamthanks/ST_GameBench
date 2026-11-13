import sys
from lib import *
build,mach,tag=sys.argv[1:4]
h=Populous2(game_dir=build,machine=mach,memsize_kb=4096,extra=(["--mmu","true"] if mach=="tt" else []))
OFF=(2,64) if mach=="falcon" else (0,0)
def click_st(x,y,wait=3.0):
    goto_st(h,x,y); time.sleep(0.3); h.click(hold=0.4); time.sleep(wait)
try:
    print("menu",h.boot_to_menu(),flush=True); time.sleep(2)
    click_st(144,91,4)      # CREATE YOUR DEITY
    h.shot(str(OUT/f"{tag}_deity_raw.png"))
    stage(h,f"{tag}_deity",(200,150),still=8,moving=8,off=OFF)
finally: h.close()
