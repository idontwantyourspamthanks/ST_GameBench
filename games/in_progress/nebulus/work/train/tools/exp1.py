import sys
from nt import *
def run(label, pokes, pre=3.0, dur=24.0, step=2.0):
    h=snapshot_open(workdir='/tmp/strun-nt2')
    out=[]
    try:
        time.sleep(pre)
        for p in pokes:
            h.debug(p,0.5)
        t0=time.time(); i=0
        while time.time()-t0<dur:
            v=h.vbl()
            tm=words(grab(h,0x3ad98,6,'t'))
            st=words(grab(h,0x3398c,8,'s'))
            ent=words(grab(h,0x33944,12,'x'))
            print(label,i,'vbl',v,'timer words',tm,'states',st,'X',ent,flush=True)
            if i%2==0: h.shot(T+f'shots/{label}_{i:02d}.png')
            i+=1; time.sleep(step)
    finally:
        h.close()
label=sys.argv[1]
pokes={'A':[], 'B':['w $3b0aa $60'], 'C':['w $3792c $4e $75','w $3398c 0 0 0 0 0 0 0 0']}[label]
run(label,pokes)
