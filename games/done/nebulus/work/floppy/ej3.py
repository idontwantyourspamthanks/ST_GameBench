import sys,time,struct
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor'); sys.path.insert(0,'.')
from e160_lib import *
from nebfloppy import NebFloppy
h=NebFloppy(sys.argv[1],machine='ste',mem=1024,workdir='/tmp/nr3/ej3',trace='fdc'); t=T(h)
print('title',h.boot_to_title(timeout=300,space_at=25),flush=True); time.sleep(3)
h.key('F10',hold=0.5); time.sleep(2)
h.cmd('hatari-option --disk-a /dev/null'); time.sleep(2)
n=len(h._logtext())
t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); h.shot('/tmp/nr3/shots/ej3_prompt.png')
t.F(3.5); time.sleep(1.5)
print('msg',repr(t.msg()),'vDisk',W(h,0x77cc0+174),'vRes',W(h,0x77cc0),flush=True)
h.shot('/tmp/nr3/shots/ej3_after.png')
tr=h._logtext()[n:]
print('fdc lines',len([l for l in tr.splitlines() if 'fdc' in l.lower()]),flush=True)
print('\n'.join([l for l in tr.splitlines() if 'Eject' in l or 'eject' in l or 'error' in l.lower()][:12]),flush=True)
h.close()
