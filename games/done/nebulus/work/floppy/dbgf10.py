import sys,time,re
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
img=sys.argv[1]; wd=sys.argv[2]
h=NebFloppy(img,workdir=wd)
def W(a):
    o=h.debug(f'm ${a:x} 2',0.35); m=re.findall(r'[0-9A-F]{8}:\s+([0-9a-f]{2}) ([0-9a-f]{2})',o,re.I); return int(''.join(m[-1]),16)
try:
    print('title',h.boot_to_title(),flush=True)
    for i in range(40):
        if W(0x3d5ae)==0: break
        time.sleep(1)
    print('page',W(0x3d5ae),flush=True)
    print(h.debug('b pc = $7574c',0.5))
    h.key('F10',hold=0.6); time.sleep(3)
    print(h.debug('r',0.5)); 
    print('page',W(0x3d5ae),'vbl',hex(int(h.debug('m $70 4',0.4).split()[-5],16)) if False else '')
    h.shot(wd+'/f10.png')
    print(h.debug('m $70 4',0.4))
finally:
    h.close()
