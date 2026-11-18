import sys
from nt import *
mode=sys.argv[1]
h=Nebulus(workdir='/tmp/strun-nt1')
try:
    if mode=='nospace':
        time.sleep(16); h.keypress(57); time.sleep(24)   # one space for HW screen
    elif mode=='fire_only':
        t0=time.time()
        while time.time()-t0<90:
            time.sleep(2)
            out=h.debug("m $3d00f 4",0.5)
            if re.search(r'3D00F:\s+48 69 67 68',out,re.I): break
            h.keypress(57)
        print('marker after',round(time.time()-t0,1),'s')
        time.sleep(2)
    print('pre', h.vbl(), h.debug("m $3d00f 4",0.5)[-70:])
    if mode!='fire_only': h.key('Right',hold=0.5); time.sleep(0.5)
    h.key('Control_R',hold=1.0); time.sleep(4)
    h.shot(T+f'shots/rec2_{mode}.png')
    print('tower?', h.debug("m $3ad98 6",0.5)[-60:])
finally:
    h.close()
