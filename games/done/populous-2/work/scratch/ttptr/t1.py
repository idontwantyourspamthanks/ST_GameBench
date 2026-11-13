import sys
from lib import *
build,mach,tag=sys.argv[1:4]
h=mk(build,mach)
try:
    print("menu",h.boot_to_menu(),flush=True)
    time.sleep(2)
    r=sample(h,tag+"_still",8,False); r+=sample(h,tag+"_mov",12,True)
    analyse(r,tag, (0,0) if mach=="tt" else (0,0))
    print("VBL/flip", h.fps(250))
finally: h.close()
