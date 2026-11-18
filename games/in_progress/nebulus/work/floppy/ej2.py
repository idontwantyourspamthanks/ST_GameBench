import sys,time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor'); sys.path.insert(0,'.')
from e160_lib import *
from nebfloppy import NebFloppy
h=NebFloppy(sys.argv[1],machine='ste',mem=1024,workdir='/tmp/nr3/ej2',trace='fdc'); t=T(h)
print('title',h.boot_to_title(timeout=300,space_at=25),flush=True); time.sleep(3)
h.key('F10',hold=0.5); time.sleep(2)
def op(name):
    t0=time.time(); n=len(h._logtext())
    t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); t.F(3.5); time.sleep(1.0)
    print(name,'msg',repr(t.msg()),'%.1fs'%(time.time()-t0),flush=True)
    h.key('F10',hold=0.5); time.sleep(3); h.key('F10',hold=0.5); time.sleep(2)   # leave the manager and return: menu back at the top
op('game disk inserted (no NEBLEVEL.OVL on it)')
h.cmd('hatari-option --disk-a /dev/null'); time.sleep(2)
op('drive A empty (ejected)')
h.cmd(f"hatari-option --disk-a /tmp/ne/d/t3.st"); time.sleep(2)
op('campaign disk inserted')
h.close()
