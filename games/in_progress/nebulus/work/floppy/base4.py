import sys,time
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
h=NebFloppy('orig.st',workdir='/tmp/nf_base4',trace='fdc')
def nread(): return open('/tmp/nf_base4/log.txt',errors='replace').read().count('fdc read sector')
try:
    time.sleep(20)
    h.key('space',hold=0.6)
    for i in range(1,11):
        time.sleep(15); print(i*15+20,'reads',nread(),flush=True); h.shot(f'/tmp/nf_base4/t{i}.png')
    h.dump('/tmp/nf_base4/ram_150.bin',0,0x100000)
    print(h.debug('r',0.4))
finally:
    h.close()
