import sys; sys.path.insert(0,'/tmp/p5')
from lib import *
def run(label, live, dx=-150):
    h=Hatari(snapshot=SNAP)
    try:
        if live: apply_live(h, live)
        time.sleep(2)
        start_log(h)
        time.sleep(1.5)
        h.rel(dx,0)
        t0=time.time()
        time.sleep(6)
        rows=stop_log(h)
        print('==',label,'dx',dx)
        prev=None
        for r in rows:
            hd=r.get(0x6742); 
            if hd is None: continue
            print(f" vbl {r['vbl']} heading {hd:4d} $6766={sgn(r.get(0x6766,0))} $6fb6hi={sgn(r.get(0x6fb6,0))}")
    finally:
        h.close()
run(sys.argv[1], sys.argv[2] if sys.argv[2]!="none" else None, int(sys.argv[3]))
