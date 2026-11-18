import sys,time
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
h=NebFloppy('orig.st',workdir='/tmp/nf_base2',trace='fdc')
try:
    time.sleep(12); h.shot('/tmp/nf_base2/a.png')
    h.keypress(57); 
    for i in range(12):
        time.sleep(5)
        print(i*5+12, h.debug('m $3d00f 4',0.4).strip().splitlines()[-1:], flush=True)
        if i in (1,4,8): h.shot(f'/tmp/nf_base2/s{i}.png')
    h.keypress(57)
    time.sleep(10); h.shot('/tmp/nf_base2/z.png')
    print(h.debug('m $3d00f 4',0.4)); print(h.debug('r',0.4))
finally:
    h.close()
