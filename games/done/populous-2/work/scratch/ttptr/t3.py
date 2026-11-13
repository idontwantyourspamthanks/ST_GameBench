import sys
from lib import *
build,mach=sys.argv[1:3]
h=mk(build,mach)
try:
    print("menu",h.boot_to_menu(),flush=True); time.sleep(2)
    h.rel(40,20,4); time.sleep(1)
    print("ptr",h.peekw(0x393fa),h.peekw(0x393fc),"202e",hex(h.peekl(0x202e)), "dc",hex(h.peekl(0x392dc)),"e0",hex(h.peekl(0x392e0)))
    for b in (0x2300,0xa000):
        f=OUT/f"buf_{b:x}.bin"; f.unlink(missing_ok=True)
        h.debug(f"savebin {f} ${b:x} 32000",1.5)
    h.debug("info video",1.0)
    print(h._logtext()[-600:])
    p=h.shot(str(OUT/"t3.png"))
finally: h.close()
