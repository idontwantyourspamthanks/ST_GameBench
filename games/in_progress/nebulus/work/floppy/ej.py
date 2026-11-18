import sys,time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor'); sys.path.insert(0,'.')
from e160_lib import *
from nebfloppy import NebFloppy
h=NebFloppy(sys.argv[1],machine='ste',mem=1024,workdir='/tmp/nr3/ej',trace='fdc'); t=T(h)
print('title',h.boot_to_title(timeout=300,space_at=25),flush=True); time.sleep(3)
h.key('F10',hold=0.5); time.sleep(2)
n0=len(h._logtext())
for v in ["''",'""','/dev/null','/tmp/nr3/none.st']:
    n=len(h._logtext()); h.cmd(f"hatari-option --disk-a {v}"); time.sleep(2)
    print(repr(v),'->',repr(h._logtext()[n:][-300:]),flush=True)
    n=len(h._logtext()); t0=time.time(); m=None
    t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); t.F(3.5); time.sleep(1.0); m=t.msg()
    print('  msg',m,'%.1fs'%(time.time()-t0),'fdc lines',len([l for l in h._logtext()[n:].splitlines() if 'FDC' in l or 'fdc' in l]),flush=True)
    t.K('Up',3,hold=0.2,gap=0.4)
h.close()
