import sys,time
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
img=sys.argv[1]; wd=sys.argv[2]
h=NebFloppy(img,workdir=wd)
try:
    time.sleep(20); h.key('space',hold=0.6)
    time.sleep(95)
    print(h.debug('r',0.5)); print(h.debug('m $70 4',0.4)); print(h.debug('m $33b1a 2',0.4));print(h.debug('m $33b6a 8',0.4)); print(h.debug('m $77ec0 64',0.4))
    h.dump(wd+'/ram.bin',0,0x100000)
finally:
    h.close()
