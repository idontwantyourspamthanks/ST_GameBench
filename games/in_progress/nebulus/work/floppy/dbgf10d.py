import sys,time,re
from pathlib import Path
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
img=sys.argv[1]; wd=sys.argv[2]
h=NebFloppy(img,workdir=wd)
def W(a):
    o=h.debug(f'm ${a:x} 2',0.35); m=re.findall(r'[0-9A-F]{8}:\s+([0-9a-f]{2}) ([0-9a-f]{2})',o,re.I); return int(''.join(m[-1]),16)
def L(a): return (W(a)<<16)|W(a+2)
try:
    print('title',h.boot_to_title(),flush=True)
    for i in range(40):
        if W(0x3d5ae)==0: break
        time.sleep(1)
    vec={n:(L(a)&0xffffff) for n,a in (('bus',8),('addr',12),('illegal',16),('linea',0x28),('linef',0x2c),('trap1',0x84))}
    print({k:hex(v) for k,v in vec.items()})
    for n in ():
        h.cmd(f'hatari-debug b pc = ${vec[n]:x} :trace :once :file {Path("cmds_exc.txt").resolve() if False else "/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy/cmds_exc.txt"}'); time.sleep(0.2)
    h.cmd('hatari-debug b pc = $77a02 :trace :once :file /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy/cmds_exc.txt'); time.sleep(0.3)
    n0=len(h._logtext())
    h.key('F10',hold=0.6); time.sleep(4)
    print(h._logtext()[n0:][:3500])
finally:
    h.close()
