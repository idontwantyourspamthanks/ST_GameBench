import sys,time,os
sys.path.insert(0,'.'); sys.path.insert(0,'../../tools')
import nefloppy
from nebfloppy import NebFloppy
names=sys.argv[1].split(','); tag=sys.argv[2]
skip={int(x,16) for x in sys.argv[3].split(',')} if len(sys.argv)>3 and sys.argv[3] else set()
# monkeypatch: drop sites by PP address
orig_plan=nefloppy.Plan
class P2(orig_plan):
    def __init__(s,*a,**k):
        super().__init__(*a,**k); s.sites=[x for x in s.sites if x[1] not in skip]
nefloppy.Plan=P2
img,rep,blocks=nefloppy.build_disk(names)
open(f'/tmp/bis_{tag}.st','wb').write(img)
h=NebFloppy(f'/tmp/bis_{tag}.st',workdir=f'/tmp/nf_bis_{tag}')
try:
    t=h.boot_to_title(); print(tag,'title at',t,flush=True)
    for i in range(6):
        h.shot(f'/tmp/nf_bis_{tag}/s{i}.png'); time.sleep(4)
    print(tag,'vbl vec',hex(h.vbl_vec()))
finally:
    h.close()
