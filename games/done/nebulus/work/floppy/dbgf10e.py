import sys,time,re
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
img=sys.argv[1]; wd=sys.argv[2]
h=NebFloppy(img,workdir=wd)
D='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy/'
def W(a):
    o=h.debug(f'm ${a:x} 2',0.35); m=re.findall(r'[0-9A-F]{8}:\s+([0-9a-f]{2}) ([0-9a-f]{2})',o,re.I); return int(''.join(m[-1]),16)
try:
    print('title',h.boot_to_title(),flush=True)
    for i in range(40):
        if W(0x3d5ae)==0: break
        time.sleep(1)
    # start tracing when the editor latch is set (rsKey byte = $44), stop at the exception
    h.cmd(f'hatari-debug b ($77cab).b = $44 :trace :once :file {D}cmds_tr.txt'); time.sleep(0.3)
    h.cmd(f'hatari-debug b pc = $77a02 :trace :once :file {D}cmds_off.txt'); time.sleep(0.3)
    n0=len(h._logtext())
    h.key('F10',hold=0.6); time.sleep(4)
    log=h._logtext()[n0:]
    open(wd+'/trace.txt','w').write(log)
    print(len(log))
finally:
    h.close()
