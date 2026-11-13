import sys, time, subprocess
from mm import *
name, medium, path = sys.argv[1], sys.argv[2], sys.argv[3]
secs=int(sys.argv[4]); extra = sys.argv[5].split()
keys = sys.argv[6] if len(sys.argv)>6 else ""
h = start(name, medium, path, extra=extra)
try:
    t0=time.time()
    for k in keys.split(","):
        if k:
            t,key=k.split(":"); time.sleep(max(0,int(t)-(time.time()-t0))); h.key(key,0.5)
    time.sleep(max(0,secs-(time.time()-t0)))
    try: h.shot("/tmp/pm5_last.png")
    except Exception as e: print("shot fail")
    print(open(h.logpath).read()[-int(5000):])
finally:
    h.close()
