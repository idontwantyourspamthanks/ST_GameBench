import sys,time,re
sys.path.insert(0,'.'); sys.path.insert(0,'../../tools')
import nefloppy
from nebfloppy import NebFloppy
names=sys.argv[1].split(',') if sys.argv[1]!='-' else []; tag=sys.argv[2]
skip={int(x,16) for x in sys.argv[3].split(',')} if len(sys.argv)>3 and sys.argv[3] else set()
O=nefloppy.Plan
class P2(O):
    def __init__(s,*a,**k):
        super().__init__(*a,**k); s.sites=[x for x in s.sites if x[1] not in skip]
nefloppy.Plan=P2
img,rep,blocks=nefloppy.build_disk(names)
open(f'/tmp/bis_{tag}.st','wb').write(img)
h=NebFloppy(f'/tmp/bis_{tag}.st',workdir=f'/tmp/nf_bis_{tag}')
def W(a):
    o=h.debug(f'm ${a:x} 2',0.35); m=re.findall(r'[0-9A-F]{8}:\s+([0-9a-f]{2}) ([0-9a-f]{2})',o,re.I); return int(''.join(m[-1]),16)
try:
    print(tag,'title',h.boot_to_title(),flush=True)
    for i in range(40):
        if W(0x3d5ae)==0: break
        time.sleep(1)
    print(tag,'before F10: vbl vec',hex(h.vbl_vec()),'RS',h.debug('m $77c80 16',0.4).splitlines()[-1][:60],flush=True)
    h.key('F10',hold=0.6); time.sleep(3)
    print(tag,'after F10: vbl vec',hex(h.vbl_vec()),'RS',h.debug('m $77c80 16',0.4).splitlines()[-1][:60],flush=True)
    h.shot(f'/tmp/nf_bis_{tag}/f10.png')
    h.key('d',hold=0.6); time.sleep(3)
    print(tag,'after D: vbl vec',hex(h.vbl_vec()),flush=True)
    h.shot(f'/tmp/nf_bis_{tag}/d.png')
finally:
    h.close()
