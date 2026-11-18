import sys,time
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
img=sys.argv[1]; wd=sys.argv[2]
h=NebFloppy(img,workdir=wd)
def W(a):
    import re
    o=h.debug(f'm ${a:x} 2',0.35); m=re.findall(r'[0-9A-F]{8}:\s+([0-9a-f]{2}) ([0-9a-f]{2})',o,re.I); return int(''.join(m[-1]),16)
try:
    t=h.boot_to_title(); print('title at',t,flush=True)
    # wait for the frog page (page word at floppy $3d5ae == 0) 
    for i in range(30):
        pw=W(0x3d5ae); print('page',pw,flush=True)
        if pw==0: break
        time.sleep(1.5)
    h.shot(wd+'/p0.png')
    h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0)
    for i in range(6):
        time.sleep(3); h.shot(wd+f'/g{i}.png'); print(i,'timer',hex(W(0x3ad74)),hex(W(0x3ad76)),hex(W(0x3ad78)),'tower',W(0x3390c),flush=True)
finally:
    h.close()
