import sys, time
from mm import *
name, medium, path = sys.argv[1], sys.argv[2], sys.argv[3]
tr = sys.argv[4]; secs=int(sys.argv[5])
h = start(name, medium, path, extra=["--trace", tr])
try:
    time.sleep(secs)
    print(mem(h,0x432,4), mem(h,0x436,4), mem(h,0x4a2,4))
    print(open(h.logpath).read()[-4000:])
finally:
    h.close()
