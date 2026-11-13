import sys
from lib import *
build,mach,tag=sys.argv[1:4]
mem=int(sys.argv[4]) if len(sys.argv)>4 else 4096
extra=["--mmu","true"] if mach=="tt" else []
h=Populous2(game_dir=build, machine=mach, memsize_kb=mem, extra=extra)
OFF=(0,0)
if mach=="falcon": OFF=(2,64)
def st(name,P,**k): return stage(h,f"{tag}_{name}",P,off=OFF,**k)
try:
    t0=time.time()
    print("boot_to_menu",h.boot_to_menu(),f"{time.time()-t0:.0f}s",flush=True); time.sleep(2)
    st("1menu",(100,100))
    h._click(384,257,3) if False else None
    h.goto(384,257,home_xy=(0,0)) if False else None
    # conquest -> deity screen (same clicks as boot_to_game, coordinates are in the 832x588 SD screenshot frame used by HOME=(96,58))
    from populous2 import HOME
    def click_st(x,y,wait=3.0):   # ST coords
        goto_st(h,x,y); time.sleep(0.3); h.click(hold=0.4); time.sleep(wait)
    click_st(144,100,3)           # CONQUEST GAME (menu text row ~ ST y 100)
    st("2deity",(200,150),still=6,moving=6)
    click_st(82,20,1.0)           # name field
    for ch in "zeus":
        h.key(ch,0.3); time.sleep(0.4)
    h.key("Return",0.3); time.sleep(1)
    click_st(164,180,3)           # PROCEED
    st("3menu2",(100,100),still=4,moving=4)
    click_st(144,100,8)           # CONQUEST -> battle sheet
    st("4sheet",(200,120),still=12,moving=12)
    click_st(60,195,12)           # PROCEED: loads
    st("5manualq",(200,150),still=6,moving=6)
    click_st(152,181,15)          # OK
    print("in_play",h.in_play(),flush=True)
    st("6map",(160,90),still=12,moving=12)
    st("7panel",(60,170),still=12,moving=12,mov=[(30+i*20,165+(i%3)*10) for i in range(12)])
    click_st(301,156,3)           # game requester
    st("8requester",(160,100),still=8,moving=8)
finally:
    h.close()
