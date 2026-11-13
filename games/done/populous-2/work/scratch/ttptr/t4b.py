import sys
from lib import *
build,mach,tag=sys.argv[1:4]
h=mk(build,mach)
try:
    print("menu",h.boot_to_menu(),flush=True); time.sleep(2)
    for P in ((13,5),(0,0),(100,2)):
        pointer_test(h,tag+f"_{P[0]}_{P[1]}",P=P,n=6,moving_n=0)
finally: h.close()
