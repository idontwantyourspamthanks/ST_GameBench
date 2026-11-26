import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy')
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
import ed, e160_lib, os, time, struct
def grab(h,a,n,name='x'):
    p=f'/tmp/ng12fl/oc/nfe_{name}.bin'
    for attempt in range(5):
        if os.path.exists(p): os.remove(p)
        h.debug(f"savebin {p} ${a:x} ${n:x}",0.4)
        for _ in range(30):
            if os.path.exists(p) and os.path.getsize(p)==n:
                time.sleep(0.05)
                d=open(p,'rb').read(); os.remove(p); return d
            time.sleep(0.1)
    raise RuntimeError('grab failed')
ed.grab=grab; e160_lib.grab=grab
from e160_lib import *
grab=grab
from nebfloppy import NebFloppy
D='/tmp/ng12fl/ne/d/'
UNZ='/nonexistent/'
class NF(NebFloppy):
    pass
_b = NebFloppy.boot_to_title
def _b2(self, *a, **k):
    r = _b(self, *a, **k)
    if r and os.environ.get('CPU16'):
        self.set_cpuclock(16); time.sleep(2); print('cpuclock 16 set after the title', flush=True)
    return r
NebFloppy.boot_to_title = _b2
