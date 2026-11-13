import sys
from lib import *
build,mach,tag=sys.argv[1:4]
h=mk(build,mach)
try:
    print("menu",h.boot_to_menu(),flush=True); time.sleep(2)
    pointer_test(h,tag)
finally: h.close()
