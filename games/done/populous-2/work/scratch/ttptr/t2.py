import sys
from lib import *
build,mach=sys.argv[1:3]
h=mk(build,mach)
try:
    print("menu",h.boot_to_menu(),flush=True); time.sleep(2)
    for a,n in ((0x2246,2),(0x202e,4),(0x11d50,2),(0x393fa,2),(0x393fc,2),(0x1c16,4),(0x86fa0,1),(0x392dc,4),(0x392e0,4),(0x2232,2),(0x2234,2)):
        print(hex(a), hex(h.peekl(a) if n==4 else h.peekw(a)))
    r=sample(h,"t2",3,False)
finally: h.close()
