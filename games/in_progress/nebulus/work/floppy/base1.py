import sys,time
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
h=NebFloppy('orig.st',workdir='/tmp/nf_base',extra=['--harddrive',''] if len(sys.argv)>1 else [])
try:
    for i in range(30):
        time.sleep(5)
        print(i*5, h.debug('m $3d00f 4',0.4).strip().splitlines()[-1:], flush=True)
        if i in (3,8,14,20): h.shot(f'/tmp/nf_base/s{i}.png')
finally:
    h.close()
