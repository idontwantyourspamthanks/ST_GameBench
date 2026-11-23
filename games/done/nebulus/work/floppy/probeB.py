import sys,time
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
h=NebFloppy('B/b.st',workdir='/tmp/nf_B',trace='fdc')
def nread(): return open('/tmp/nf_B/log.txt',errors='replace').read().count('fdc read sector')
try:
    t0=time.time()
    for i in range(1,21):
        time.sleep(8)
        if i in (2,3): h.keypress(57)
        m=h.debug('m $3d00f 4',0.4).strip().splitlines()[-1][:20]
        print(int(time.time()-t0),'reads',nread(),m,flush=True)
        if i in (3,6,10): h.shot(f'/tmp/nf_B/t{i}.png')
        if 'Higl'.encode().hex().upper()[:2] in m and '48 69' in m: break
    print(h.debug('m $b0020 8',0.4))
finally:
    h.close()
