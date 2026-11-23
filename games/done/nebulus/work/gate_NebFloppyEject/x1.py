import sys; sys.path.insert(0,'.')
from lib import *
WD=sys.argv[1]; mode=sys.argv[2]
h=NebFloppy(UNZ+'Nebulus_game_disk.st',machine='ste',mem=1024,workdir=WD,trace='fdc'); t=T(h)
def op(save=False):
    h.key('F10',hold=0.4); time.sleep(2.5); h.key('F10',hold=0.4); time.sleep(2.5)
    t.K('Down',4 if save else 3,hold=0.2,gap=0.4); t.F(1.0); t0=time.time(); t.F(1.0)
    m=None
    for _ in range(60):
        time.sleep(0.5)
        try: busy=struct.unpack('>H',grab(h,0x77cc0+174,2,'vd'))[0]
        except Exception: continue
        if busy==0:
            m=t.msg()
            if m is not None: break
    print('   (%.1f s) %r'%(time.time()-t0,m),flush=True); return m
print('title',h.boot_to_title(timeout=400,space_at=20),flush=True); time.sleep(3)
h.key('F10',hold=0.5); time.sleep(2)
if mode=='devnull': h.cmd('hatari-option --disk-a /dev/null'); time.sleep(2)
print(op())
print(op())
t.insert(D+'t3.st'); print(op())
h.close()
