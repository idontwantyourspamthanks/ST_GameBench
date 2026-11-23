import sys,time,subprocess
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
h=NebFloppy('orig.st',workdir='/tmp/nf_base3',trace='fdc')
def nread(): return open('/tmp/nf_base3/log.txt',errors='replace').read().count('fdc read sector')
try:
    time.sleep(40)
    print('reads at 40s',nread(),flush=True)
    h.dump('/tmp/nf_base3/ram_wait.bin',0,0x100000)
    print(h.debug('r',0.4))
    for k in ('space','Return'):
        h.key(k,hold=0.6); time.sleep(8); print(k,'reads',nread(),flush=True)
        h.shot(f'/tmp/nf_base3/{k}.png')
    h.click('1',hold=0.4); time.sleep(8); print('click reads',nread())
    h.shot('/tmp/nf_base3/click.png')
    h.dump('/tmp/nf_base3/ram_after.bin',0,0x100000)
finally:
    h.close()
