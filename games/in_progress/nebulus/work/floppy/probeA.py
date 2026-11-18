import sys,time
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
img=sys.argv[1]; wd=sys.argv[2]
h=NebFloppy(img,workdir=wd,trace='fdc')
try:
    t=h.boot_to_title(); print('title at',t,flush=True)
    h.shot(wd+'/title.png')
    print(h.debug('m $77ec0 8',0.4))
    ok=h.boot_to_game() if False else None
    time.sleep(1)
    h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(4)
    print('timer',h.debug('m $3ad74 6',0.4)); h.shot(wd+'/tower.png')
finally:
    h.close()
