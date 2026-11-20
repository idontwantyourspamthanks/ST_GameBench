import sys, time, os
sys.path.insert(0,'tools')
from msrfloppy import mk, peekb
a, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
h = mk(a)
try:
    n=0; last=0
    while n<60:
        time.sleep(1.2); v=h.vbl()
        if v<1900: continue
        h.shot(f"{out}/{n:02d}_vbl{v}.png"); print(n,v,peekb(h,0x1021),h.peekw(0x100e),flush=True); n+=1
        if time.time()-last>7: h.keypress(57); last=time.time()
finally:
    h.close()
