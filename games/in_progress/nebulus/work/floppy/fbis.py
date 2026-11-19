import sys,time,hashlib
sys.path.insert(0,'.'); sys.path.insert(0,'../../tools')
import nefloppy
from nebfloppy import NebFloppy
names=sys.argv[1].split(',') if sys.argv[1]!='-' else []
tag=sys.argv[2]
img,rep,blocks=nefloppy.build_disk(names)
open(f'/tmp/bis_{tag}.st','wb').write(img)
h=NebFloppy(f'/tmp/bis_{tag}.st',workdir=f'/tmp/nf_bis_{tag}')
try:
    t=h.boot_to_title(); print(tag,'title at',t,flush=True)
    for i in range(5):
        time.sleep(6); h.shot(f'/tmp/nf_bis_{tag}/s{i}.png')
    h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(5); h.shot(f'/tmp/nf_bis_{tag}/g.png')
    print(tag,'timer',h.debug('m $3ad74 6',0.4).splitlines()[-2:], flush=True)
finally:
    h.close()
