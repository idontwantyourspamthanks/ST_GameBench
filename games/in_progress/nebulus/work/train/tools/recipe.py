import sys
from nt import *
mode=sys.argv[1]
h=Nebulus(workdir='/tmp/strun-nt1')
try:
    if mode in ('lead','leadd'):
        h.boot_to_game()
    else:
        t0=time.time()
        while time.time()-t0<90:
            time.sleep(2)
            out=h.debug("m $3d00f 4",0.5)
            if re.search(r'3D00F:\s+48 69 67 68',out,re.I): break
            h.keypress(57)
        print('marker after',round(time.time()-t0,1),'s')
        time.sleep(2)
    if mode=='lead_dbg':
        pass
    if mode=='leadd':
        h.debug("m $3d00f 4",0.5)
    print('pre', h.debug("m $38498 4",0.5)[-80:])
    h.key('Right',hold=0.5); time.sleep(0.5)
    h.key('Control_R',hold=1.0); time.sleep(4)
    h.shot(T+f'shots/rec_{mode}.png')
    print('t d0 vars',h.debug("m $3390c 2",0.5)[-60:], h.debug("m $3ad98 6",0.5)[-60:])
finally:
    h.close()
