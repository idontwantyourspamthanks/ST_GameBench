import sys
from lib import *
build,mach=sys.argv[1:3]
h=mk(build,mach)
try:
    print("menu",h.boot_to_menu(),flush=True); time.sleep(2)
    goto_st(h,100,100); time.sleep(1)
    f=h.shot(str(OUT/"t5.png")); im=Image.open(f).convert("RGB")
    (x,y,shp),px,pal=expected(h)
    print("ptr",x,y,shp,"npx",len(px),"pal",[hex(p) for p in pal])
    seen={}
    for (a,b,i) in px:
        seen.setdefault(i,{}); c=im.getpixel((a*2,b*2)); seen[i][c]=seen[i].get(c,0)+1
    print(seen)
finally: h.close()
