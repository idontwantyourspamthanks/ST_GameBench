import sys, time, os, re
sys.path.insert(0,'tools')
from msrfloppy import mk
a, out = sys.argv[1], sys.argv[2]
h = mk(a, trace="fdc")
try:
    last=0
    while True:
        time.sleep(1.2); v=h.vbl()
        if v>3400: break
        if v>1900 and time.time()-last>7: h.keypress(57); last=time.time()
    open(out,'w').write(h._logtext())
finally:
    h.close()
